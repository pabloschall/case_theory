import html
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

from app.integrations.fbi.exceptions import FBIAPIError
from app.integrations.fbi.schemas import FBICaseRecord, NormalizedFBICase


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def sanitize_fbi_text(value: str | None) -> str | None:
    if not value:
        return None
    parser = _TextExtractor()
    parser.feed(value)
    text = html.unescape(" ".join(parser.parts))
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned or None


def _official_url(value: object) -> str | None:
    if value is None:
        return None
    url = str(value)
    parsed = urlsplit(url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (hostname == "fbi.gov" or hostname.endswith(".fbi.gov")):
        return None
    return url


def _locations(value: object) -> list[str]:
    if isinstance(value, str):
        return [sanitize_fbi_text(value) or value]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if isinstance(item, str):
                result.append(sanitize_fbi_text(item) or item)
            elif isinstance(item, dict):
                candidate = item.get("name") or item.get("city") or item.get("location")
                if candidate:
                    result.append(str(candidate))
        return result
    if isinstance(value, dict):
        candidate = value.get("name") or value.get("city") or value.get("location")
        return [str(candidate)] if candidate else []
    return []


def map_fbi_case_to_eillen_case(record: FBICaseRecord) -> NormalizedFBICase:
    source_url = _official_url(record.url)
    if not source_url:
        raise FBIAPIError("FBI record did not include a valid official source URL")
    image_url = None
    for image in record.images or []:
        image_url = _official_url(image.large) or _official_url(image.original) or _official_url(image.thumb)
        if image_url:
            break
    return NormalizedFBICase(
        external_id=record.uid,
        title=sanitize_fbi_text(record.title) or "Untitled FBI case",
        description=sanitize_fbi_text(record.description),
        details=sanitize_fbi_text(record.details),
        remarks=sanitize_fbi_text(record.remarks),
        caution=sanitize_fbi_text(record.caution),
        warning_message=sanitize_fbi_text(record.warning_message),
        reward_text=sanitize_fbi_text(record.reward_text),
        status=record.status,
        classification=record.person_classification,
        subjects=[value for item in (record.subjects or []) if (value := sanitize_fbi_text(item))],
        aliases=[value for item in (record.aliases or []) if (value := sanitize_fbi_text(item))],
        dates_of_birth=list(record.dates_of_birth_used or []),
        place_of_birth=sanitize_fbi_text(record.place_of_birth),
        nationality=sanitize_fbi_text(record.nationality),
        sex=record.sex,
        race=record.race,
        hair=record.hair,
        eyes=record.eyes,
        field_offices=list(record.field_offices or []),
        locations=_locations(record.locations),
        publication=record.publication,
        modified=record.modified,
        source_url=source_url,
        image_url=image_url,
        original_payload=record.original_payload,
    )
