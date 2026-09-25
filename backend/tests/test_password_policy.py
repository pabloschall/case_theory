import pytest
from pydantic import ValidationError

from app.admin.schemas import AdminUserCreate
from app.auth.schemas import PasswordResetRequest, RegisterRequest


def test_eight_character_password_is_accepted_everywhere() -> None:
    password = "case1234"

    registration = RegisterRequest(
        email="reader@example.com",
        username="reader",
        display_name="Reader",
        password=password,
        confirm_age_18=True,
        accept_terms=True,
        accept_community_standards=True,
    )
    reset = PasswordResetRequest(token="a" * 32, password=password)
    admin = AdminUserCreate(
        email="admin@example.com",
        username="case_admin",
        display_name="Case Admin",
        password=password,
    )

    assert registration.password == reset.password == admin.password == password


@pytest.mark.parametrize(
    ("model", "values"),
    [
        (
            RegisterRequest,
            {
                "email": "reader@example.com",
                "username": "reader",
                "display_name": "Reader",
                "confirm_age_18": True,
                "accept_terms": True,
                "accept_community_standards": True,
            },
        ),
        (PasswordResetRequest, {"token": "a" * 32}),
        (
            AdminUserCreate,
            {
                "email": "admin@example.com",
                "username": "case_admin",
                "display_name": "Case Admin",
            },
        ),
    ],
)
def test_seven_character_password_is_rejected(
    model: type[RegisterRequest] | type[PasswordResetRequest] | type[AdminUserCreate],
    values: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        model(**values, password="case123")
