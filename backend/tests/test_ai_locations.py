from app.ai.schemas import GeneratedLocation


def _location(**coordinates: float | None) -> GeneratedLocation:
    return GeneratedLocation(
        name="North trailhead, Oregon",
        description="Public trailhead named in the supporting source.",
        location_type="last_seen",
        precision="approximate",
        confidence=0.8,
        source_numbers=[1],
        **coordinates,
    )


def test_ai_location_rejects_zero_coordinate_placeholder() -> None:
    location = _location(latitude=0, longitude=0)

    assert location.latitude is None
    assert location.longitude is None


def test_ai_location_preserves_real_coordinates() -> None:
    location = _location(latitude=43.7904, longitude=-110.6818)

    assert location.latitude == 43.7904
    assert location.longitude == -110.6818


def test_ai_location_drops_incomplete_coordinate_pair() -> None:
    location = _location(latitude=43.7904, longitude=None)

    assert location.latitude is None
    assert location.longitude is None
