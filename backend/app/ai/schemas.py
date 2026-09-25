from datetime import date

from pydantic import BaseModel, Field, model_validator


class GeneratedTimelineEvent(BaseModel):
    date_label: str = Field(description="A cautious date label supported by the research sources")
    title: str
    description: str
    confidence: str = Field(pattern="^(low|medium|high)$")
    source_numbers: list[int] = Field(min_length=1, max_length=8)


class GeneratedEntity(BaseModel):
    name: str
    role: str
    category: str = Field(pattern="^(primary|family|friend|law_enforcement|witness|other)$")
    entity_type: str = Field(pattern="^(person|organization|location|other)$")
    summary: str
    relationship_to_primary: str | None = None
    is_primary: bool = False
    source_numbers: list[int] = Field(min_length=1, max_length=8)


class GeneratedRelationship(BaseModel):
    source_name: str
    target_name: str
    relationship_type: str
    label: str
    description: str
    confidence: float = Field(ge=0, le=1)
    source_numbers: list[int] = Field(min_length=1, max_length=8)


class GeneratedDiscussionPrompt(BaseModel):
    title: str = Field(min_length=3, max_length=140)
    body: str = Field(min_length=1, max_length=5000)
    thread_type: str = Field(pattern="^(question|theory|dispute)$")
    source_numbers: list[int] = Field(min_length=1, max_length=8)


class GeneratedEvidenceLink(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    description: str = Field(min_length=1, max_length=3000)
    evidence_type: str = Field(pattern="^(article|link)$")
    source_number: int = Field(ge=1)


class GeneratedLocation(BaseModel):
    name: str
    description: str
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_type: str = Field(
        pattern="^(primary|event|evidence|last_seen|sighting|search_area|law_enforcement|other)$"
    )
    occurred_on: date | None = None
    precision: str = Field(pattern="^(exact|approximate)$")
    confidence: float = Field(ge=0, le=1)
    source_numbers: list[int] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def reject_placeholder_coordinates(self) -> "GeneratedLocation":
        if self.latitude == 0 and self.longitude == 0:
            self.latitude = None
            self.longitude = None
        elif (self.latitude is None) != (self.longitude is None):
            self.latitude = None
            self.longitude = None
        return self


class GeneratedCaseDraft(BaseModel):
    title: str
    overview: str
    timeline: list[GeneratedTimelineEvent] = Field(min_length=1, max_length=12)
    entities: list[GeneratedEntity] = Field(default_factory=list, max_length=20)
    relationships: list[GeneratedRelationship] = Field(default_factory=list, max_length=30)
    locations: list[GeneratedLocation] = Field(default_factory=list, max_length=20)
    discussion_prompts: list[GeneratedDiscussionPrompt] = Field(default_factory=list, max_length=3)
    evidence_links: list[GeneratedEvidenceLink] = Field(default_factory=list, max_length=3)
    banner_prompt: str


class ResearchedSource(BaseModel):
    title: str
    url: str


class WebResearchResult(BaseModel):
    dossier: str
    sources: list[ResearchedSource] = Field(min_length=1)


class ThreadResearchResult(BaseModel):
    body: str = Field(min_length=1, max_length=4800)
    sources: list[ResearchedSource] = Field(min_length=1, max_length=12)
