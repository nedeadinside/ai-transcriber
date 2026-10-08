import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar, Final

import httpx
from arq.connections import RedisSettings

from api.schemas import Artifacts, TranscribeResult
from clients.diarizer import DiarizerClient
from clients.whisper import WhisperClient
from config import load_config
from config.models import AppConfig
from core.api.schemas import JobCancelled, JobFailed, JobSucceeded
from llm.factory import build_llm
from llm.prompts import load_prompts
from pipeline import convert, transcription
from worker.context import WorkerContext

logger = logging.getLogger(__name__)

cfg: AppConfig = load_config()

_WEBHOOK_TIMEOUT_SEC: Final[float] = 10.0


async def startup(ctx: WorkerContext) -> None:
    """
    Open the shared http client and build the service clients once per worker process.

    :param ctx: ARQ worker context.
    """
    logging.basicConfig(level=cfg.logging.level)
    client = httpx.AsyncClient()
    ctx["http"] = client
    ctx["whisper"] = WhisperClient(cfg, client)
    ctx["diarizer"] = DiarizerClient(cfg, client)
    ctx["prompts"] = load_prompts()
    ctx["llm"] = build_llm(cfg.llm)


async def shutdown(ctx: WorkerContext) -> None:
    """
    Close the shared http client.

    :param ctx: ARQ worker context.
    """
    await ctx["http"].aclose()


async def notify(
    ctx: WorkerContext,
    webhooks: list[str],
    body: JobSucceeded[TranscribeResult] | JobFailed | JobCancelled,
) -> None:
    """
    POST a finished job to each webhook, once, without letting a failure reach the job.

    :param ctx: ARQ worker context holding the shared http client.
    :param webhooks: URLs to notify.
    :param body: Terminal job status, the same shape the job endpoint returns.
    """
    if not webhooks:
        return

    payload = {"job_id": ctx["job_id"], **body.model_dump(mode="json")}
    for url in webhooks:
        try:
            response = await ctx["http"].post(url, json=payload, timeout=_WEBHOOK_TIMEOUT_SEC)
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("webhook %s failed: %s", url, e)


async def transcribe(
    ctx: WorkerContext,
    path: str,
    artifacts: Artifacts,
    webhooks: list[str],
) -> TranscribeResult:
    """
    Convert an upload to FLAC, transcribe it, then notify the webhooks.

    :param ctx: ARQ worker context holding the service clients.
    :param path: Path to the uploaded audio or video file in the spool volume.
    :param artifacts: Artifacts to return.
    :param webhooks: URLs to POST the finished job to.
    :raises TranscriberError: If any step fails; ARQ turns it into a job failure.
    :return: The requested artifacts.
    """
    started_at = datetime.now(UTC)
    source = Path(path)
    audio = source.with_suffix(".norm.flac")

    def elapsed() -> float:
        """
        Measure how long the job has been running.

        :return: Seconds since this job started.
        """
        return round((datetime.now(UTC) - started_at).total_seconds(), 3)

    try:
        await convert.to_flac(source, audio)
        result = await transcription.run(ctx, str(audio), artifacts)
    except asyncio.CancelledError:
        await notify(ctx, webhooks, JobCancelled(started_at=started_at, duration_sec=elapsed()))
        raise
    except Exception as e:
        body = JobFailed(error=str(e), started_at=started_at, duration_sec=elapsed())
        await notify(ctx, webhooks, body)
        raise
    else:
        body = JobSucceeded[TranscribeResult](
            result=result, started_at=started_at, duration_sec=elapsed()
        )
        await notify(ctx, webhooks, body)
        return result
    finally:
        await asyncio.to_thread(source.unlink, missing_ok=True)
        await asyncio.to_thread(audio.unlink, missing_ok=True)


class WorkerSettings:
    """
    ARQ worker configuration entrypoint.
    """

    functions: ClassVar[list[Callable[..., Any]]] = [transcribe]
    on_startup: ClassVar[Callable[..., Any]] = startup
    on_shutdown: ClassVar[Callable[..., Any]] = shutdown
    redis_settings: RedisSettings = RedisSettings.from_dsn(cfg.queue.redis_url)
    max_jobs: int = cfg.queue.concurrency
    job_timeout: int = cfg.queue.job_timeout
    allow_abort_jobs: bool = True
