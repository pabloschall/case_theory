import hashlib
import json
import re
from typing import Any

import httpx
from pydantic import ValidationError

from app.config.settings import Settings
from app.integrations.cache import JSONCache
from app.integrations.fbi.exceptions import FBIAPIError, FBIAPITimeout, FBICaseNotFound
from app.integrations.fbi.mapper import map_fbi_case_to_eillen_case
from app.integrations.fbi.schemas import FBICasePage, FBICaseRecord, FBIListResponse, NormalizedFBICase


class FBIClient:
    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.AsyncClient | None = None,
        cache: JSONCache | None = None,
    ) -> None:
        self.settings = settings
        self.http_client = http_client
        self.cache = cache
        self.base_url = settings.fbi_api_base_url.rstrip("/")

    async def list_cases(
        self,
        *,
        page: int = 1,
        title: str | None = None,
        field_offices: str | None = None,
        person_classification: str | None = None,
        status: str | None = None,
    ) -> FBICasePage:
        params: dict[str, str | int] = {"page": page}
        for key, value in (
            ("title", title),
            ("field_offices", field_offices),
            ("person_classification", person_classification),
            ("status", status),
        ):
            if value and value.strip():
                params[key] = value.strip()
        payload = await self._request_json(
            "/list", params=params, cache_ttl=self.settings.fbi_list_cache_seconds
        )
        try:
            raw = FBIListResponse.model_validate(payload)
        except ValidationError as exc:
            raise FBIAPIError("FBI returned an invalid case-list response") from exc
        items = [
            map_fbi_case_to_eillen_case(
                item.model_copy(update={"original_payload": source_payload})
            )
            for item, source_payload in zip(raw.items, payload.get("items", []), strict=True)
        ]
        page_size = max(len(items), 1)
        return FBICasePage(
            items=items,
            page=raw.page,
            total=raw.total,
            has_next=raw.page * page_size < raw.total,
        )

    async def search_cases(
        self,
        query: str,
        *,
        page: int = 1,
        field_offices: str | None = None,
        person_classification: str | None = None,
        status: str | None = None,
    ) -> FBICasePage:
        return await self.list_cases(
            page=page,
            title=query,
            field_offices=field_offices,
            person_classification=person_classification,
            status=status,
        )

    async def get_case(self, case_id: str) -> FBICaseRecord:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", case_id):
            raise FBICaseNotFound("FBI case was not found")
        payload = await self._request_json(
            "/list",
            params={"uid": case_id},
            cache_ttl=self.settings.fbi_case_cache_seconds,
        )
        try:
            response = FBIListResponse.model_validate(payload)
        except ValidationError as exc:
            raise FBIAPIError("FBI returned an invalid case response") from exc
        raw_items = payload.get("items", [])
        for item, original in zip(response.items, raw_items, strict=True):
            if item.uid == case_id:
                return item.model_copy(update={"original_payload": original})
        raise FBICaseNotFound("FBI case was not found")

    def normalize(self, source_case: FBICaseRecord) -> NormalizedFBICase:
        return map_fbi_case_to_eillen_case(source_case)

    async def _request_json(
        self,
        path: str,
        *,
        params: dict[str, str | int] | None = None,
        cache_ttl: int,
    ) -> dict[str, Any]:
        cache_key = self._cache_key(path, params)
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached
        headers = {
            "Accept": "application/json",
            "User-Agent": f"{self.settings.app_name} case-research integration/1.0",
        }
        if self.settings.fbi_api_key:
            headers["X-API-Key"] = self.settings.fbi_api_key
        owns_client = self.http_client is None
        client = self.http_client or httpx.AsyncClient(timeout=self.settings.fbi_api_timeout)
        try:
            response = await client.get(f"{self.base_url}{path}", params=params, headers=headers)
            if response.status_code == 404:
                raise FBICaseNotFound("FBI case was not found")
            if response.status_code == 429:
                raise FBIAPIError("FBI case discovery is temporarily rate limited")
            if response.status_code >= 500:
                raise FBIAPIError("FBI case discovery is temporarily unavailable")
            if response.status_code >= 400:
                raise FBIAPIError("FBI case discovery request was rejected")
            try:
                payload = response.json()
            except (json.JSONDecodeError, ValueError) as exc:
                raise FBIAPIError("FBI returned a malformed response") from exc
            if not isinstance(payload, dict):
                raise FBIAPIError("FBI returned a malformed response")
            if self.cache:
                await self.cache.set(cache_key, payload, cache_ttl)
            return payload
        except httpx.TimeoutException as exc:
            raise FBIAPITimeout("FBI case discovery timed out") from exc
        except httpx.RequestError as exc:
            raise FBIAPIError("FBI case discovery is temporarily unavailable") from exc
        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    def _cache_key(path: str, params: dict[str, str | int] | None) -> str:
        serialized = json.dumps(params or {}, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(f"{path}:{serialized}".encode()).hexdigest()
        return f"integration:fbi:{digest}"
