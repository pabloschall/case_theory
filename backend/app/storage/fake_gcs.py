from urllib.parse import quote, urlencode

import httpx

from app.common.errors import AppError
from app.config.settings import Settings
from app.storage.base import ObjectMetadata, StorageProvider


class FakeGCSStorageProvider(StorageProvider):
    """Adapter for fake-gcs-server used only in local development and tests."""

    def __init__(self, settings: Settings) -> None:
        self.bucket = settings.gcs_bucket
        self.internal_url = settings.gcs_emulator_internal_url.rstrip("/")
        self.public_url = settings.gcs_emulator_public_url.rstrip("/")

    async def put(self, object_key: str, content: bytes, content_type: str) -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.internal_url}/upload/storage/v1/b/{quote(self.bucket)}/o",
                params={"uploadType": "media", "name": object_key},
                headers={"Content-Type": content_type},
                content=content,
            )
        response.raise_for_status()

    async def create_upload_url(self, object_key: str, content_type: str) -> tuple[str, str]:
        query = urlencode({"uploadType": "media", "name": object_key})
        return f"{self.public_url}/upload/storage/v1/b/{quote(self.bucket)}/o?{query}", "POST"

    async def create_download_url(self, object_key: str) -> str:
        encoded = quote(object_key, safe="")
        return f"{self.public_url}/download/storage/v1/b/{quote(self.bucket)}/o/{encoded}?alt=media"

    async def metadata(self, object_key: str) -> ObjectMetadata:
        encoded = quote(object_key, safe="")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{self.internal_url}/storage/v1/b/{quote(self.bucket)}/o/{encoded}"
            )
        if response.status_code == 404:
            raise AppError(409, "upload_missing", "The uploaded file was not found")
        response.raise_for_status()
        data = response.json()
        return ObjectMetadata(size=int(data["size"]), content_type=data.get("contentType"))

    async def read(self, object_key: str) -> bytes:
        encoded = quote(object_key, safe="")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.internal_url}/download/storage/v1/b/{quote(self.bucket)}/o/{encoded}",
                params={"alt": "media"},
            )
        response.raise_for_status()
        return response.content

    async def delete(self, object_key: str) -> None:
        encoded = quote(object_key, safe="")
        async with httpx.AsyncClient(timeout=10) as client:
            await client.delete(f"{self.internal_url}/storage/v1/b/{quote(self.bucket)}/o/{encoded}")
