import uuid
from typing import Any

import pytest

from app.config.settings import Settings
from app.reels.jobs import trigger_reel_job


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return {"name": "projects/case-theory/locations/us-central1/operations/test-operation"}


class FakeAsyncClient:
    request: tuple[str, dict[str, Any]] | None = None

    def __init__(self, **_: Any) -> None:
        pass

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.__class__.request = (url, kwargs)
        return FakeResponse()


@pytest.mark.asyncio
async def test_trigger_reel_job_targets_selected_case(monkeypatch: pytest.MonkeyPatch) -> None:
    case_id = uuid.UUID("6705f163-9dba-452c-9773-f1ef1e60c8bc")
    settings = Settings(
        _env_file=None,
        reel_job_project_id="case-theory",
        reel_job_location="us-central1",
        reel_job_name="case-theory-stg-youtube-short",
    )
    monkeypatch.setattr("app.reels.jobs._access_token", lambda: "access-token")
    monkeypatch.setattr("app.reels.jobs.httpx.AsyncClient", FakeAsyncClient)

    operation_name = await trigger_reel_job(settings, case_id)

    assert operation_name.endswith("/test-operation")
    assert FakeAsyncClient.request is not None
    url, request = FakeAsyncClient.request
    assert url.endswith("/jobs/case-theory-stg-youtube-short:run")
    assert request["headers"] == {"Authorization": "Bearer access-token"}
    assert request["json"] == {
        "overrides": {
            "containerOverrides": [
                {"args": ["--force-new", "--case-id", str(case_id)]},
            ]
        }
    }
