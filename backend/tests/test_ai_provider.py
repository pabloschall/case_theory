import base64
from typing import Any, cast

from app.ai.openai_provider import OpenAICaseGenerator, _extract_researched_sources
from app.config.settings import Settings
from app.storage.base import ObjectMetadata, StorageProvider


class BannerStorage(StorageProvider):
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    async def put(self, object_key: str, content: bytes, content_type: str) -> None:
        self.objects[object_key] = (content, content_type)

    async def create_upload_url(self, object_key: str, content_type: str) -> tuple[str, str]:
        raise NotImplementedError

    async def create_download_url(self, object_key: str) -> str:
        return f"https://storage.test/{object_key}"

    async def metadata(self, object_key: str) -> ObjectMetadata:
        content, content_type = self.objects[object_key]
        return ObjectMetadata(size=len(content), content_type=content_type)

    async def read(self, object_key: str) -> bytes:
        return self.objects[object_key][0]

    async def delete(self, object_key: str) -> None:
        self.objects.pop(object_key, None)


class FakeImages:
    async def generate(self, **_: object) -> object:
        encoded = base64.b64encode(b"RIFF-generated-WEBP").decode()
        return type("ImageResponse", (), {"data": [type("Image", (), {"b64_json": encoded})()]})()


async def test_generated_banner_is_written_to_object_storage() -> None:
    storage = BannerStorage()
    generator = OpenAICaseGenerator(Settings(openai_api_key="test-key"), storage)
    cast(Any, generator).client = type("Client", (), {"images": FakeImages()})()

    object_key = await generator.generate_banner("case-123", "Symbolic editorial landscape")

    assert object_key.startswith("cases/case-123/covers/")
    assert object_key.endswith(".webp")
    assert storage.objects[object_key] == (b"RIFF-generated-WEBP", "image/webp")


def test_extracts_and_deduplicates_web_research_sources() -> None:
    sources = _extract_researched_sources(
        {
            "output": [
                {
                    "type": "web_search_call",
                    "action": {
                        "sources": [
                            {"type": "url", "url": "https://example.gov/case?id=4#section"},
                        ]
                    },
                },
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "title": "Official case release",
                                    "url": "https://example.gov/case?id=4#details",
                                }
                            ],
                        }
                    ],
                },
            ]
        }
    )

    assert len(sources) == 1
    assert sources[0].title == "Official case release"
    assert sources[0].url == "https://example.gov/case?id=4"
