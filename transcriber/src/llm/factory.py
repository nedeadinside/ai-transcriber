from typing import TYPE_CHECKING

from langchain.chat_models import init_chat_model

from errors import LLMError

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

    from config.models import LLMConfig


def build_llm(cfg: "LLMConfig") -> "BaseChatModel":
    """
    Build the chat model described by the config.

    ``init_chat_model`` maps the standard parameters onto whatever the provider package calls
    them, so the same config keys work for every provider.

    :param cfg: Chat model settings.
    :raises LLMError: If the provider is unavailable or rejects the settings.
    :return: The chat model.
    """
    kwargs = dict(cfg.params)
    if cfg.api_key is not None:
        kwargs["api_key"] = cfg.api_key.get_secret_value()
    try:
        return init_chat_model(
            cfg.model,
            model_provider=cfg.provider,
            temperature=cfg.temperature,
            **kwargs,
        )
    except Exception as e:
        raise LLMError(f"cannot build chat model {cfg.provider}:{cfg.model}: {e}") from e
