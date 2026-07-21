from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict

from core.config import BaseAppConfig
from enums import Device


class ModelConfig(BaseModel):
    """
    Diarization model settings.
    """

    checkpoint: str
    auth_token: str | None = None


class InferenceConfig(BaseModel):
    """
    Inference and device selection settings.
    """

    device: Device


class AppConfig(BaseAppConfig):
    """
    Root settings for the diarizer.
    """

    model_config = SettingsConfigDict(
        yaml_config_section="diarizer",
        env_prefix="DIARIZER_",
    )

    model: ModelConfig
    inference: InferenceConfig
