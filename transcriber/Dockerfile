FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
COPY core/pyproject.toml core/
COPY transcriber/pyproject.toml transcriber/
RUN uv sync --frozen --no-install-workspace --package transcriber

COPY core ./core
COPY transcriber/src ./transcriber/src
RUN uv sync --frozen --package transcriber

ENV PYTHONPATH=/app/transcriber/src
ENV PATH=/app/.venv/bin:$PATH
