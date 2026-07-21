from enum import StrEnum


class LLMProvider(StrEnum):
    """
    Chat model provider, named as ``init_chat_model`` expects it.
    """

    OPENAI = "openai"
    OLLAMA = "ollama"
