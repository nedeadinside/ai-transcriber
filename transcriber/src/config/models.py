from typing import Any

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import SettingsConfigDict

from core.config import BaseAppConfig
from enums import LLMProvider


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
