from functools import lru_cache

from .models import YamlSettings


@lru_cache
def load_config[C: YamlSettings](config_cls: type[C]) -> C:
    """
    Return the cached settings instance for a service's config class.

    :param config_cls: The service's settings class to instantiate.
    :return: The validated settings, cached per class.
    """
    return config_cls()
