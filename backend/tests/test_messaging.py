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
        self.objects[object_key] = (b"\xff\xd8\xffmessage photo", content_type)
        return f"http://storage.test/{object_key}", "PUT"

    async def create_download_url(self, object_key: str) -> str:
        return f"http://storage.test/{object_key}?signed=true"

    async def metadata(self, object_key: str) -> ObjectMetadata:
        content, content_type = self.objects[object_key]
        return ObjectMetadata(len(content), content_type)

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


async def test_direct_messages_with_private_file_attachments(client: AsyncClient) -> None:
    storage = MemoryStorage()
    app.dependency_overrides[get_storage_provider] = lambda: storage
    try:
        token = await _csrf(client)
        first = await _register(
            client,
            token,
            email="message-one@example.com",
            username="message_one",
            display_name="First Investigator",
        )
        await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})
        second = await _register(
            client,
            token,
            email="message-two@example.com",
            username="message_two",
            display_name="Second Investigator",
        )
        profile = await client.get(f"/api/v1/users/{first['id']}")
        assert profile.status_code == 200
        assert profile.json()["display_name"] == "First Investigator"

        opened = await client.post(
            "/api/v1/messages/conversations",
            headers={"X-CSRF-Token": token},
            json={"recipient_user_id": first["id"]},
        )
        assert opened.status_code == 201
        conversation_id = opened.json()["id"]

        ticket = await client.post(
            f"/api/v1/messages/conversations/{conversation_id}/attachments",
            headers={"X-CSRF-Token": token},
            json={
                "filename": "scene-photo.jpg",
                "content_type": "image/jpeg",
                "file_size": 16,
            },
        )
        assert ticket.status_code == 201
        attachment_id = ticket.json()["attachment"]["id"]
        completed = await client.post(
            f"/api/v1/messages/conversations/{conversation_id}/attachments/"
            f"{attachment_id}/complete",
            headers={"X-CSRF-Token": token},
        )
        assert completed.status_code == 200
        assert completed.json()["status"] == "available"

        sent = await client.post(
            f"/api/v1/messages/conversations/{conversation_id}/messages",
            headers={"X-CSRF-Token": token},
            json={
                "body": "This photo may clarify the location.",
                "attachment_ids": [attachment_id],
            },
        )
        assert sent.status_code == 200
        message = sent.json()
        assert message["sender"]["id"] == second["id"]
        assert message["attachments"][0]["original_filename"] == "scene-photo.jpg"

        second_message = await client.post(
            f"/api/v1/messages/conversations/{conversation_id}/messages",
            headers={"X-CSRF-Token": token},
            json={"body": "I added a second note for pagination.", "attachment_ids": []},
        )
        assert second_message.status_code == 200

        latest = await client.get(
            f"/api/v1/messages/conversations/{conversation_id}", params={"limit": 1}
        )
        assert latest.status_code == 200
        assert latest.json()["total_messages"] == 2
        assert latest.json()["has_more"] is True
        assert latest.json()["next_cursor"]
        assert latest.json()["messages"][0]["id"] == second_message.json()["id"]
        earlier = await client.get(
            f"/api/v1/messages/conversations/{conversation_id}",
            params={"limit": 1, "cursor": latest.json()["next_cursor"]},
        )
        assert earlier.status_code == 200
        assert earlier.json()["has_more"] is False
        assert earlier.json()["messages"][0]["id"] == message["id"]

        signed = await client.get(
            f"/api/v1/messages/conversations/{conversation_id}/attachments/"
            f"{attachment_id}/url"
        )
        assert signed.status_code == 200
        assert signed.json()["url"].endswith("?signed=true")

        conversations = await client.get("/api/v1/messages/conversations")
        assert conversations.status_code == 200
        assert conversations.json()["items"][0]["other_user"]["id"] == first["id"]
        assert conversations.json()["items"][0]["last_message"] == "I added a second note for pagination."
        assert conversations.json()["total"] == 1
        assert conversations.json()["has_more"] is False
    finally:
        app.dependency_overrides.pop(get_storage_provider, None)


async def test_conversation_access_is_limited_to_participants(client: AsyncClient) -> None:
    token = await _csrf(client)
    first = await _register(
        client,
        token,
        email="private-message-one@example.com",
        username="private_message_one",
        display_name="Message One",
    )
    await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})
    second = await _register(
        client,
        token,
        email="private-message-two@example.com",
        username="private_message_two",
        display_name="Message Two",
    )
    conversation = await client.post(
        "/api/v1/messages/conversations",
        headers={"X-CSRF-Token": token},
        json={"recipient_user_id": first["id"]},
    )
    assert conversation.status_code == 201
    await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})
    await _register(
        client,
        token,
        email="message-outsider@example.com",
        username="message_outsider",
        display_name="Outsider",
    )
    blocked = await client.get(f"/api/v1/messages/conversations/{conversation.json()['id']}")
    assert blocked.status_code == 404
    assert second["id"] != first["id"]


async def test_conversation_list_uses_cursor_pagination(client: AsyncClient) -> None:
    token = await _csrf(client)
    owner = await _register(
        client,
        token,
        email="message-owner@example.com",
        username="message_owner",
        display_name="Message Owner",
    )
    await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})
    first = await _register(
        client,
        token,
        email="message-contact-one@example.com",
        username="message_contact_one",
        display_name="First Contact",
    )
    await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})
    second = await _register(
        client,
        token,
        email="message-contact-two@example.com",
        username="message_contact_two",
        display_name="Second Contact",
    )
    await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})
    logged_in = await client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": token},
        json={"email": "message-owner@example.com", "password": "sourcework123"},
    )
    assert logged_in.status_code == 200

    for contact in (first, second):
        opened = await client.post(
            "/api/v1/messages/conversations",
            headers={"X-CSRF-Token": token},
            json={"recipient_user_id": contact["id"]},
        )
        assert opened.status_code == 201

    first_page = await client.get(
        "/api/v1/messages/conversations", params={"limit": 1}
    )
    assert first_page.status_code == 200
    assert first_page.json()["total"] == 2
    assert first_page.json()["has_more"] is True
    assert first_page.json()["next_cursor"]
    second_page = await client.get(
        "/api/v1/messages/conversations",
        params={"limit": 1, "cursor": first_page.json()["next_cursor"]},
    )
    assert second_page.status_code == 200
    assert second_page.json()["has_more"] is False
    assert first_page.json()["items"][0]["id"] != second_page.json()["items"][0]["id"]
    assert owner["id"]
