import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Final

import httpx
from mcp.server.mcpserver.exceptions import ToolError

from core.enums import JobState

if TYPE_CHECKING:
    from pathlib import Path

    from config import TranscriberConfig

_CANCEL_TIMEOUT_SEC: Final[float] = 5.0


class TranscriberClient:
    """
    Client that runs one transcription on the transcriber service and waits for it.
    """

    def __init__(self, cfg: "TranscriberConfig", client: httpx.AsyncClient) -> None:
        """
        Store settings and the http client.

        :param cfg: Transcriber settings.
        :param client: Async http client.
        """
        self.cfg = cfg
        self.client = client

    async def run(
        self,
        file: "Path",
        artifacts: dict[str, bool],
        on_poll: Callable[[int], Awaitable[None]],
    ) -> dict[str, Any]:
        """
        Transcribe a file and wait for the result.

        :param file: Audio file to upload.
        :param artifacts: Artifact flags forwarded as form fields.
        :param on_poll: Callback awaited on every poll with the poll count.
        :return: The job result.
        """
        job_id = await self.submit(file, artifacts)
        return await self.wait(job_id, on_poll)

    async def submit(self, file: "Path", artifacts: dict[str, bool]) -> str:
        """
        Upload the file and queue a transcription job.

        :param file: Audio file to upload.
        :param artifacts: Artifact flags forwarded as form fields.
        :raises ToolError: If the service rejects the upload or is unreachable.
        :return: Identifier of the queued job.
        """
        try:
            with file.open("rb") as f:
                response = await self.client.post(
                    f"{self.cfg.url}/v1/transcribe",
                    files={"file": (file.name, f)},
                    data={name: str(flag).lower() for name, flag in artifacts.items()},
                    timeout=self.cfg.timeout_sec,
                )
        except httpx.HTTPError as e:
            raise ToolError(f"transcriber unreachable: {e}") from e
        if response.is_error:
            raise ToolError(f"transcriber rejected the file: {_detail(response)}")
        return response.json()["job_id"]

    async def wait(self, job_id: str, on_poll: Callable[[int], Awaitable[None]]) -> dict[str, Any]:
        """
        Poll a job until it finishes, cancelling it if the caller goes away.

        :param job_id: Identifier of the queued job.
        :param on_poll: Callback awaited on every poll with the poll count.
        :raises ToolError: If the job fails, is cancelled, or the service is unreachable.
        :return: The job result.
        """
        polls = 0
        try:
            while True:
                try:
                    response = await self.client.get(f"{self.cfg.url}/v1/jobs/{job_id}")
                    response.raise_for_status()
                except httpx.HTTPError as e:
                    raise ToolError(f"job poll failed: {e}") from e

                body = response.json()
                status = body["status"]
                if status == JobState.SUCCESS:
                    return body["result"]
                if status == JobState.FAILURE:
                    raise ToolError(f"transcription failed: {body.get('error')}")
                if status == JobState.CANCELLED:
                    raise ToolError("transcription was cancelled")

                polls += 1
                await on_poll(polls)
                await asyncio.sleep(self.cfg.poll_interval_sec)
        except asyncio.CancelledError:
            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.shield(self._cancel(job_id))
            raise

    async def _cancel(self, job_id: str) -> None:
        """
        Ask the transcriber to abort a job, on a best-effort basis.

        :param job_id: Identifier of the queued job.
        """
        with contextlib.suppress(httpx.HTTPError):
            await self.client.post(
                f"{self.cfg.url}/v1/jobs/{job_id}/cancel", timeout=_CANCEL_TIMEOUT_SEC
            )


def _detail(response: httpx.Response) -> str:
    """
    Pull the error detail out of an error response.

    :param response: Error response from the transcriber.
    :return: The detail field, or the raw body when it is not json.
    """
    try:
        return str(response.json()["detail"])
    except (ValueError, KeyError, TypeError):
        return response.text
