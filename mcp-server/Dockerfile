FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
COPY mcp-server/pyproject.toml mcp-server/
RUN uv sync --frozen --package mcp-server

COPY core ./core
COPY mcp-server/src ./mcp-server/src

ENV PYTHONPATH=/app/mcp-server/src:/app
ENV PATH=/app/.venv/bin:$PATH
