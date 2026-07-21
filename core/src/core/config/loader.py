from functools import lru_cache

from .models import BaseAppConfig


@lru_cache
def load_config[C: BaseAppConfig](config_cls: type[C]) -> C:
    """
    Return the cached settings instance for a service's config class.

    :param config_cls: The service's BaseAppConfig subclass to instantiate.
    :return: The validated settings, cached per class.
    """
    return config_cls()
