import re
from datetime import date, time

MONTHS = {
    name.lower(): number
    for number, names in enumerate(
        (
            (),
            ("january", "jan"),
            ("february", "feb"),
            ("march", "mar"),
            ("april", "apr"),
            ("may",),
            ("june", "jun"),
            ("july", "jul"),
            ("august", "aug"),
            ("september", "sep", "sept"),
            ("october", "oct"),
            ("november", "nov"),
            ("december", "dec"),
        )
    )
    for name in names
}
MONTH_PATTERN = "|".join(sorted(MONTHS, key=len, reverse=True))


def parse_timeline_date(value: str) -> date | None:
    """Return the earliest useful calendar date in an AI-produced timeline label."""
    normalized = value.strip().lower()
    iso_match = re.search(r"\b((?:18|19|20)\d{2})-(\d{1,2})-(\d{1,2})\b", normalized)
    if iso_match:
        return _safe_date(*(int(part) for part in iso_match.groups()))

    full_match = re.search(
        rf"\b({MONTH_PATTERN})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:\s*[-–]\s*\d{{1,2}})?\s*,?\s*((?:18|19|20)\d{{2}})\b",
        normalized,
    )
    if full_match:
        month, day, year = full_match.groups()
        return _safe_date(int(year), MONTHS[month], int(day))

    month_match = re.search(
        rf"\b({MONTH_PATTERN})\.?\s+((?:18|19|20)\d{{2}})\b",
        normalized,
    )
    if month_match:
        month, year = month_match.groups()
        return date(int(year), MONTHS[month], 1)

    year_match = re.search(r"\b((?:18|19|20)\d{2})\b", normalized)
    return date(int(year_match.group(1)), 1, 1) if year_match else None


def parse_timeline_time(value: str) -> time | None:
    """Return a local clock time when an AI timeline label states one."""
    normalized = value.strip().lower()
    twelve_hour = re.search(
        r"\b(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*([ap])\.?m\.?\b",
        normalized,
    )
    if twelve_hour:
        hour_text, minute_text, meridiem = twelve_hour.groups()
        hour = int(hour_text) % 12
        if meridiem == "p":
            hour += 12
        return time(hour, int(minute_text or 0))

    twenty_four_hour = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", normalized)
    if twenty_four_hour:
        hour_text, minute_text = twenty_four_hour.groups()
        return time(int(hour_text), int(minute_text))
    return None


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None
