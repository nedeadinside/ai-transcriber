from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from enums import AudioFormat, Device, LogLevel


class QueueConfig(BaseModel):
    """
    Task queue settings (ARQ over a single Redis).
    """

    redis_url: str
    job_timeout: int
    concurrency: int


class ModelConfig(BaseModel):
    """
    Diarization model settings.
    """

    checkpoint: str = "pyannote/speaker-diarization-3.1"
    auth_token: str | None = None


class InferenceConfig(BaseModel):
    """
    Inference and device selection settings.
    """

    device: Device = Device.CPU


class AudioConfig(BaseModel):
    """
    Audio ingestion and storage settings.
    """

    spool_dir: str = "/data/spool"
    allowed_formats: list[AudioFormat] = [
        AudioFormat.WAV,
        AudioFormat.MP3,
        AudioFormat.M4A,
        AudioFormat.FLAC,
        AudioFormat.OGG,
    ]
    max_duration_sec: int
    max_upload_mb: int


class LoggingConfig(BaseModel):
    """
    Logging settings.
    """

    level: LogLevel = LogLevel.INFO


class AppConfig(BaseSettings):
    """
    Root settings combining yaml and environment variables.
    """

    model_config = SettingsConfigDict(
        yaml_file="/app/config.yaml",
        env_prefix="DIARIZER_",
        env_nested_delimiter="__",
        extra="ignore",
        protected_namespaces=(),
    )

    queue: QueueConfig
    model: ModelConfig = ModelConfig()
    inference: InferenceConfig = InferenceConfig()
    audio: AudioConfig
    logging: LoggingConfig = LoggingConfig()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """
        Order the settings sources so environment variables override yaml.

        :param settings_cls: Settings class being configured.
        :param init_settings: Values passed directly to the constructor.
        :param env_settings: Values read from environment variables.
        :param dotenv_settings: Values read from a dotenv file.
        :param file_secret_settings: Values read from secret files.
        :return: Ordered tuple of settings sources.
        """
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )
