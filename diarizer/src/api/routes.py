from http import HTTPStatus
from typing import Annotated

from arq.jobs import Job, JobStatus as ArqStatus
from fastapi import APIRouter, File, Request, UploadFile

from enums import JobState

from .schemas import (
    DiarizeAccepted,
    DiarizeResult,
    JobFailed,
    JobQueued,
    JobStatus,
    JobSucceeded,
)

router = APIRouter()


@router.post("/diarize", status_code=HTTPStatus.ACCEPTED)
async def diarize(
    request: Request,
    file: Annotated[UploadFile, File()],
) -> DiarizeAccepted:
    """
    Accept audio and queue a diarization job.

    :param request: Incoming request, holding the ARQ redis pool.
    :param file: Uploaded audio file.
    :return: Identifier of the queued job.
    """
    path = await request.app.state.audio_spool.save(file)
    job = await request.app.state.redis.enqueue_job("diarize", path)
    return DiarizeAccepted(job_id=job.job_id)


@router.get("/jobs/{job_id}")
async def job_status(job_id: str, request: Request) -> JobStatus:
    """
    Return the status and result of a diarization job.

    :param job_id: Identifier of a previously queued job.
    :param request: Incoming request, holding the ARQ redis pool.
    :return: Job status with its result or error message.
    """
    job = Job(job_id, request.app.state.redis)
    status = await job.status()
    if status == ArqStatus.in_progress:
        return JobQueued(status=JobState.STARTED)
    if status != ArqStatus.complete:
        return JobQueued(status=JobState.PENDING)

    info = await job.result_info()
    if info is None:
        return JobQueued(status=JobState.PENDING)
    if info.success:
        return JobSucceeded(result=DiarizeResult(**info.result))
    return JobFailed(error=str(info.result))


@router.get("/health")
async def health(request: Request) -> dict[str, str]:
    """
    Report service liveness.

    :return: Service health payload.
    """
    await request.app.state.redis.ping()
    return {"status": "ok"}
