import hashlib

from app.config.settings import get_settings

APP_NAME = get_settings().app_name

POLICY_VERSIONS = {
    "age_requirement": "2026-09-22",
    "terms_of_use": "2026-09-22",
    "community_standards": "2026-09-22",
}

POLICY_TEXT = {
    "age_requirement": "I confirm that I am at least 18 years old.",
    "terms_of_use": (
        f"I agree to use {APP_NAME} lawfully, upload only material I have the right to share, "
        "respect source provenance, and avoid presenting theories or AI synthesis as verified facts."
    ),
    "community_standards": (
        "I agree not to harass, threaten, stalk, dox, make reckless accusations, share private personal "
        "information, or upload illegal, exploitative, or otherwise prohibited material."
    ),
}


def policy_checksum(policy_type: str) -> str:
    return hashlib.sha256(POLICY_TEXT[policy_type].encode()).hexdigest()
