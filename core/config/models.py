from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from core.enums import AudioFormat, LogLevel


class QueueConfig(BaseModel):
    """
    Task queue settings (ARQ over a single Redis).
    """

    redis_url: str
    job_timeout: int
    concurrency: int


class AudioConfig(BaseModel):
    """
    Audio ingestion and storage settings.
    """

    spool_dir: str
    allowed_formats: list[AudioFormat]
    max_duration_sec: int
    max_upload_mb: int


class LoggingConfig(BaseModel):
    """
    Logging settings.
    """

    level: LogLevel


class YamlSettings(BaseSettings):
    """
    Settings read from the shared yaml file, with environment variables taking precedence.

    Each service subclasses this and sets its own yaml_config_section and env_prefix;
    pydantic merges that model_config over this one, so the rest carries over.
    """

    model_config = SettingsConfigDict(
        yaml_file="/app/config.yaml",
        env_nested_delimiter="__",
        extra="ignore",
        protected_namespaces=(),
    )

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
        Add the yaml source and order it so environment variables win.

        :return: Ordered tuple of settings sources, earliest wins.
        """
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )


class BaseAppConfig(YamlSettings):
    """
    Root settings shared by every queue-backed service.
    """

    queue: QueueConfig
    audio: AudioConfig
    logging: LoggingConfig
