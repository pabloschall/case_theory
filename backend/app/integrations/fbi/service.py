import re
import uuid
from urllib.parse import urlsplit

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cases.models import Case, CaseSource, CaseSummary, Source, SourceCitation
from app.common.errors import AppError
from app.evidence.models import Evidence
from app.integrations.fbi.client import FBIClient
from app.integrations.fbi.exceptions import FBIImageError
from app.integrations.fbi.schemas import FBIImportResult, NormalizedFBICase
from app.people.models import Person
from app.storage.base import StorageProvider
from app.subscriptions.permissions import PermissionService
from app.users.models import User

logger = structlog.get_logger()
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ("jpg", (b"\xff\xd8\xff",)),
    "image/png": ("png", (b"\x89PNG\r\n\x1a\n",)),
    "image/webp": ("webp", (b"RIFF",)),
}


def _slug(value: str, suffix: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:140] or "case"
    return f"{normalized}-{suffix}"


class FBICaseImportService:
    def __init__(
        self,
        db: AsyncSession,
        client: FBIClient,
        storage: StorageProvider,
        *,
        image_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.db = db
        self.client = client
        self.storage = storage
        self.image_client = image_client

    async def import_case(self, external_id: str, user: User) -> FBIImportResult:
        if not await PermissionService(self.db).allows(
            user.id, "case.import", is_admin=user.is_admin
        ):
            raise AppError(403, "case_import_forbidden", "Your account cannot import public cases")
        existing = await self.db.scalar(
            select(CaseSource).where(
                CaseSource.source_type == "fbi", CaseSource.external_id == external_id
            )
        )
        if existing:
            return FBIImportResult(
                already_imported=True,
                case_id=str(existing.case_id),
                message="This FBI case has already been imported.",
            )

        await PermissionService(self.db).require_case_creation(user)

        record = await self.client.get_case(external_id)
        normalized = self.client.normalize(record)
        case_id = uuid.uuid4()
        source_layer_id = uuid.uuid4()
        official_source_id = uuid.uuid4()
        summary_id = uuid.uuid4()
        location = ", ".join(normalized.locations[:2] or normalized.field_offices[:2]) or None
        case = Case(
            id=case_id,
            slug=_slug(normalized.title, str(case_id)[:8]),
            title=normalized.title,
            victim_names=normalized.title,
            year=None,
            location=location,
            intake_notes="Imported from an official FBI public record for review.",
            status="draft",
            privacy="private",
            ai_research_status="source_imported",
            counts_toward_weekly_limit=True,
            created_by_user_id=user.id,
        )
        source_layer = CaseSource(
            id=source_layer_id,
            case_id=case_id,
            source_type="fbi",
            external_id=normalized.external_id,
            source_url=normalized.source_url,
            source_name="Federal Bureau of Investigation",
            source_payload=normalized.original_payload,
            source_published_at=normalized.publication,
            source_updated_at=normalized.modified,
        )
        official_source = Source(
            id=official_source_id,
            case_id=case_id,
            url=normalized.source_url,
            canonical_url=normalized.source_url,
            title=f"FBI: {normalized.title}",
            position=1,
            publisher="Federal Bureau of Investigation",
            source_type="official",
            reliability_metadata={
                "classification_basis": "Official source provenance; no truth score assigned",
                "external_source_id": normalized.external_id,
            },
        )
        summary_text, summary_field = self._summary(normalized)
        summary = CaseSummary(
            id=summary_id,
            case_id=case_id,
            version=1,
            body=summary_text,
            source="official_source",
            is_current=True,
        )
        self.db.add_all([case, source_layer, official_source, summary])
        self.db.add(
            SourceCitation(
                case_source_id=source_layer_id,
                resource_type="summary",
                resource_id=summary_id,
                source_field=summary_field,
                source_text=summary_text,
                interpretation_type="official",
            )
        )
        await self._create_primary_person(case, source_layer, normalized, user)

        stored_key: str | None = None
        if normalized.image_url:
            try:
                content, content_type, extension = await self._download_image(normalized.image_url)
                stored_key = (
                    f"cases/{case_id}/sources/fbi/{normalized.external_id}/cover.{extension}"
                )
                await self.storage.put(stored_key, content, content_type)
                case.cover_image_object_key = stored_key
                case.cover_image_url = f"/api/v1/cases/{case_id}/cover"
                evidence_id = uuid.uuid4()
                self.db.add(
                    Evidence(
                        id=evidence_id,
                        case_id=case_id,
                        uploaded_by_user_id=user.id,
                        title=f"Official FBI image — {normalized.title}",
                        description="Image published with the official FBI case record.",
                        evidence_type="image",
                        storage_object_key=stored_key,
                        original_filename=f"fbi-{normalized.external_id}.{extension}",
                        mime_type=content_type,
                        file_size=len(content),
                        source_url=normalized.image_url,
                        source_id=official_source_id,
                        verification_status="source_backed",
                        processing_status="available",
                        review_status="published",
                    )
                )
                self.db.add(
                    SourceCitation(
                        case_source_id=source_layer_id,
                        resource_type="evidence",
                        resource_id=evidence_id,
                        source_field="images",
                        source_text=normalized.image_url,
                        interpretation_type="official",
                    )
                )
            except FBIImageError as exc:
                logger.warning(
                    "fbi_image_skipped",
                    external_source_id=normalized.external_id,
                    reason=str(exc),
                )
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            if stored_key:
                try:
                    await self.storage.delete(stored_key)
                except Exception:
                    logger.warning("fbi_orphan_image_cleanup_failed", object_key=stored_key)
            existing = await self.db.scalar(
                select(CaseSource).where(
                    CaseSource.source_type == "fbi",
                    CaseSource.external_id == external_id,
                )
            )
            if existing:
                return FBIImportResult(
                    already_imported=True,
                    case_id=str(existing.case_id),
                    message="This FBI case has already been imported.",
                )
            raise
        logger.info(
            "fbi_case_imported",
            case_id=str(case_id),
            user_id=str(user.id),
            external_source_id=normalized.external_id,
        )
        return FBIImportResult(
            already_imported=False,
            case_id=str(case_id),
            message="FBI case imported as a private draft.",
        )

    async def _create_primary_person(
        self,
        case: Case,
        source_layer: CaseSource,
        normalized: NormalizedFBICase,
        user: User,
    ) -> None:
        person_id = uuid.uuid4()
        role = normalized.classification or (normalized.subjects[0] if normalized.subjects else "Subject")
        summary_parts = [
            value
            for value in (
                normalized.description,
                f"Aliases: {', '.join(normalized.aliases)}" if normalized.aliases else None,
                f"Place of birth: {normalized.place_of_birth}" if normalized.place_of_birth else None,
            )
            if value
        ]
        self.db.add(
            Person(
                id=person_id,
                case_id=case.id,
                name=normalized.title,
                slug=_slug(normalized.title, str(person_id)[:8]),
                role=role[:120],
                category="primary",
                entity_type="person",
                summary=" ".join(summary_parts) or None,
                is_primary=True,
                ai_suggested=False,
                review_status="confirmed",
                created_by_user_id=user.id,
            )
        )
        self.db.add(
            SourceCitation(
                case_source_id=source_layer.id,
                resource_type="person",
                resource_id=person_id,
                source_field="title",
                source_text=normalized.title,
                interpretation_type="official",
            )
        )

    @staticmethod
    def _summary(case: NormalizedFBICase) -> tuple[str, str]:
        for field in ("details", "description", "remarks", "caution"):
            value = getattr(case, field)
            if value:
                return value, field
        return "The FBI record contains limited public narrative information.", "title"

    async def _download_image(self, url: str) -> tuple[bytes, str, str]:
        parsed = urlsplit(url)
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not (hostname == "fbi.gov" or hostname.endswith(".fbi.gov")):
            raise FBIImageError("Image URL is not an official FBI HTTPS URL")
        owns_client = self.image_client is None
        client = self.image_client or httpx.AsyncClient(
            timeout=self.client.settings.fbi_api_timeout, follow_redirects=True
        )
        try:
            async with client.stream("GET", url, headers={"Accept": "image/*"}) as response:
                if response.status_code != 200:
                    raise FBIImageError("Official image could not be retrieved")
                final_hostname = (response.url.host or "").lower()
                if not (
                    final_hostname == "fbi.gov" or final_hostname.endswith(".fbi.gov")
                ):
                    raise FBIImageError("Official image redirected outside FBI infrastructure")
                raw_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if raw_type not in ALLOWED_IMAGE_TYPES:
                    raise FBIImageError("Official image has an unsupported content type")
                declared_size = int(response.headers.get("content-length", "0") or 0)
                if declared_size > self.client.settings.fbi_image_max_bytes:
                    raise FBIImageError("Official image exceeds the import size limit")
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > self.client.settings.fbi_image_max_bytes:
                        raise FBIImageError("Official image exceeds the import size limit")
                    chunks.append(chunk)
            content = b"".join(chunks)
            extension, signatures = ALLOWED_IMAGE_TYPES[raw_type]
            if raw_type == "image/webp":
                valid = content.startswith(signatures[0]) and content[8:12] == b"WEBP"
            else:
                valid = any(content.startswith(signature) for signature in signatures)
            if not valid:
                raise FBIImageError("Official image content did not match its declared type")
            return content, raw_type, extension
        except httpx.HTTPError as exc:
            raise FBIImageError("Official image could not be retrieved") from exc
        finally:
            if owns_client:
                await client.aclose()
