import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import BASE_DIR, settings
from app.core.exceptions import register_exception_handlers
from app.database.connection import close_database_connection, engine
from app.redis.pubsub_manager import start_listener, stop_listener
from app.redis.redis_connection import close_redis, get_redis, init_redis
from app.routers import api_router
from app.routers.websocket import router as websocket_router

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Redis is optional: without it the app still serves REST and realtime
    # traffic for a single process (in-memory fallbacks).
    await init_redis()
    await start_listener()
    try:
        yield
    finally:
        await stop_listener()
        await close_redis()
        await close_database_connection()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Realtime chat and notification API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(api_router, prefix="/api/v1")
app.include_router(websocket_router)


FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"


@app.get("/", include_in_schema=False)
async def root():
    """Serve the built SPA when available, otherwise the API docs."""
    if FRONTEND_INDEX.is_file():
        return FileResponse(FRONTEND_INDEX)
    return RedirectResponse("/docs")


@app.get("/health", tags=["health"], summary="Liveness / readiness probe")
async def health() -> dict[str, str]:
    database = "up"
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        database = "down"

    redis_state = "unavailable"
    client = get_redis()
    if client is not None:
        try:
            await client.ping()
            redis_state = "up"
        except Exception:
            redis_state = "down"

    return {
        "status": "ok" if database == "up" else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": database,
        "redis": redis_state,
    }


# Mounted last so /api, /ws, /docs and /health keep working. Building the
# frontend (npm run build in frontend/) makes the whole app available on :8000.
if FRONTEND_INDEX.is_file():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
