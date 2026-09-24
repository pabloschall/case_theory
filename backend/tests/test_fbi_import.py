import uuid
from collections.abc import Callable

import httpx
from httpx import AsyncClient
from sqlalchemy import select

from app.auth.security import hash_password
from app.cases.models import Case, CaseSource, SourceCitation
from app.config.settings import Settings
from app.db.session import SessionFactory
from app.evidence.models import Evidence
from app.integrations.fbi.client import FBIClient
from app.integrations.fbi.enrichment import (
    FBIEnrichedEvent,
    FBIEnrichedEvidence,
    FBIEnrichedPerson,
    FBIEnrichedSummary,
    FBIEnrichmentDraft,
    FBIEnrichmentService,
)
from app.integrations.fbi.routes import get_fbi_client
from app.integrations.fbi.service import FBICaseImportService
from app.main import app
from app.people.models import Person
from app.storage.base import ObjectMetadata, StorageProvider
from app.storage.provider import get_storage_provider
from app.subscriptions.models import SubscriptionPlan, UserSubscription
from app.users.models import User, UserProfile


def fbi_record(uid: str = "fbi-123", *, image_url: str | None = None) -> dict[str, object]:
    return {
        "uid": uid,
        "title": "Taylor Example",
        "description": "<p>The FBI is seeking information in this public case.</p>",
        "details": "<p>Taylor was last seen in a publicly identified area.</p>",
        "remarks": "Information remains under review.",
        "status": "na",
        "person_classification": "Victim",
        "subjects": ["Kidnappings and Missing Persons"],
        "aliases": ["T. Example"],
        "field_offices": ["phoenix"],
        "publication": "2025-01-02T10:00:00+00:00",
        "modified": "2025-02-03T10:00:00+00:00",
        "url": f"https://www.fbi.gov/wanted/example/{uid}",
        "images": [{"large": image_url}] if image_url else [],
        "unmodeled_official_field": "preserved",
    }


def fbi_settings() -> Settings:
    return Settings(
        environment="test",
        fbi_api_base_url="https://api.fbi.test/wanted/v1",
        fbi_api_timeout=1,
        fbi_image_max_bytes=1024,
    )


class MemoryStorage(StorageProvider):
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    async def put(self, object_key: str, content: bytes, content_type: str) -> None:
        self.objects[object_key] = (content, content_type)

    async def create_upload_url(self, object_key: str, content_type: str) -> tuple[str, str]:
        return f"https://storage.test/{object_key}", "PUT"

    async def create_download_url(self, object_key: str) -> str:
        return f"https://storage.test/{object_key}"

    async def metadata(self, object_key: str) -> ObjectMetadata:
        content, content_type = self.objects[object_key]
        return ObjectMetadata(size=len(content), content_type=content_type)

    async def read(self, object_key: str) -> bytes:
        return self.objects[object_key][0]

    async def delete(self, object_key: str) -> None:
        self.objects.pop(object_key, None)


def make_fbi_client(record_factory: Callable[[str], dict[str, object]]) -> tuple[FBIClient, httpx.AsyncClient]:
    async def handler(request: httpx.Request) -> httpx.Response:
        uid = request.url.params.get("uid")
        if uid:
            return httpx.Response(
                200,
                json={"items": [record_factory(uid)], "page": 1, "total": 1},
            )
        if request.url.path.endswith("list"):
            return httpx.Response(200, json={"items": [record_factory("fbi-123")], "page": 1, "total": 1})
        return httpx.Response(404)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return FBIClient(fbi_settings(), http_client=http_client), http_client


async def register(client: AsyncClient) -> tuple[str, User]:
    token = (await client.get("/api/v1/auth/csrf")).json()["csrf_token"]
    await client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": token},
        json={
            "email": "fbi-importer@example.com",
            "username": "fbi_importer",
            "display_name": "FBI Importer",
            "password": "sourcework123",
            "confirm_age_18": True,
            "accept_terms": True,
            "accept_community_standards": True,
        },
    )
    async with SessionFactory() as db:
        user = await db.scalar(select(User).where(User.email == "fbi-importer@example.com"))
        assert user is not None
        return token, user


async def test_fbi_discovery_import_duplicate_authorization_and_provenance(
    client: AsyncClient,
) -> None:
    fbi_client, http_client = make_fbi_client(lambda uid: fbi_record(uid))
    storage = MemoryStorage()
    app.dependency_overrides[get_fbi_client] = lambda: fbi_client
    app.dependency_overrides[get_storage_provider] = lambda: storage
    try:
        token, user = await register(client)
        async with SessionFactory() as db:
            registered_user = await db.get(User, user.id)
            assert registered_user is not None
            registered_user.is_verified = True
            await db.commit()
        discovered = await client.get("/api/v1/integrations/fbi/cases?q=Taylor&page=1")
        assert discovered.status_code == 200
        assert discovered.json()["items"][0]["title"] == "Taylor Example"
        assert discovered.json()["items"][0]["already_imported"] is False

        imported = await client.post(
            "/api/v1/integrations/fbi/cases/fbi-123/import",
            headers={"X-CSRF-Token": token},
        )
        assert imported.status_code == 201
        result = imported.json()
        assert result["already_imported"] is False

        duplicate = await client.post(
            "/api/v1/integrations/fbi/cases/fbi-123/import",
            headers={"X-CSRF-Token": token},
        )
        assert duplicate.status_code == 201
        assert duplicate.json() == {
            "already_imported": True,
            "case_id": result["case_id"],
            "message": "This FBI case has already been imported.",
        }

        async with SessionFactory() as db:
            imported_case = await db.get(Case, uuid.UUID(result["case_id"]))
            assert imported_case is not None
            assert imported_case.status == "draft"
            assert imported_case.privacy == "private"
            source = await db.scalar(select(CaseSource).where(CaseSource.case_id == imported_case.id))
            assert source is not None
            assert source.source_payload["unmodeled_official_field"] == "preserved"
            assert await db.scalar(select(Person).where(Person.case_id == imported_case.id))
            citations = (
                await db.scalars(
                    select(SourceCitation).where(SourceCitation.case_source_id == source.id)
                )
            ).all()
            assert {citation.resource_type for citation in citations} == {"summary", "person"}

        opened = await client.get(f"/api/v1/cases/{result['case_id']}")
        assert opened.status_code == 200
        assert opened.json()["external_sources"][0]["source_type"] == "fbi"
    finally:
        app.dependency_overrides.clear()
        await http_client.aclose()


async def make_lead_user() -> User:
    async with SessionFactory() as db:
        lead = await db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == "lead"))
        assert lead
        user = User(
            email="direct-import@example.com",
            username="direct_import",
            password_hash=hash_password("sourcework123"),
            is_verified=True,
            profile=UserProfile(display_name="Direct Importer"),
        )
        db.add(user)
        await db.flush()
        db.add(UserSubscription(user_id=user.id, plan_id=lead.id))
        await db.commit()
        return user


async def test_fbi_image_import_validates_content_and_uses_private_storage() -> None:
    user = await make_lead_user()
    image_url = "https://www.fbi.gov/images/example.png"
    fbi_client, fbi_http = make_fbi_client(lambda uid: fbi_record(uid, image_url=image_url))

    async def image_handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "image/png"}, content=b"\x89PNG\r\n\x1a\nimage")

    image_http = httpx.AsyncClient(transport=httpx.MockTransport(image_handler))
    storage = MemoryStorage()
    try:
        async with SessionFactory() as db:
            result = await FBICaseImportService(
                db, fbi_client, storage, image_client=image_http
            ).import_case("image-valid", user)
            case = await db.get(Case, uuid.UUID(result.case_id))
            assert case and case.cover_image_object_key in storage.objects
            evidence = await db.scalar(select(Evidence).where(Evidence.case_id == case.id))
            assert evidence and evidence.mime_type == "image/png"
    finally:
        await fbi_http.aclose()
        await image_http.aclose()


async def test_fbi_invalid_image_is_not_stored() -> None:
    user = await make_lead_user()
    image_url = "https://www.fbi.gov/images/not-an-image.png"
    fbi_client, fbi_http = make_fbi_client(lambda uid: fbi_record(uid, image_url=image_url))

    async def image_handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "image/png"}, content=b"not a png")

    image_http = httpx.AsyncClient(transport=httpx.MockTransport(image_handler))
    storage = MemoryStorage()
    try:
        async with SessionFactory() as db:
            result = await FBICaseImportService(
                db, fbi_client, storage, image_client=image_http
            ).import_case("image-invalid", user)
            case = await db.get(Case, uuid.UUID(result.case_id))
            assert case and case.cover_image_object_key is None
            assert storage.objects == {}
    finally:
        await fbi_http.aclose()
        await image_http.aclose()


async def test_fbi_ai_enrichment_stays_suggested_and_retains_provenance() -> None:
    user = await make_lead_user()
    fbi_client, fbi_http = make_fbi_client(lambda uid: fbi_record(uid))
    try:
        async with SessionFactory() as db:
            imported = await FBICaseImportService(db, fbi_client, MemoryStorage()).import_case(
                "enrichment-source", user
            )
            case_id = uuid.UUID(imported.case_id)
            source = await db.scalar(select(CaseSource).where(CaseSource.case_id == case_id))
            assert source
            draft = FBIEnrichmentDraft(
                summary=FBIEnrichedSummary(
                    body="The official FBI record asks the public for information about this case.",
                    source_fields=["details"],
                ),
                timeline=[
                    FBIEnrichedEvent(
                        date_label="Approximately 2024",
                        date_precision="approximate",
                        title="Reported last sighting",
                        description="The official record describes a reported last sighting.",
                        confidence="high",
                        source_field="details",
                        source_text="was last seen in a publicly identified area",
                    )
                ],
                people=[
                    FBIEnrichedPerson(
                        name="Named Witness",
                        role="Witness",
                        summary="Named as a witness in the official record.",
                        source_field="details",
                        source_text="Named Witness reported the sighting",
                    )
                ],
                evidence=[
                    FBIEnrichedEvidence(
                        title="Described personal item",
                        description="An item described in the FBI source.",
                        evidence_type="personal_item",
                        source_field="remarks",
                        source_text="carried a distinctive personal item",
                    )
                ],
            )
            await FBIEnrichmentService(db).apply(
                case_id, source, draft, model_name="mock-source-enricher"
            )

            case = await db.get(Case, case_id)
            assert case and case.status == "draft"
            suggested_people = (
                await db.scalars(
                    select(Person).where(Person.case_id == case_id, Person.ai_suggested.is_(True))
                )
            ).all()
            assert suggested_people[0].review_status == "suggested"
            suggested_evidence = await db.scalar(
                select(Evidence).where(Evidence.case_id == case_id, Evidence.ai_generated.is_(True))
            )
            assert suggested_evidence and suggested_evidence.review_status == "suggested"
            citations = (
                await db.scalars(
                    select(SourceCitation).where(
                        SourceCitation.case_source_id == source.id,
                        SourceCitation.interpretation_type == "ai_extracted",
                    )
                )
            ).all()
            assert {item.resource_type for item in citations} == {
                "summary",
                "timeline_event",
                "person",
                "evidence",
            }
    finally:
        await fbi_http.aclose()
