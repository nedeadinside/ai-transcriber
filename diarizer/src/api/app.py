import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI

from audio.io import AudioSpool
from config import load_config

from .routes import router


def create_app() -> FastAPI:
    """
    Build and configure the application.

    :return: The configured application.
    """
    cfg = load_config()
    logging.basicConfig(level=cfg.logging.level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """
        Attach shared state and open the ARQ redis pool for the app lifetime.

        :param app: Application instance.
        """
        app.state.cfg = cfg
        app.state.audio_spool = AudioSpool(cfg)
        app.state.redis = await create_pool(RedisSettings.from_dsn(cfg.queue.redis_url))
        yield
        await app.state.redis.aclose()

    app = FastAPI(lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
