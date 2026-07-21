import asyncio
import logging
from typing import TYPE_CHECKING

from api.schemas import Artifacts, TranscribeResult
from llm import tasks as llm_tasks
from pipeline.merge import attach_speakers
from worker.context import WorkerContext

if TYPE_CHECKING:
    from api.schemas import Segment

logger = logging.getLogger(__name__)


async def run(ctx: WorkerContext, path: str, artifacts: Artifacts) -> TranscribeResult:
    """
    Produce the requested artifacts from an audio file.

    :param ctx: ARQ worker context holding the service clients.
    :param path: Path to the audio file in the spool volume.
    :param artifacts: Artifacts to return.
    :raises TranscriberError: If any step fails.
    :return: The requested artifacts, each left None when it was not requested.
    """
    async with asyncio.TaskGroup() as tg:
        asr_task = tg.create_task(ctx["whisper"].run(path))
        speakers_task = tg.create_task(ctx["diarizer"].run(path)) if artifacts.diarized else None

    asr = asr_task.result()
    raw = attach_speakers(asr.segments, []) if artifacts.raw else None

    diarized: list[Segment] | None = None
    if speakers_task is not None:
        diarized = attach_speakers(asr.segments, speakers_task.result())

    summary: str | None = None
    if artifacts.summary:
        if diarized is not None:
            transcript = "\n".join(f"[{seg.speaker or 'UNKNOWN'}] {seg.text}" for seg in diarized)
        else:
            transcript = "\n".join(seg.text for seg in asr.segments)
        summary = await llm_tasks.summarize(ctx["llm"], ctx["prompts"], transcript)

    return TranscribeResult(raw=raw, diarized=diarized, summary=summary)
