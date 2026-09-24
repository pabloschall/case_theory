import asyncio
from datetime import timedelta
from typing import Any

from app.config.settings import Settings
from app.storage.base import ObjectMetadata, StorageProvider


class GoogleCloudStorageProvider(StorageProvider):
    def __init__(self, settings: Settings) -> None:
        import google.auth  # type: ignore[import-not-found]
        from google.cloud import storage  # type: ignore[import-not-found]

        self.credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        self.signing_service_account = settings.gcs_signing_service_account
        self.client = storage.Client(
            project=settings.gcs_project_id,
            credentials=self.credentials,
        )
        self.bucket = self.client.bucket(settings.gcs_bucket)

    def _signing_kwargs(self) -> dict[str, Any]:
        from google.auth.transport.requests import Request  # type: ignore[import-not-found]

        if not self.signing_service_account:
            raise RuntimeError("GCS_SIGNING_SERVICE_ACCOUNT is required to sign storage URLs")
        if not self.credentials.valid or not self.credentials.token:
            self.credentials.refresh(Request())
        return {
            "service_account_email": self.signing_service_account,
            "access_token": self.credentials.token,
        }

    async def put(self, object_key: str, content: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self.bucket.blob(object_key).upload_from_string,
            content,
            content_type=content_type,
        )

    async def create_upload_url(self, object_key: str, content_type: str) -> tuple[str, str]:
        blob = self.bucket.blob(object_key)
        signing_kwargs = await asyncio.to_thread(self._signing_kwargs)
        url = await asyncio.to_thread(
            blob.generate_signed_url,
            version="v4",
            expiration=timedelta(minutes=15),
            method="PUT",
            content_type=content_type,
            **signing_kwargs,
        )
        return url, "PUT"

    async def create_download_url(self, object_key: str) -> str:
        blob = self.bucket.blob(object_key)
        signing_kwargs = await asyncio.to_thread(self._signing_kwargs)
        return await asyncio.to_thread(
            blob.generate_signed_url,
            version="v4",
            expiration=timedelta(minutes=15),
            method="GET",
            **signing_kwargs,
        )

    async def metadata(self, object_key: str) -> ObjectMetadata:
        blob = self.bucket.blob(object_key)
        await asyncio.to_thread(blob.reload)
        return ObjectMetadata(size=int(blob.size or 0), content_type=blob.content_type)

    async def read(self, object_key: str) -> bytes:
        return await asyncio.to_thread(self.bucket.blob(object_key).download_as_bytes)

    async def delete(self, object_key: str) -> None:
        await asyncio.to_thread(self.bucket.blob(object_key).delete)
