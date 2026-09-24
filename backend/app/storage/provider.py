from functools import lru_cache

from app.config.settings import get_settings
from app.storage.base import StorageProvider
from app.storage.fake_gcs import FakeGCSStorageProvider
from app.storage.gcs import GoogleCloudStorageProvider


@lru_cache
def _provider(name: str) -> StorageProvider:
    settings = get_settings()
    if name == "gcs":
        return GoogleCloudStorageProvider(settings)
    return FakeGCSStorageProvider(settings)


def get_storage_provider() -> StorageProvider:
    settings = get_settings()
    return _provider(settings.storage_provider)
