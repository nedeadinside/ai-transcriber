from typing import Annotated, Literal

from pydantic import BaseModel, Field

from enums import JobState


class Segment(BaseModel):
    """
    A single speech segment for one speaker.
    """

    start: float
    end: float
    speaker: str


class DiarizeAccepted(BaseModel):
    """
    Response returned after a job is queued.
    """

    job_id: str


class DiarizeResult(BaseModel):
    """
    Diarization result containing the segment list.
    """

    segments: list[Segment]


class JobQueued(BaseModel):
    """
    Job that is waiting in the queue or currently running.
    """

    status: Literal[JobState.PENDING, JobState.STARTED]


class JobSucceeded(BaseModel):
    """
    Job that finished successfully with a diarization result.
    """

    status: Literal[JobState.SUCCESS] = JobState.SUCCESS
    result: DiarizeResult


class JobFailed(BaseModel):
    """
    Job that finished with an error.
    """

    status: Literal[JobState.FAILURE] = JobState.FAILURE
    error: str


JobStatus = Annotated[
    JobQueued | JobSucceeded | JobFailed,
    Field(discriminator="status"),
]
