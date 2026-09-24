import pytest
from httpx import AsyncClient

from app.main import app
from app.storage.base import ObjectMetadata, StorageProvider
from app.storage.provider import get_storage_provider

pytestmark = pytest.mark.usefixtures("paid_signups")


class MemoryStorage(StorageProvider):
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    async def put(self, object_key: str, content: bytes, content_type: str) -> None:
        self.objects[object_key] = (content, content_type)

    async def create_upload_url(self, object_key: str, content_type: str) -> tuple[str, str]:
        self.objects[object_key] = (b"\x89PNG\r\n\x1a\nprofile", content_type)
        return f"http://storage.test/{object_key}", "PUT"

    async def create_download_url(self, object_key: str) -> str:
        return f"http://storage.test/{object_key}?signed=true"

    async def metadata(self, object_key: str) -> ObjectMetadata:
        content, content_type = self.objects[object_key]
        return ObjectMetadata(size=len(content), content_type=content_type)

    async def read(self, object_key: str) -> bytes:
        return self.objects[object_key][0]

    async def delete(self, object_key: str) -> None:
        self.objects.pop(object_key, None)


async def _csrf(client: AsyncClient) -> str:
    return (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]


async def _register(
    client: AsyncClient, token: str, *, email: str, username: str, display_name: str
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": email,
            "username": username,
            "display_name": display_name,
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    assert response.status_code == 201
    return (await client.get("/api/v1/users/me")).json()


async def test_profile_edit_and_avatar_upload(client: AsyncClient) -> None:
    storage = MemoryStorage()
    app.dependency_overrides[get_storage_provider] = lambda: storage
    try:
        token = await _csrf(client)
        user = await _register(
            client,
            token,
            email="profile@example.com",
            username="profile_user",
            display_name="Profile User",
        )
        updated = await client.patch(
            "/api/v1/users/me",
            headers={"X-CSRF-Token": token},
            json={
                "display_name": "Case Researcher",
                "username": "case_researcher",
                "bio": "I research public records and historical cases.",
            },
        )
        assert updated.status_code == 200
        assert updated.json()["display_name"] == "Case Researcher"
        assert updated.json()["bio"] == "I research public records and historical cases."

        ticket = await client.post(
            "/api/v1/users/me/avatar",
            headers={"X-CSRF-Token": token},
            json={"filename": "portrait.png", "content_type": "image/png", "file_size": 15},
        )
        assert ticket.status_code == 201
        completed = await client.post(
            f"/api/v1/users/me/avatar/{ticket.json()['upload_id']}/complete",
            headers={"X-CSRF-Token": token},
        )
        assert completed.status_code == 200
        assert completed.json()["avatar_url"] == f"/api/v1/users/{user['id']}/avatar"

        avatar = await client.get(f"/api/v1/users/{user['id']}/avatar", follow_redirects=False)
        assert avatar.status_code == 307
        assert avatar.headers["location"].endswith("?signed=true")
    finally:
        app.dependency_overrides.pop(get_storage_provider, None)


async def test_blocking_prevents_messages_until_unblocked(client: AsyncClient) -> None:
    token = await _csrf(client)
    first = await _register(
        client,
        token,
        email="block-one@example.com",
        username="block_one",
        display_name="Block One",
    )
    await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})
    second = await _register(
        client,
        token,
        email="block-two@example.com",
        username="block_two",
        display_name="Block Two",
    )
    blocked = await client.post(
        f"/api/v1/users/{first['id']}/block", headers={"X-CSRF-Token": token}
    )
    assert blocked.status_code == 200
    assert blocked.json() == {"is_blocked": True}
    profile = await client.get(f"/api/v1/users/{first['id']}")
    assert profile.json()["is_blocked_by_me"] is True
    blocked_list = await client.get("/api/v1/users/me/blocked")
    assert [item["id"] for item in blocked_list.json()] == [first["id"]]

    conversation = await client.post(
        "/api/v1/messages/conversations",
        headers={"X-CSRF-Token": token},
        json={"recipient_user_id": first["id"]},
    )
    assert conversation.status_code == 403
    assert conversation.json()["error"]["code"] == "messaging_blocked"

    unblocked = await client.delete(
        f"/api/v1/users/{first['id']}/block", headers={"X-CSRF-Token": token}
    )
    assert unblocked.json() == {"is_blocked": False}
    opened = await client.post(
        "/api/v1/messages/conversations",
        headers={"X-CSRF-Token": token},
        json={"recipient_user_id": first["id"]},
    )
    assert opened.status_code == 201
    assert second["id"] != first["id"]
