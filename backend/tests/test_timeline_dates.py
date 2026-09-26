from datetime import date, time

from app.cases.timeline_dates import parse_timeline_date, parse_timeline_time


def test_parse_timeline_dates_from_ai_labels() -> None:
    assert parse_timeline_date("June 12, 2021") == date(2021, 6, 12)
    assert parse_timeline_date("August 27–30, 2021") == date(2021, 8, 27)
    assert parse_timeline_date("Late September 1998") == date(1998, 9, 1)
    assert parse_timeline_date("Sometime in 1974") == date(1974, 1, 1)
    assert parse_timeline_date("Date unknown") is None


def test_parse_timeline_times_from_ai_labels() -> None:
    assert parse_timeline_time("June 12, 2021 at 5:32 p.m.") == time(17, 32)
    assert parse_timeline_time("September 11, 2001, 08:46") == time(8, 46)
    assert parse_timeline_time("Sometime in 1974") is None
