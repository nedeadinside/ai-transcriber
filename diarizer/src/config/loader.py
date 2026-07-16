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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _cfg = load_config()
    assert _cfg.queue.redis_url, "redis_url must be set"  # noqa: S101
    logger.info("%s", _cfg.model_dump())
