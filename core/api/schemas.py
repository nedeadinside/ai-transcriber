from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from core.enums import JobState


class SpeakerSegment(BaseModel):
    """
    A single speech segment attributed to one speaker.
    """

    start: float
    end: float
    speaker: str


class JobAccepted(BaseModel):
    """
    Response returned after a job is queued.
    """

    job_id: str


class JobQueued(BaseModel):
    """
    Job that is waiting in the queue or currently running.
    """

    status: Literal[JobState.PENDING, JobState.STARTED]


class JobFinished(BaseModel):
    """
    Timing shared by every job that reached a terminal state.

    ARQ records the start only once a job finishes, so a queued or running job carries no
    timing at all and reports as JobQueued instead.
    """

    started_at: datetime
    duration_sec: float


class JobSucceeded[ResultT: BaseModel](JobFinished):
    """
    Job that finished successfully with its result.
    """

    status: Literal[JobState.SUCCESS] = JobState.SUCCESS
    result: ResultT


class JobFailed(JobFinished):
    """
    Job that finished with an error.
    """

    status: Literal[JobState.FAILURE] = JobState.FAILURE
    error: str


class JobCancelled(JobFinished):
    """
    Job that was aborted on request.
    """

    status: Literal[JobState.CANCELLED] = JobState.CANCELLED
