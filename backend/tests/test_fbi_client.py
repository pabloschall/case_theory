import json

import httpx
import pytest

from app.config.settings import Settings
from app.integrations.fbi.client import FBIClient
from app.integrations.fbi.exceptions import FBIAPIError, FBIAPITimeout, FBICaseNotFound


def fbi_record(uid: str = "case-123") -> dict[str, object]:
    return {
        "uid": uid,
        "title": "<strong>Jordan Example</strong>",
        "description": "<p>Seeking information about a public case.</p>",
        "details": "<p>Official details from the FBI.</p>",
        "status": "na",
        "person_classification": "Victim",
        "subjects": ["Kidnappings and Missing Persons"],
        "field_offices": ["phoenix"],
        "publication": "2025-01-02T10:00:00+00:00",
        "modified": "2025-02-03T10:00:00+00:00",
        "url": f"https://www.fbi.gov/wanted/example/{uid}",
        "images": [],
    }


def settings() -> Settings:
    return Settings(
        environment="test",
        fbi_api_base_url="https://api.fbi.test/wanted/v1",
        fbi_api_timeout=1,
    )


async def test_fbi_list_search_and_pagination_are_normalized() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/wanted/v1/list"
        assert request.url.params["page"] == "2"
        assert request.url.params["title"] == "Jordan"
        assert request.url.params["field_offices"] == "phoenix"
        return httpx.Response(
            200,
            json={"items": [fbi_record()], "page": 2, "total": 41},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        result = await FBIClient(settings(), http_client=http_client).search_cases(
            "Jordan", page=2, field_offices="phoenix"
        )

    assert result.page == 2
    assert result.total == 41
    assert result.has_next
    assert result.items[0].title == "Jordan Example"
    assert result.items[0].details == "Official details from the FBI."
    assert result.items[0].original_payload["uid"] == "case-123"


async def test_fbi_case_lookup_and_not_found() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        uid = request.url.params["uid"]
        items = [] if uid == "missing" else [fbi_record("case-456")]
        return httpx.Response(200, json={"items": items, "page": 1, "total": len(items)})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = FBIClient(settings(), http_client=http_client)
        case = await client.get_case("case-456")
        assert case.uid == "case-456"
        with pytest.raises(FBICaseNotFound):
            await client.get_case("missing")
        with pytest.raises(FBICaseNotFound):
            await client.get_case("../../unsafe")


@pytest.mark.parametrize("status", [429, 500, 503])
async def test_fbi_api_unavailable_or_rate_limited(status: int) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        with pytest.raises(FBIAPIError):
            await FBIClient(settings(), http_client=http_client).list_cases()


async def test_fbi_api_timeout() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        with pytest.raises(FBIAPITimeout):
            await FBIClient(settings(), http_client=http_client).list_cases()


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"not json"),
        httpx.Response(200, content=json.dumps({"items": "wrong"}).encode()),
        httpx.Response(200, json=[]),
    ],
)
async def test_fbi_api_malformed_response(response: httpx.Response) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return response

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        with pytest.raises(FBIAPIError):
            await FBIClient(settings(), http_client=http_client).list_cases()
