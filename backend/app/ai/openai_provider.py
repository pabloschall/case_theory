import base64
import uuid
from typing import Any, cast
from urllib.parse import urlsplit, urlunsplit

from openai import AsyncOpenAI

from app.ai.schemas import GeneratedCaseDraft, ResearchedSource, WebResearchResult
from app.cases.models import Case
from app.config.settings import Settings
from app.storage.base import StorageProvider


class OpenAICaseGenerator:
    def __init__(self, settings: Settings, storage: StorageProvider) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        self.settings = settings
        self.storage = storage
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    def _intake(self, case: Case) -> str:
        return (
            f"Names: {case.victim_names}\n"
            f"Year: {case.year if case.year is not None else 'Not provided'}\n"
            f"Location: {case.location or 'Not provided'}\n"
            f"Additional user context: {case.intake_notes or 'None provided'}"
        )

    async def research(self, case: Case) -> WebResearchResult:
        response = await self.client.responses.create(
            model=self.settings.ai_text_model,
            tools=[{"type": "web_search", "search_context_size": "high"}],
            tool_choice="required",
            include=["web_search_call.action.sources"],
            max_tool_calls=8,
            instructions=(
                "Research the identified public case on the web before answering. Resolve ambiguous names using "
                "the supplied year, location, and context when available. Prefer primary and authoritative sources "
                "such as government agencies, courts, and official records, then established reporting. Find several "
                "independent sources. Do not use private personal data, rumor sites, or unsourced accusations. "
                "Distinguish confirmed facts, attributed statements, allegations, and uncertainty. Return a concise "
                "research dossier covering identity, case overview, important dates, official findings, conflicts, "
                "and known unknowns. Cite every factual paragraph with web citations."
            ),
            input=self._intake(case),
        )
        sources = _extract_researched_sources(cast(Any, response).model_dump())
        if not response.output_text.strip():
            raise RuntimeError("OpenAI web research returned no dossier")
        if not sources:
            raise RuntimeError("OpenAI web research returned no inspectable sources")
        return WebResearchResult(dossier=response.output_text, sources=sources[:24])

    async def generate_draft(self, case: Case, research: WebResearchResult) -> GeneratedCaseDraft:
        source_catalog = "\n".join(
            f"[{index}] {source.title} — {source.url}" for index, source in enumerate(research.sources, start=1)
        )
        input_text = (
            f"CASE INTAKE\n{self._intake(case)}\n\n"
            f"WEB RESEARCH DOSSIER\n{research.dossier}\n\n"
            f"APPROVED SOURCE CATALOG\n{source_catalog}"
        )
        response = await self.client.responses.parse(
            model=self.settings.ai_text_model,
            instructions=(
                "Create a sourced case-workspace draft from the supplied web research dossier. Use only claims "
                "supported by the approved source catalog. The overview must be neutral, factual, and readable, "
                "and cite claims with source numbers such as [1] or [2][3]. Never invent a URL, source number, "
                "date, quotation, person, accusation, or conclusion. State conflicts and uncertainty plainly. "
                "Timeline items remain AI suggestions for review; each must include the supporting source_numbers. "
                "Extract only publicly documented people or organizations that materially help explain the case. "
                "Classify each entity conservatively and never label a person a suspect unless an authoritative "
                "source explicitly uses that legal status. Relationships must reference entity names exactly, "
                "include supporting source_numbers and confidence, and remain AI suggestions for human review. "
                "Extract important public case locations when a source supports the place. Coordinates are optional: "
                "include real coordinates only when they are supported and confidently known. Never use 0,0 or any "
                "other placeholder coordinates; return null for both latitude and longitude when they are unknown. "
                "Use approximate precision unless an exact public location is explicitly documented. Never include "
                "private home addresses or other sensitive personal locations. Every location must include supporting "
                "source_numbers. Give each location a specific, searchable public place name including region/state. "
                "Create two or three focused discussion prompts when the sources support useful questions. Prompts may "
                "examine documented competing theories, source contradictions, disputed public claims, or unresolved "
                "questions. Label them question, theory, or dispute. Never invent a conspiracy, accusation, suspect, "
                "or sensational claim. Phrase theories as questions for investigation rather than facts, and attach "
                "every prompt to the source_numbers that justify discussing it. "
                "Select two or three of the strongest approved public sources as initial link evidence. Prefer "
                "official records, government or police publications, and substantive established reporting. Give "
                "each a neutral title and a short description of what the linked source can document. Use article or "
                "link as the type, and reference exactly one valid source_number. Selection does not mean the source "
                "is verified as true. "
                "Use legal-status language precisely and never create an unsupported suspect label. The title should "
                "be a concise public case name. Create banner_prompt from the researched overview and known general "
                "location or atmosphere. It must request symbolic editorial illustration with no real-person likeness, "
                "photorealistic reconstruction, graphic imagery, simulated evidence, readable text, or logos."
            ),
            input=input_text,
            text_format=GeneratedCaseDraft,
        )
        if response.output_parsed is None:
            raise RuntimeError("OpenAI returned no structured case draft")
        return response.output_parsed

    async def generate_banner(self, case_id: str, prompt: str) -> str:
        response = await self.client.images.generate(
            model=self.settings.ai_image_model,
            prompt=prompt,
            size="1536x1024",
            quality="low",
            output_format="webp",
            n=1,
        )
        encoded = response.data[0].b64_json if response.data else None
        if not encoded:
            raise RuntimeError("OpenAI returned no banner image")
        object_key = f"cases/{case_id}/covers/{uuid.uuid4()}.webp"
        await self.storage.put(object_key, base64.b64decode(encoded), "image/webp")
        return object_key


def _canonical_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, parsed.query, ""))


def _extract_researched_sources(payload: dict[str, Any]) -> list[ResearchedSource]:
    found: dict[str, ResearchedSource] = {}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("type") == "url_citation" and isinstance(value.get("url"), str):
                url = _canonical_url(value["url"])
                raw_title = value.get("title")
                title = raw_title.strip() if isinstance(raw_title, str) else urlsplit(url).netloc
                found[url] = ResearchedSource(title=title or urlsplit(url).netloc, url=url)
            sources = value.get("sources")
            if isinstance(sources, list):
                for source in sources:
                    if isinstance(source, dict) and isinstance(source.get("url"), str):
                        url = _canonical_url(source["url"])
                        found.setdefault(url, ResearchedSource(title=urlsplit(url).netloc, url=url))
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return list(found.values())
