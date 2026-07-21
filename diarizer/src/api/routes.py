from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile

from core.api import jobs
from core.api.schemas import JobAccepted

from .schemas import DiarizeResult, JobStatus

router = APIRouter(prefix="/v1")


@router.post("/diarize", status_code=HTTPStatus.ACCEPTED)
async def diarize(
    request: Request,
    file: Annotated[UploadFile, File()],
) -> JobAccepted:
    """
    Accept audio and queue a diarization job.

    :param request: Incoming request, holding the ARQ redis pool.
    :param file: Uploaded audio file.
    :raises AudioError: If the upload is rejected; the app maps it onto a status code.
    :return: Identifier of the queued job.
    """
    path = await request.app.state.audio_spool.save(file)
    job = await request.app.state.redis.enqueue_job("diarize", path)
    return JobAccepted(job_id=job.job_id)


@router.get("/jobs/{job_id}")
async def job_status(job_id: str, request: Request) -> JobStatus:
    """
    Return the status and result of a diarization job.

    :param job_id: Identifier of a previously queued job.
    :param request: Incoming request, holding the ARQ redis pool.
    :return: Job status with its result, error or timing.
    """
    return await jobs.get_status(job_id, request.app.state.redis, DiarizeResult)


@router.post("/jobs/{job_id}/cancel", status_code=HTTPStatus.ACCEPTED)
async def cancel_job(job_id: str, request: Request) -> JobStatus:
    """
    Ask the worker to abort a diarization job.

    :param job_id: Identifier of a previously queued job.
    :param request: Incoming request, holding the ARQ redis pool.
    :return: Job status as of this request; poll the job to see it reach a terminal state.
    """
    return await jobs.request_cancel(job_id, request.app.state.redis, DiarizeResult)
