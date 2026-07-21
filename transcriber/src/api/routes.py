from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import HttpUrl, ValidationError

from core.api import jobs
from core.api.schemas import JobAccepted

from .schemas import Artifacts, JobStatus, TranscribeResult

router = APIRouter(prefix="/v1")


@router.post("/transcribe", status_code=HTTPStatus.ACCEPTED)
async def transcribe(
    request: Request,
    file: Annotated[UploadFile, File()],
    raw: Annotated[bool, Form()] = False,
    diarized: Annotated[bool, Form()] = False,
    summary: Annotated[bool, Form()] = False,
    webhooks: Annotated[list[str] | None, Form()] = None,
) -> JobAccepted:
    """
    Accept audio and queue a transcription job for the requested artifacts.

    :param request: Incoming request, holding the ARQ redis pool.
    :param file: Uploaded audio file.
    :param raw: Whether to return the transcript segments.
    :param diarized: Whether to return segments carrying speaker labels.
    :param summary: Whether to return a summary.
    :param webhooks: URLs to POST the finished job to.
    :raises HTTPException: If no artifact is requested or a webhook is not a valid URL.
    :raises AudioError: If the upload is rejected; the app maps it onto a status code.
    :return: Identifier of the queued job.
    """
    artifacts = Artifacts(raw=raw, diarized=diarized, summary=summary)
    if not artifacts.requested():
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=f"request at least one artifact: {', '.join(Artifacts.model_fields)}",
        )

    try:
        urls = [str(HttpUrl(url)) for url in webhooks or [] if url.strip()]
    except ValidationError as e:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail="webhooks must be valid URLs"
        ) from e

    path = await request.app.state.audio_spool.save(file)
    job = await request.app.state.redis.enqueue_job("transcribe", path, artifacts, urls)
    return JobAccepted(job_id=job.job_id)


@router.get("/jobs/{job_id}")
async def job_status(job_id: str, request: Request) -> JobStatus:
    """
    Return the status and result of a transcription job.

    :param job_id: Identifier of a previously queued job.
    :param request: Incoming request, holding the ARQ redis pool.
    :return: Job status with its result, error or timing.
    """
    return await jobs.get_status(job_id, request.app.state.redis, TranscribeResult)


@router.post("/jobs/{job_id}/cancel", status_code=HTTPStatus.ACCEPTED)
async def cancel_job(job_id: str, request: Request) -> JobStatus:
    """
    Ask the worker to abort a transcription job.

    :param job_id: Identifier of a previously queued job.
    :param request: Incoming request, holding the ARQ redis pool.
    :return: Job status as of this request.
    """
    return await jobs.request_cancel(job_id, request.app.state.redis, TranscribeResult)
