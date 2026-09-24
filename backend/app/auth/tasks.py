import html

import httpx
import structlog

from app.config.settings import get_settings
from app.workers.celery_app import celery_app

log = structlog.get_logger()


@celery_app.task(  # type: ignore[untyped-decorator]
    name="auth.send_email",
    autoretry_for=(httpx.HTTPError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def send_email(recipient: str, subject: str, text_body: str, html_body: str) -> None:
    settings = get_settings()
    if not all((settings.mailgun_base_url, settings.mailgun_api_key, settings.mailgun_from_email)):
        log.warning("mailgun_not_configured", subject=subject)
        return
    response = httpx.post(
        f"{settings.mailgun_base_url.rstrip('/')}/messages",
        auth=("api", settings.mailgun_api_key),
        data={
            "from": settings.mailgun_from_email,
            "to": recipient,
            "subject": subject,
            "text": text_body,
            "html": html_body,
        },
        timeout=15.0,
    )
    response.raise_for_status()


def queue_verification_email(recipient: str, token: str) -> None:
    settings = get_settings()
    url = f"{settings.frontend_url.rstrip('/')}/verify-email?token={token}"
    escaped_url = html.escape(url, quote=True)
    send_email.delay(
        recipient,
        f"Verify your {settings.app_name} email",
        f"Verify your email by opening this link: {url}\n\n"
        f"This link expires in {settings.email_verification_expiry_hours} hours.",
        f'<p>Verify your email to finish setting up your {html.escape(settings.app_name)} account.</p>'
        f'<p><a href="{escaped_url}">Verify email</a></p>'
        f"<p>This link expires in {settings.email_verification_expiry_hours} hours.</p>",
    )


def queue_password_reset_email(recipient: str, token: str) -> None:
    settings = get_settings()
    url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"
    escaped_url = html.escape(url, quote=True)
    send_email.delay(
        recipient,
        f"Reset your {settings.app_name} password",
        f"Reset your password by opening this link: {url}\n\n"
        f"This link expires in {settings.password_reset_expiry_minutes} minutes.",
        f'<p>We received a request to reset your {html.escape(settings.app_name)} password.</p>'
        f'<p><a href="{escaped_url}">Reset password</a></p>'
        f"<p>This link expires in {settings.password_reset_expiry_minutes} minutes. "
        "If you did not request this, you can ignore this email.</p>",
    )
