from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

from arq.connections import RedisSettings

from config import load_config
from config.models import AppConfig
from pipeline.diarization import DiarizationPipeline, SegmentDict

cfg: AppConfig = load_config()


async def startup(ctx: dict[str, Any]) -> None:
    """
    Load the pipeline once per worker process.

    :param ctx: ARQ worker context.
    """
    diarizer = DiarizationPipeline(cfg)
    diarizer.load()
    ctx["diarizer"] = diarizer


async def diarize(
    ctx: dict[str, Any],
    path: str,
) -> dict[str, list[SegmentDict]]:
    """
    Run diarization on an audio file and return the segments.

    :param ctx: ARQ worker context holding the loaded pipeline.
    :param path: Path to the audio file in the spool volume.
    :return: Dictionary containing the list of segments.
    """
    try:
        diarizer: DiarizationPipeline = ctx["diarizer"]
        segments = diarizer.run(path)
        return {"segments": segments}
    finally:
        Path(path).unlink(missing_ok=True)  # noqa: ASYNC240


class WorkerSettings:
    """
    ARQ worker configuration entrypoint.
    """

    functions: ClassVar[list[Callable[..., Any]]] = [diarize]
    on_startup: ClassVar[Callable[..., Any]] = startup
    redis_settings: RedisSettings = RedisSettings.from_dsn(cfg.queue.redis_url)
    max_jobs: int = cfg.queue.concurrency
    job_timeout: int = cfg.queue.job_timeout
