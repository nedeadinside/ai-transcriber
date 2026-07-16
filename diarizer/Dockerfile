FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

ARG TORCH_EXTRA=cpu
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --extra ${TORCH_EXTRA}

COPY src ./src
ENV PYTHONPATH=/app/src
ENV PATH=/app/.venv/bin:$PATH
