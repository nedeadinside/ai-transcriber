FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
COPY transcriber/pyproject.toml transcriber/
RUN uv sync --frozen --package transcriber

COPY core ./core
COPY transcriber/src ./transcriber/src

ENV PYTHONPATH=/app/transcriber/src:/app
ENV PATH=/app/.venv/bin:$PATH
