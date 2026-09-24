import uuid

import pytest
from httpx import AsyncClient
from pytest import MonkeyPatch

from app.cases import routes as case_routes
from app.cases.models import TimelineEvent
from app.db.session import SessionFactory
from app.main import app
from app.storage.base import ObjectMetadata, StorageProvider
from app.storage.provider import get_storage_provider

pytestmark = pytest.mark.usefixtures("paid_signups")


class StubTask:
    def delay(self, case_id: str, job_id: str) -> None:
        assert case_id
        assert job_id


class MemoryStorage(StorageProvider):
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put(self, object_key: str, content: bytes, content_type: str) -> None:
        self.objects[object_key] = content

    async def create_upload_url(self, object_key: str, content_type: str) -> tuple[str, str]:
        self.objects[object_key] = b"%PDF-1.7\nfictional evidence"
        return f"http://storage.test/{object_key}", "PUT"

    async def create_download_url(self, object_key: str) -> str:
        return f"http://storage.test/{object_key}?signed=true"

    async def metadata(self, object_key: str) -> ObjectMetadata:
        return ObjectMetadata(len(self.objects[object_key]), "application/pdf")

    async def read(self, object_key: str) -> bytes:
        return self.objects[object_key]

    async def delete(self, object_key: str) -> None:
        self.objects.pop(object_key, None)


async def test_upload_link_and_reuse_evidence(client: AsyncClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(case_routes, "generate_case", StubTask())
    storage = MemoryStorage()
    app.dependency_overrides[get_storage_provider] = lambda: storage
    try:
        token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
        await client.post(
            "/api/v1/auth/register",
            headers={"X-CSRF-Token": token},
            json={
                "email": "evidence@example.com",
                "username": "evidence_user",
                "display_name": "Evidence User",
                "password": "sourcework123",
                "confirm_age_18": True,
                "accept_terms": True,
                "accept_community_standards": True,
            },
        )
        case_id = (
            await client.post(
                "/api/v1/cases",
                headers={"X-CSRF-Token": token},
                json={"victim_names": "Fictional Evidence Case"},
            )
        ).json()["id"]

        external = await client.post(
            f"/api/v1/cases/{case_id}/evidence/links",
            headers={"X-CSRF-Token": token},
            json={
                "title": "Public video archive",
                "url": "https://www.youtube.com/watch?v=fictional",
                "evidence_type": "video",
            },
        )
        assert external.status_code == 201
        external_id = external.json()["id"]

        ticket = await client.post(
            f"/api/v1/cases/{case_id}/evidence/uploads",
            headers={"X-CSRF-Token": token},
            json={
                "title": "Trail bulletin",
                "filename": "bulletin.pdf",
                "content_type": "application/pdf",
                "file_size": 28,
            },
        )
        assert ticket.status_code == 201
        assert ticket.json()["upload_method"] == "PUT"
        upload_id = ticket.json()["evidence"]["id"]
        completed = await client.post(
            f"/api/v1/cases/{case_id}/evidence/{upload_id}/complete",
            headers={"X-CSRF-Token": token},
        )
        assert completed.status_code == 200
        assert completed.json()["processing_status"] == "available"
        assert completed.json()["mime_type"] == "application/pdf"

        first_page = await client.get(
            f"/api/v1/cases/{case_id}/evidence", params={"limit": 1}
        )
        assert first_page.status_code == 200
        assert first_page.json()["total"] == 2
        assert first_page.json()["has_more"] is True
        assert first_page.json()["next_cursor"]
        second_page = await client.get(
            f"/api/v1/cases/{case_id}/evidence",
            params={"limit": 1, "cursor": first_page.json()["next_cursor"]},
        )
        assert second_page.status_code == 200
        assert second_page.json()["has_more"] is False
        assert first_page.json()["items"][0]["id"] != second_page.json()["items"][0]["id"]

        thread = await client.post(
            f"/api/v1/cases/{case_id}/discussions",
            headers={"X-CSRF-Token": token},
            json={
                "title": "Review the archive",
                "body": "This source may establish the public timeline.",
                "evidence_ids": [external_id, upload_id],
            },
        )
        assert thread.status_code == 201
        assert {item["id"] for item in thread.json()["evidence"]} == {external_id, upload_id}

        first_comment = await client.post(
            f"/api/v1/cases/{case_id}/evidence/{external_id}/comments",
            headers={"X-CSRF-Token": token},
            json={"body": "The publication date should be compared with the timeline."},
        )
        assert first_comment.status_code == 201
        assert first_comment.json()["can_delete"] is True
        second_comment = await client.post(
            f"/api/v1/cases/{case_id}/evidence/{external_id}/comments",
            headers={"X-CSRF-Token": token},
            json={"body": "The original upload may contain additional metadata."},
        )
        assert second_comment.status_code == 201
        comments = await client.get(
            f"/api/v1/cases/{case_id}/evidence/{external_id}/comments",
            params={"limit": 1},
        )
        assert comments.status_code == 200
        assert comments.json()["total"] == 2
        assert comments.json()["has_more"] is True
        older_comments = await client.get(
            f"/api/v1/cases/{case_id}/evidence/{external_id}/comments",
            params={"limit": 1, "cursor": comments.json()["next_cursor"]},
        )
        assert older_comments.status_code == 200
        assert older_comments.json()["has_more"] is False
        deleted_comment = await client.delete(
            f"/api/v1/cases/{case_id}/evidence/{external_id}/comments/{first_comment.json()['id']}",
            headers={"X-CSRF-Token": token},
        )
        assert deleted_comment.status_code == 204
        evidence_after_comment = await client.get(f"/api/v1/cases/{case_id}/evidence")
        commented_item = next(
            item for item in evidence_after_comment.json()["items"] if item["id"] == external_id
        )
        assert commented_item["comment_count"] == 1

        async with SessionFactory() as db:
            event = TimelineEvent(
                case_id=uuid.UUID(case_id),
                date_label="Date unknown",
                title="Candidate event",
                description="A candidate event requiring review.",
            )
            db.add(event)
            await db.commit()
            event_id = event.id

        attached = await client.post(
            f"/api/v1/cases/{case_id}/evidence/timeline/{event_id}",
            headers={"X-CSRF-Token": token},
            json={"evidence_id": external_id},
        )
        assert attached.status_code == 204
        opened = await client.get(f"/api/v1/cases/{case_id}")
        assert opened.json()["timeline"][0]["evidence"][0]["id"] == external_id

        signed = await client.get(f"/api/v1/cases/{case_id}/evidence/{upload_id}/url")
        assert signed.status_code == 200
        assert signed.json()["url"].endswith("?signed=true")
    finally:
        app.dependency_overrides.pop(get_storage_provider, None)


async def test_upload_rejects_extension_and_content_type_mismatch(
    client: AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(case_routes, "generate_case", StubTask())
    storage = MemoryStorage()
    app.dependency_overrides[get_storage_provider] = lambda: storage
    try:
        token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
        await client.post(
            "/api/v1/auth/register",
            headers={"X-CSRF-Token": token},
            json={
                "email": "invalid-upload@example.com",
                "username": "invalid_upload",
                "display_name": "Invalid Upload",
                "password": "sourcework123",
                "confirm_age_18": True,
                "accept_terms": True,
                "accept_community_standards": True,
            },
        )
        case_id = (
            await client.post(
                "/api/v1/cases",
                headers={"X-CSRF-Token": token},
                json={"victim_names": "Fictional Upload Case"},
            )
        ).json()["id"]
        response = await client.post(
            f"/api/v1/cases/{case_id}/evidence/uploads",
            headers={"X-CSRF-Token": token},
            json={
                "title": "Unsafe mismatch",
                "filename": "program.exe",
                "content_type": "application/pdf",
                "file_size": 100,
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "unsupported_file"
    finally:
        app.dependency_overrides.pop(get_storage_provider, None)
