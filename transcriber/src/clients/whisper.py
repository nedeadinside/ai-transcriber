import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Final

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from errors import WhisperError

if TYPE_CHECKING:
    from config.models import AppConfig

_PARAMS: Final[dict[str, str | bool]] = {
    "task": "transcribe",
    "encode": True,
    "output": "json",
    "word_timestamps": True,
}


class Word(BaseModel):
    """
    A single word with its timing.
    """

    model_config = ConfigDict(extra="ignore")

    start: float
    end: float
    word: str


class AsrSegment(BaseModel):
    """
    A single segment returned by the ASR service.
    """

    model_config = ConfigDict(extra="ignore")

    start: float
    end: float
    text: str
    words: list[Word] | None = None


class AsrResult(BaseModel):
    """
    Parsed body of an /asr response.
    """

    model_config = ConfigDict(extra="ignore")

    segments: list[AsrSegment] = []


class WhisperClient:
    """
    Client for the Whisper ASR webservice.
    """

    def __init__(self, cfg: "AppConfig", client: httpx.AsyncClient) -> None:
        """
        Store settings and the shared http client.

        :param cfg: Root settings.
        :param client: Shared async http client.
        """
        self.cfg = cfg
        self.client = client

    async def run(self, path: str) -> AsrResult:
        """
        Transcribe an audio file through the ASR service.

        :param path: Path to the audio file.
        :raises WhisperError: If the service fails or returns an unparseable body.
        :return: Parsed transcription result.
        """
        params = dict(_PARAMS)
        params["vad_filter"] = self.cfg.whisper.vad_filter
        if self.cfg.whisper.language:
            params["language"] = self.cfg.whisper.language

        file = Path(path)
        content = await asyncio.to_thread(file.read_bytes)
        try:
            response = await self.client.post(
                f"{self.cfg.whisper.url}/asr",
                params=params,
                files={"audio_file": (file.name, content)},
                timeout=self.cfg.whisper.timeout_sec,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise WhisperError(f"asr request failed: {e}") from e

        try:
            return AsrResult.model_validate_json(response.content)
        except ValidationError as e:
            raise WhisperError(f"unparseable asr response: {e}") from e
