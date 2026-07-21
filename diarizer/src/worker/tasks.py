import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar, TypedDict

from arq.connections import RedisSettings

from config import load_config
from config.models import AppConfig
from core.api.schemas import SpeakerSegment
from pipeline.diarization import DiarizationPipeline

cfg: AppConfig = load_config()


class WorkerContext(TypedDict):
    """
    Partial view of the ARQ worker context, covering the keys this app populates and reads.
    """

    diarizer: DiarizationPipeline


async def startup(ctx: WorkerContext) -> None:
    """
    Load the pipeline once per worker process.

    :param ctx: ARQ worker context.
    """
    diarizer = DiarizationPipeline(cfg)
    diarizer.load()
    ctx["diarizer"] = diarizer


async def diarize(
    ctx: WorkerContext,
    path: str,
) -> dict[str, list[SpeakerSegment]]:
    """
    Run diarization on an audio file and return the segments.

    :param ctx: ARQ worker context holding the loaded pipeline.
    :param path: Path to the audio file in the spool volume.
    :return: Dictionary containing the list of segments.
    """
    try:
        segments = await asyncio.to_thread(ctx["diarizer"].run, path)
        return {"segments": segments}
    finally:
        await asyncio.to_thread(Path(path).unlink, missing_ok=True)


class WorkerSettings:
    """
    ARQ worker configuration entrypoint.
    """

    functions: ClassVar[list[Callable[..., Any]]] = [diarize]
    on_startup: ClassVar[Callable[..., Any]] = startup
    redis_settings: RedisSettings = RedisSettings.from_dsn(cfg.queue.redis_url)
    max_jobs: int = cfg.queue.concurrency
    job_timeout: int = cfg.queue.job_timeout
    allow_abort_jobs: bool = True
