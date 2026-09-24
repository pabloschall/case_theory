from typing import Any

import pytest

from app.auth.tasks import send_email
from app.config.settings import Settings


def test_send_email_posts_to_mailgun(monkeypatch: pytest.MonkeyPatch) -> None:
    request: dict[str, Any] = {}

    class Response:
        def raise_for_status(self) -> None:
            request["status_checked"] = True

    def post(url: str, **kwargs: Any) -> Response:
        request.update(url=url, **kwargs)
        return Response()

    monkeypatch.setattr(
        "app.auth.tasks.get_settings",
        lambda: Settings(
            mailgun_base_url="https://api.mailgun.net/v3/mg.example.com/",
            mailgun_api_key="key-secret",
            mailgun_from_email="Game Theory <mail@mg.example.com>",
        ),
    )
    monkeypatch.setattr("app.auth.tasks.httpx.post", post)

    send_email.run("reader@example.com", "Subject", "Text", "<p>HTML</p>")

    assert request["url"] == "https://api.mailgun.net/v3/mg.example.com/messages"
    assert request["auth"] == ("api", "key-secret")
    assert request["data"] == {
        "from": "Game Theory <mail@mg.example.com>",
        "to": "reader@example.com",
        "subject": "Subject",
        "text": "Text",
        "html": "<p>HTML</p>",
    }
    assert request["status_checked"] is True
