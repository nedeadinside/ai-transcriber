from typing import Any, Self

from pydantic import BaseModel, Field, SecretStr, model_validator
from pydantic_settings import SettingsConfigDict

from core.config import BaseAppConfig
from enums import LLMProvider
from pipeline import convert


class WhisperConfig(BaseModel):
    """
    Settings for the external Whisper ASR webservice.
    """

    url: str
    language: str | None
    vad_filter: bool
    timeout_sec: int


class DiarizerConfig(BaseModel):
    """
    Settings for the Diarizer service.
    """

    url: str
    poll_interval_sec: float
    timeout_sec: int


class LLMConfig(BaseModel):
    """
    Chat model settings, provider-independent.
    """

    provider: LLMProvider
    model: str
    prompts_file: str
    temperature: float = 0.0
    api_key: SecretStr | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class AppConfig(BaseAppConfig):
    """
    Root settings for the transcriber.
    """

    model_config = SettingsConfigDict(
        yaml_config_section="transcriber",
        env_prefix="TRANSCRIBER_",
    )

    whisper: WhisperConfig
    diarizer: DiarizerConfig
    llm: LLMConfig

    @model_validator(mode="after")
    def _check_converters(self) -> Self:
        """
        Refuse to start when an accepted format has no conversion strategy.

        :raises ValueError: If an allowed format is missing from the converter registry.
        :return: The validated settings.
        """
        missing = set(self.audio.allowed_formats) - convert.formats()
        if missing:
            raise ValueError(f"no converter for allowed formats: {', '.join(sorted(missing))}")
        return self
