import logging
from functools import lru_cache

from .models import AppConfig

logger = logging.getLogger(__name__)


@lru_cache
def load_config() -> AppConfig:
    """
    Return the cached settings instance.

    :return: The validated settings.
    """
    return AppConfig()
