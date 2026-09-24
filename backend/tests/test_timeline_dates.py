from datetime import date

from app.cases.timeline_dates import parse_timeline_date


def test_parse_timeline_dates_from_ai_labels() -> None:
    assert parse_timeline_date("June 12, 2021") == date(2021, 6, 12)
    assert parse_timeline_date("August 27–30, 2021") == date(2021, 8, 27)
    assert parse_timeline_date("Late September 1998") == date(1998, 9, 1)
    assert parse_timeline_date("Sometime in 1974") == date(1974, 1, 1)
    assert parse_timeline_date("Date unknown") is None
