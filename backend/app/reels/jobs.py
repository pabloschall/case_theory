"""Start manual reel executions on the configured Cloud Run job."""

import asyncio
import uuid
from typing import Any

import httpx

from app.common.errors import AppError
from app.config.settings import Settings

CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


def _access_token() -> str:
    import google.auth  # type: ignore[import-not-found]
    from google.auth.transport.requests import Request  # type: ignore[import-not-found]

    credentials, _ = google.auth.default(scopes=[CLOUD_PLATFORM_SCOPE])
    credentials.refresh(Request())
    token = credentials.token
    if not isinstance(token, str) or not token:
        raise RuntimeError("Google application credentials returned no access token")
    return token


async def trigger_reel_job(settings: Settings, case_id: uuid.UUID) -> str:
    if not all((settings.reel_job_project_id, settings.reel_job_location, settings.reel_job_name)):
        raise AppError(503, "reel_job_unavailable", "YouTube Short generation is not configured")
    try:
        token = await asyncio.to_thread(_access_token)
        url = (
            "https://run.googleapis.com/v2/projects/"
            f"{settings.reel_job_project_id}/locations/{settings.reel_job_location}/jobs/"
            f"{settings.reel_job_name}:run"
        )
        payload: dict[str, Any] = {
            "overrides": {
                "containerOverrides": [
                    {"args": ["--force-new", "--case-id", str(case_id)]},
                ]
            }
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
            response.raise_for_status()
        operation_name = response.json().get("name")
        if not isinstance(operation_name, str) or not operation_name:
            raise RuntimeError("Cloud Run returned no operation name")
        return operation_name
    except AppError:
        raise
    except Exception as exc:
        raise AppError(
            502,
            "reel_job_start_failed",
            "The YouTube Short job could not be started",
        ) from exc
