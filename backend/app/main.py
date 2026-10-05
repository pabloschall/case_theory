from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles

from app.admin.routes import router as admin_router
from app.auth.routes import router as auth_router
from app.cases.routes import router as cases_router
from app.common.errors import AppError, app_error_handler
from app.config.logging import configure_logging
from app.config.middleware import RequestContextMiddleware
from app.config.settings import get_settings
from app.discussions.routes import router as discussions_router
from app.evidence.routes import router as evidence_router
from app.integrations.fbi.routes import router as fbi_router
from app.integrations.youtube.routes import router as youtube_router
from app.invitations.routes import router as invitations_router
from app.maps.routes import router as maps_router
from app.messaging.routes import router as messaging_router
from app.moderation.routes import router as moderation_router
from app.notes.routes import router as notes_router
from app.people.routes import router as people_router
from app.progression.routes import router as progression_router
from app.reels.routes import router as reels_router
from app.seo import router as seo_router
from app.subscriptions.routes import router as subscription_router
from app.users.routes import router as user_router

settings = get_settings()
configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    yield
    await app.state.redis.aclose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/api/docs" if settings.environment != "production" else None,
    openapi_url="/api/openapi.json" if settings.environment != "production" else None,
    lifespan=lifespan,
)
app.add_exception_handler(AppError, app_error_handler)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID"],
)

app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(user_router, prefix=settings.api_prefix)
app.include_router(subscription_router, prefix=settings.api_prefix)
app.include_router(cases_router, prefix=settings.api_prefix)
app.include_router(discussions_router, prefix=settings.api_prefix)
app.include_router(evidence_router, prefix=settings.api_prefix)
app.include_router(maps_router, prefix=settings.api_prefix)
app.include_router(people_router, prefix=settings.api_prefix)
app.include_router(progression_router, prefix=settings.api_prefix)
app.include_router(reels_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(fbi_router, prefix=settings.api_prefix)
app.include_router(youtube_router, prefix=settings.api_prefix)
app.include_router(invitations_router, prefix=settings.api_prefix)
app.include_router(messaging_router, prefix=settings.api_prefix)
app.include_router(notes_router, prefix=settings.api_prefix)
app.include_router(moderation_router, prefix=settings.api_prefix)
app.include_router(seo_router)
if settings.storage_provider == "fake_gcs":
    app.mount("/media", StaticFiles(directory=settings.local_storage_path, check_dir=False), name="media")


@app.get("/health", tags=["operations"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
