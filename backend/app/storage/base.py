from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ObjectMetadata:
    size: int
    content_type: str | None


class StorageProvider(ABC):
    @abstractmethod
    async def put(self, object_key: str, content: bytes, content_type: str) -> None:
        """Store server-generated content under a private object key."""

    @abstractmethod
    async def create_upload_url(self, object_key: str, content_type: str) -> tuple[str, str]:
        """Return an upload URL and HTTP method."""

    @abstractmethod
    async def create_download_url(self, object_key: str) -> str:
        """Return a short-lived browser download URL."""

    @abstractmethod
    async def metadata(self, object_key: str) -> ObjectMetadata:
        """Return trusted object metadata from storage."""

    @abstractmethod
    async def read(self, object_key: str) -> bytes:
        """Read an object for validation and hashing."""

    @abstractmethod
    async def delete(self, object_key: str) -> None:
        """Delete an object that failed validation or was abandoned."""
