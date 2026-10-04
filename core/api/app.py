import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import TYPE_CHECKING

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from core.audio.io import AudioSpool
from core.errors import AudioError, AudioTooLargeError

if TYPE_CHECKING:
    from core.config.models import BaseAppConfig

health_router = APIRouter()


@health_router.get("/health")
async def health(request: Request) -> dict[str, str]:
    """
    Report service liveness.

    :param request: Incoming request, holding the ARQ redis pool.
    :return: Service health payload.
    """
    await request.app.state.redis.ping()
    return {"status": "ok"}


async def audio_error_handler(request: Request, exc: Exception) -> JSONResponse:  # noqa: ARG001
    """
    Turn a rejected upload into the status code that describes why it was rejected.

    Registered against AudioError; starlette matches handlers by walking the exception's
    MRO, so every subclass lands here and no route repeats the mapping.

    :param request: Incoming request.
    :param exc: The raised audio error.
    :return: Error response.
    """
    status = (
        HTTPStatus.REQUEST_ENTITY_TOO_LARGE
        if isinstance(exc, AudioTooLargeError)
        else HTTPStatus.BAD_REQUEST
    )
    return JSONResponse(status_code=status, content={"detail": str(exc)})


def create_app(cfg: "BaseAppConfig", router: APIRouter) -> FastAPI:
    """
    Build and configure the application.

    :param cfg: Root settings.
    :param router: Service routes, mounted alongside the shared health route.
    :return: The configured application.
    """
    logging.basicConfig(level=cfg.logging.level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """
        Attach shared state and open the ARQ redis pool for the app lifetime.

        :param app: Application instance.
        """
        app.state.cfg = cfg
        app.state.audio_spool = AudioSpool(cfg.audio)
        app.state.redis = await create_pool(RedisSettings.from_dsn(cfg.queue.redis_url))
        yield
        await app.state.redis.aclose()

    app = FastAPI(lifespan=lifespan)
    app.add_exception_handler(AudioError, audio_error_handler)
    app.include_router(router)
    app.include_router(health_router)
    return app
