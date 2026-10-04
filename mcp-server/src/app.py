import logging
from pathlib import Path
from typing import Any

import httpx
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from client import TranscriberClient
from config import AppConfig, load_config

cfg: AppConfig = load_config()
logging.basicConfig(level=cfg.logging.level)

mcp = MCPServer("transcriber")


def resolve_in_pool(path: str, pool_dir: str) -> Path:
    """
    Resolve an agent-supplied path to a file inside the shared pool.

    :param path: Absolute path, or path relative to the pool root.
    :param pool_dir: Root of the shared pool.
    :raises ToolError: If the path leaves the pool or names no file.
    :return: The resolved file path.
    """
    pool = Path(pool_dir).resolve()
    file = (pool / path).resolve()
    if not file.is_relative_to(pool):
        raise ToolError(f"path is outside the file pool: {path}")
    if not file.is_file():
        raise ToolError(f"no such file in the pool: {path}")
    return file


@mcp.tool()
async def transcribe(
    path: str,
    ctx: Context,
    raw: bool = False,
    diarized: bool = False,
    summary: bool = False,
) -> dict[str, Any]:
    """
    Transcribe an audio file from the shared pool and return the requested artifacts.

    :param path: Path of the audio file in the pool, as the upload reported it.
    :param ctx: Request context used to report progress.
    :param raw: Whether to return the plain transcript segments.
    :param diarized: Whether to return segments labelled by speaker.
    :param summary: Whether to return a summary of the conversation.
    :return: One key per requested artifact.
    """
    file = resolve_in_pool(path, cfg.pool.dir)

    async def on_poll(polls: int) -> None:
        """
        Report that the job is still running.

        :param polls: Number of polls so far.
        """
        await ctx.report_progress(polls, message="transcription in progress")

    async with httpx.AsyncClient() as http:
        client = TranscriberClient(cfg.transcriber, http)
        return await client.run(
            file, {"raw": raw, "diarized": diarized, "summary": summary}, on_poll
        )


app = mcp.streamable_http_app(host="0.0.0.0")
