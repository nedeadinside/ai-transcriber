FROM python:3.12-slim-trixie

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

ARG TORCH_EXTRA=cpu
COPY pyproject.toml uv.lock .python-version ./
COPY diarizer/pyproject.toml diarizer/
RUN uv sync --frozen --package diarizer --extra ${TORCH_EXTRA}

COPY core ./core
COPY diarizer/src ./diarizer/src

ENV PYTHONPATH=/app/diarizer/src:/app
ENV PATH=/app/.venv/bin:$PATH
