import uuid
from urllib.parse import urlparse

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.cases.models import Case, CaseMember
from app.db.session import SessionFactory
from app.users.models import User

pytestmark = pytest.mark.usefixtures("paid_signups")


async def _csrf(client: AsyncClient) -> str:
    return (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]


async def _register(
    client: AsyncClient, token: str, *, email: str, username: str, display_name: str
) -> None:
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


async def test_invitation_acceptance_grants_private_access_and_adds_my_desk(
    client: AsyncClient,
) -> None:
    token = await _csrf(client)
    await _register(
        client,
        token,
        email="invite-owner@example.com",
        username="invite_owner",
        display_name="Pablo",
    )
    created = await client.post(
        "/api/v1/cases",
        headers={"X-CSRF-Token": token},
        json={
            "victim_names": "Fictional River Case",
            "creation_mode": "manual",
            "summary": "A fictional case used to test private collaboration.",
            "banner_template": "/case-banners/mountain-trail.jpg",
        },
    )
    assert created.status_code == 202
    case_id = created.json()["id"]
    async with SessionFactory() as db:
        case = await db.scalar(select(Case).where(Case.id == uuid.UUID(case_id)))
        assert case is not None
        case.privacy = "private"
        await db.commit()

    invitation = await client.post(
        f"/api/v1/cases/{case_id}/invitations",
        headers={"X-CSRF-Token": token},
        json={"role": "contributor"},
    )
    assert invitation.status_code == 201
    payload = invitation.json()
    assert payload["inviter_name"] == "Pablo"
    assert "Pablo invited you to collaborate" in payload["message"]
    raw_token = urlparse(payload["invite_url"]).path.rsplit("/", 1)[-1]

    await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})
    preview = await client.get(f"/api/v1/invitations/{raw_token}")
    assert preview.status_code == 200
    assert preview.json()["case_title"] == "Fictional River Case"
    assert preview.json()["is_available"] is True
    assert (await client.get(f"/api/v1/cases/{case_id}")).status_code == 404
    unauthenticated = await client.post(
        f"/api/v1/invitations/{raw_token}/accept",
        headers={"X-CSRF-Token": token},
    )
    assert unauthenticated.status_code == 401

    await _register(
        client,
        token,
        email="invited-friend@example.com",
        username="invited_friend",
        display_name="Invited Friend",
    )
    accepted = await client.post(
        f"/api/v1/invitations/{raw_token}/accept",
        headers={"X-CSRF-Token": token},
    )
    assert accepted.status_code == 200
    assert accepted.json()["case_id"] == case_id
    assert (await client.get(f"/api/v1/cases/{case_id}")).status_code == 200
    desk = await client.get("/api/v1/cases/following")
    assert [item["id"] for item in desk.json()] == [case_id]
    async with SessionFactory() as db:
        invited_user = await db.scalar(select(User).where(User.email == "invited-friend@example.com"))
        assert invited_user is not None
        member = await db.scalar(
            select(CaseMember).where(
                CaseMember.case_id == uuid.UUID(case_id),
                CaseMember.user_id == invited_user.id,
            )
        )
        assert member is not None
        assert member.role == "contributor"

    reused = await client.post(
        f"/api/v1/invitations/{raw_token}/accept",
        headers={"X-CSRF-Token": token},
    )
    assert reused.status_code == 410


async def test_public_case_participant_can_invite(client: AsyncClient) -> None:
    token = await _csrf(client)
    await _register(
        client,
        token,
        email="first-owner@example.com",
        username="first_owner",
        display_name="First Owner",
    )
    case_id = (
        await client.post(
            "/api/v1/cases",
            headers={"X-CSRF-Token": token},
            json={
                "victim_names": "Fictional Public Case",
                "creation_mode": "manual",
                "summary": "A fictional public case used for invitation authorization testing.",
                "banner_template": "/case-banners/archive-room.jpg",
            },
        )
    ).json()["id"]
    await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})
    await _register(
        client,
        token,
        email="not-owner@example.com",
        username="not_owner",
        display_name="Not Owner",
    )
    invitation = await client.post(
        f"/api/v1/cases/{case_id}/invitations",
        headers={"X-CSRF-Token": token},
        json={"role": "contributor"},
    )
    assert invitation.status_code == 201
    assert invitation.json()["case_id"] == case_id
