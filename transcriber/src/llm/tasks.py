from typing import TYPE_CHECKING

from langchain_core.output_parsers import StrOutputParser

from errors import LLMError

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

    from .prompts import Prompts


async def summarize(llm: "BaseChatModel", prompts: "Prompts", text: str) -> str:
    """
    Ask the LLM to summarize a transcript.

    :param llm: Chat model.
    :param prompts: Loaded prompt templates.
    :param text: Transcript to summarize.
    :raises LLMError: If the model call fails.
    :return: The summary.
    """
    chain = prompts.summarize | llm | StrOutputParser()
    try:
        return (await chain.ainvoke({"transcript": text})).strip()
    except Exception as e:
        raise LLMError(f"summarize failed: {e}") from e
