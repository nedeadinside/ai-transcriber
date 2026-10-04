import asyncio
from http import HTTPStatus
from typing import TYPE_CHECKING

from arq.constants import abort_jobs_ss
from arq.jobs import Job, JobStatus as ArqStatus
from arq.utils import timestamp_ms
from fastapi import HTTPException
from pydantic import BaseModel

from core.enums import JobState

from .schemas import JobCancelled, JobFailed, JobQueued, JobSucceeded

if TYPE_CHECKING:
    from arq import ArqRedis


async def get_status[ResultT: BaseModel](
    job_id: str, redis: "ArqRedis", result_type: type[ResultT]
) -> JobQueued | JobSucceeded[ResultT] | JobFailed | JobCancelled:
    """
    Return the status of a job, with its result and timing once it has finished.

    :param job_id: Identifier of a previously queued job.
    :param redis: ARQ redis pool.
    :param result_type: Model the job result is validated against.
    :raises HTTPException: If no job with that identifier is known.
    :return: Job status, carrying the result, error or timing that applies to its state.
    """
    job = Job(job_id, redis)
    status = await job.status()
    if status == ArqStatus.not_found:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"unknown job {job_id}")
    if status == ArqStatus.in_progress:
        return JobQueued(status=JobState.STARTED)
    if status != ArqStatus.complete:
        return JobQueued(status=JobState.PENDING)

    info = await job.result_info()
    if info is None:
        return JobQueued(status=JobState.PENDING)

    timing = {
        "started_at": info.start_time,
        "duration_sec": (info.finish_time - info.start_time).total_seconds(),
    }
    if info.success:
        return JobSucceeded[result_type](result=result_type.model_validate(info.result), **timing)
    if isinstance(info.result, asyncio.CancelledError):
        return JobCancelled(**timing)
    return JobFailed(error=str(info.result) or type(info.result).__name__, **timing)


async def request_cancel[ResultT: BaseModel](
    job_id: str, redis: "ArqRedis", result_type: type[ResultT]
) -> JobQueued | JobSucceeded[ResultT] | JobFailed | JobCancelled:
    """
    Ask the worker to abort a job and report the state it is in right now.

    Aborting is asynchronous: a queued job is dropped before it starts, a running one is
    cancelled at its next await. Callers poll the job to see it reach a terminal state.

    :param job_id: Identifier of a previously queued job.
    :param redis: ARQ redis pool.
    :param result_type: Model the job result is validated against.
    :raises HTTPException: If no job with that identifier is known.
    :return: Job status as of this request, before the abort has been picked up.
    """
    job = Job(job_id, redis)
    if await job.status() == ArqStatus.not_found:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"unknown job {job_id}")

    await redis.zadd(abort_jobs_ss, {job_id: timestamp_ms()})
    return await get_status(job_id, redis, result_type)
