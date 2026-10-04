from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict

from core.config import LoggingConfig, YamlSettings, load_config as _load_config


class TranscriberConfig(BaseModel):
    """
    Settings for the transcriber service this server forwards to.
    """

    url: str
    poll_interval_sec: float
    timeout_sec: int


class PoolConfig(BaseModel):
    """
    Settings for the shared directory the agent's files land in.
    """

    dir: str


class AppConfig(YamlSettings):
    """
    Root settings for the MCP server.
    """

    model_config = SettingsConfigDict(
        yaml_config_section="mcp",
        env_prefix="MCP_",
    )

    transcriber: TranscriberConfig
    pool: PoolConfig
    logging: LoggingConfig


def load_config() -> AppConfig:
    """
    Return the cached settings instance for this service.

    :return: The validated settings.
    """
    return _load_config(AppConfig)
