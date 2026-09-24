import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.auth.models import AccountActionToken, LegalAcceptance
from app.db.session import SessionFactory
from app.users.models import User


async def csrf(client: AsyncClient) -> str:
    response = await client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    return response.json()["csrf_token"]


async def test_register_current_user_and_logout(client: AsyncClient) -> None:
    token = await csrf(client)
    registered = await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "ada@example.com",
            "username": "ada_l",
            "display_name": "Ada L",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    assert registered.status_code == 201
    async with SessionFactory() as db:
        acceptances = list(
            await db.scalars(
                select(LegalAcceptance).order_by(LegalAcceptance.policy_type)
            )
        )
    assert {item.policy_type for item in acceptances} == {
        "age_requirement",
        "community_standards",
        "terms_of_use",
    }
    assert all(item.accepted_at is not None for item in acceptances)
    assert all(item.policy_version == "2026-09-22" for item in acceptances)
    assert all(len(item.document_checksum) == 64 for item in acceptances)
    assert all(item.request_id for item in acceptances)
    assert client.cookies.get("eillen_access")
    current = await client.get("/api/v1/users/me")
    assert current.status_code == 200
    assert current.json()["plan_code"] == "free"
    assert current.json()["tier_level"] == 1
    assert "case.create" in current.json()["permissions"]
    assert "case.create_ai" in current.json()["permissions"]
    assert current.json()["ai_cases_remaining"] == 1
    assert "ai.research" in current.json()["permissions"]
    assert current.json()["weekly_cases_remaining"] == 1
    assert current.json()["weekly_case_limit"] == 1
    assert "admin.access" not in current.json()["permissions"]
    logged_out = await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token})
    assert logged_out.status_code == 200
    assert not client.cookies.get("eillen_access")

    logged_in = await client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": token},
        json={"email": "ada@example.com", "password": "sourcework123"},
    )
    assert logged_in.status_code == 200
    original_refresh = client.cookies.get("eillen_refresh")
    refreshed = await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": token})
    assert refreshed.status_code == 200
    assert client.cookies.get("eillen_refresh") != original_refresh


async def test_login_rejects_bad_credentials_and_csrf(client: AsyncClient) -> None:
    no_csrf = await client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "bad"})
    assert no_csrf.status_code == 403
    token = await csrf(client)
    bad_login = await client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": token},
        json={"email": "nobody@example.com", "password": "bad"},
    )
    assert bad_login.status_code == 401
    assert bad_login.json()["error"]["code"] == "invalid_credentials"


async def test_registration_requires_every_consent(client: AsyncClient) -> None:
    token = await csrf(client)
    response = await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "no-consent@example.com",
            "username": "no_consent",
            "display_name": "No Consent",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": False,
        },
    )
    assert response.status_code == 422


async def test_registration_reports_duplicate_username_and_email(client: AsyncClient) -> None:
    token = await csrf(client)
    account = {
        "email": "first@example.com",
        "username": "duplicate",
        "display_name": "First Account",
        "password": "sourcework123",
        "confirm_age_18": True,
        "accept_terms": True,
        "accept_community_standards": True,
    }
    created = await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json=account,
    )
    assert created.status_code == 201

    duplicate_username = await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={**account, "email": "second@example.com"},
    )
    assert duplicate_username.status_code == 409
    assert duplicate_username.json()["error"] == {
        "code": "username_taken",
        "message": "That username is already taken",
        "details": None,
        "request_id": duplicate_username.json()["error"]["request_id"],
    }

    duplicate_email = await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={**account, "username": "different"},
    )
    assert duplicate_email.status_code == 409
    assert duplicate_email.json()["error"]["code"] == "email_registered"
    assert duplicate_email.json()["error"]["message"] == "An account with that email already exists"


async def test_email_verification_is_one_time_and_resend_is_private(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    messages: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "app.auth.service.queue_verification_email",
        lambda recipient, token: messages.append((recipient, token)),
    )
    token = await csrf(client)
    registered = await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "verify@example.com",
            "username": "verify_me",
            "display_name": "Verify Me",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    assert registered.status_code == 201
    assert messages[0][0] == "verify@example.com"

    confirmed = await client.post(
        "/api/v1/auth/email-verification/confirm",
        headers={"X-CSRF-Token": token},
        json={"token": messages[0][1]},
    )
    assert confirmed.status_code == 200
    async with SessionFactory() as db:
        user = await db.scalar(select(User).where(User.email == "verify@example.com"))
        account_token = await db.scalar(select(AccountActionToken))
    assert user is not None and user.is_verified
    assert account_token is not None and account_token.used_at is not None

    repeated = await client.post(
        "/api/v1/auth/email-verification/confirm",
        headers={"X-CSRF-Token": token},
        json={"token": messages[0][1]},
    )
    assert repeated.status_code == 200

    unknown = await client.post(
        "/api/v1/auth/email-verification/request",
        headers={"X-CSRF-Token": token},
        json={"email": "unknown@example.com"},
    )
    assert unknown.status_code == 200
    assert len(messages) == 1


async def test_password_reset_changes_password_revokes_sessions_and_cannot_be_reused(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    reset_messages: list[tuple[str, str]] = []
    monkeypatch.setattr("app.auth.service.queue_verification_email", lambda *_: None)
    monkeypatch.setattr(
        "app.auth.service.queue_password_reset_email",
        lambda recipient, token: reset_messages.append((recipient, token)),
    )
    token = await csrf(client)
    await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "reset@example.com",
            "username": "reset_me",
            "display_name": "Reset Me",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    requested = await client.post(
        "/api/v1/auth/password/forgot",
        headers={"X-CSRF-Token": token},
        json={"email": "reset@example.com"},
    )
    assert requested.status_code == 200
    assert reset_messages[0][0] == "reset@example.com"

    reset = await client.post(
        "/api/v1/auth/password/reset",
        headers={"X-CSRF-Token": token},
        json={"token": reset_messages[0][1], "password": "replacement123"},
    )
    assert reset.status_code == 200
    assert not client.cookies.get("eillen_refresh")

    reused = await client.post(
        "/api/v1/auth/password/reset",
        headers={"X-CSRF-Token": token},
        json={"token": reset_messages[0][1], "password": "anotherpass123"},
    )
    assert reused.status_code == 400
    assert reused.json()["error"]["code"] == "invalid_password_reset_token"

    old_login = await client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": token},
        json={"email": "reset@example.com", "password": "sourcework123"},
    )
    assert old_login.status_code == 401
    new_login = await client.post(
        "/api/v1/auth/login",
        headers={"X-CSRF-Token": token},
        json={"email": "reset@example.com", "password": "replacement123"},
    )
    assert new_login.status_code == 200
