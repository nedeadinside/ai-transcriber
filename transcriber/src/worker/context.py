from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    import httpx
    from langchain_core.language_models.chat_models import BaseChatModel

    from clients.diarizer import DiarizerClient
    from clients.whisper import WhisperClient
    from llm.prompts import Prompts


class WorkerContext(TypedDict):
    """
    Partial view of the ARQ worker context, covering the keys this app populates and reads.

    ARQ injects its own keys too (``redis``, ``job_try`` and so on); only what the app touches
    is declared here.
    """

    http: "httpx.AsyncClient"
    whisper: "WhisperClient"
    diarizer: "DiarizerClient"
    prompts: "Prompts"
    llm: "BaseChatModel"
    job_id: str
