from typing import Annotated

from pydantic import BaseModel, Field

from core.api.schemas import JobCancelled, JobFailed, JobQueued, JobSucceeded, SpeakerSegment


class DiarizeResult(BaseModel):
    """
    Diarization result containing the segment list.
    """

    segments: list[SpeakerSegment]


JobStatus = Annotated[
    JobQueued | JobSucceeded[DiarizeResult] | JobFailed | JobCancelled,
    Field(discriminator="status"),
]
