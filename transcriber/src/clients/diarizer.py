import asyncio
import contextlib
from pathlib import Path
from typing import TYPE_CHECKING, Final

import httpx
from pydantic import ValidationError

from core.api.schemas import SpeakerSegment
from core.enums import JobState
from errors import DiarizerError

if TYPE_CHECKING:
    from config.models import AppConfig

_CANCEL_TIMEOUT_SEC: Final[float] = 5.0


class DiarizerClient:
    """
    Client for the Diarizer service.
    """

    def __init__(self, cfg: "AppConfig", client: httpx.AsyncClient) -> None:
        """
        Store settings and the shared http client.

        :param cfg: Root settings.
        :param client: Shared async http client.
        """
        self.cfg = cfg
        self.client = client

    async def run(self, path: str) -> list[SpeakerSegment]:
        """
        Diarize an audio file and wait for the job to finish.

        :param path: Path to the audio file.
        :raises DiarizerError: If the job fails, times out, or the service is unreachable.
        :return: List of speaker segments.
        """
        job_id = await self._submit(path)
        return await self._poll(job_id)

    async def _submit(self, path: str) -> str:
        """
        Upload the audio file and queue a diarization job.

        :param path: Path to the audio file.
        :raises DiarizerError: If the service is unreachable or returns an error status.
        :return: Identifier of the queued job.
        """
        file = Path(path)
        try:
            with file.open("rb") as f:  # noqa: ASYNC230
                response = await self.client.post(
                    f"{self.cfg.diarizer.url}/v1/diarize",
                    files={"file": (file.name, f)},
                    timeout=self.cfg.diarizer.timeout_sec,
                )
            response.raise_for_status()
            return response.json()["job_id"]
        except httpx.HTTPError as e:
            raise DiarizerError(f"diarize request failed: {e}") from e
        except (KeyError, ValueError) as e:
            raise DiarizerError(f"unparseable diarize response: {e}") from e

    async def _poll(self, job_id: str) -> list[SpeakerSegment]:
        """
        Poll a diarization job until it reaches a terminal state.

        :param job_id: Identifier of the queued job.
        :raises DiarizerError: If the job fails, is cancelled, times out, or the service is unreachable.
        :return: List of speaker segments.
        """
        deadline = asyncio.get_running_loop().time() + self.cfg.diarizer.timeout_sec
        try:
            while asyncio.get_running_loop().time() < deadline:
                try:
                    response = await self.client.get(f"{self.cfg.diarizer.url}/v1/jobs/{job_id}")
                    response.raise_for_status()
                    body = response.json()
                except httpx.HTTPError as e:
                    raise DiarizerError(f"job poll failed: {e}") from e

                status = body.get("status")
                if status == JobState.SUCCESS:
                    try:
                        return [
                            SpeakerSegment.model_validate(s) for s in body["result"]["segments"]
                        ]
                    except (KeyError, ValidationError) as e:
                        raise DiarizerError(f"unparseable diarizer result: {e}") from e
                if status == JobState.FAILURE:
                    raise DiarizerError(f"diarizer job {job_id} failed: {body.get('error')}")
                if status == JobState.CANCELLED:
                    raise DiarizerError(f"diarizer job {job_id} was cancelled")
                await asyncio.sleep(self.cfg.diarizer.poll_interval_sec)
        except asyncio.CancelledError:
            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.shield(self._cancel(job_id))
            raise
        raise DiarizerError(f"diarizer job {job_id} timed out")

    async def _cancel(self, job_id: str) -> None:
        """
        Ask the diarizer to abort a job, on a best-effort basis.

        Called while this task is already unwinding, so a failure here has nothing left to
        report to and is swallowed rather than masking the cancellation.

        :param job_id: Identifier of the queued job.
        """
        with contextlib.suppress(httpx.HTTPError):
            await self.client.post(
                f"{self.cfg.diarizer.url}/v1/jobs/{job_id}/cancel",
                timeout=_CANCEL_TIMEOUT_SEC,
            )
