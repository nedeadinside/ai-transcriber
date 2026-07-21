from core.config import load_config as _load_config

from .models import AppConfig


def load_config() -> AppConfig:
    """
    Return the cached settings instance for this service.

    :return: The validated settings.
    """
    return _load_config(AppConfig)


__all__ = ["AppConfig", "load_config"]
