from typing import Annotated

from pydantic import BaseModel, Field

from core.api.schemas import JobCancelled, JobFailed, JobQueued, JobSucceeded


class Segment(BaseModel):
    """
    A single transcript segment.
    """

    start: float
    end: float
    text: str
    speaker: str | None = None


class Artifacts(BaseModel):
    """
    Which artifacts a transcription job should produce.
    """

    raw: bool = False
    diarized: bool = False
    summary: bool = False

    def requested(self) -> bool:
        """
        Report whether at least one artifact was asked for.

        :return: True when any artifact is requested.
        """
        return any(self.model_dump().values())


class TranscribeResult(BaseModel):
    """
    The artifacts a job produced, one key per artifact of the same name.
    """

    raw: list[Segment] | None = None
    diarized: list[Segment] | None = None
    summary: str | None = None


JobStatus = Annotated[
    JobQueued | JobSucceeded[TranscribeResult] | JobFailed | JobCancelled,
    Field(discriminator="status"),
]
