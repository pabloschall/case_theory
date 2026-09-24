from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class FBIImage(BaseModel):
    model_config = ConfigDict(extra="allow")

    thumb: HttpUrl | None = None
    large: HttpUrl | None = None
    original: HttpUrl | None = None
    caption: str | None = None


class FBIFile(BaseModel):
    model_config = ConfigDict(extra="allow")

    url: HttpUrl | None = None
    name: str | None = None


class FBICaseRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    uid: str
    title: str | None = None
    description: str | None = None
    details: str | None = None
    remarks: str | None = None
    warning_message: str | None = None
    caution: str | None = None
    reward_text: str | None = None
    reward_min: int | float | str | None = None
    reward_max: int | float | str | None = None
    status: str | None = None
    person_classification: str | None = None
    subjects: list[str] | None = None
    aliases: list[str] | None = None
    dates_of_birth_used: list[str] | None = None
    place_of_birth: str | None = None
    nationality: str | None = None
    sex: str | None = None
    race: str | None = None
    hair: str | None = None
    eyes: str | None = None
    height_min: int | float | str | None = None
    height_max: int | float | str | None = None
    weight: int | float | str | None = None
    field_offices: list[str] | None = None
    publication: datetime | None = None
    modified: datetime | None = None
    url: HttpUrl | None = None
    images: list[FBIImage] | None = None
    files: list[FBIFile] | None = None
    coordinates: list[Any] | dict[str, Any] | None = None
    locations: list[Any] | dict[str, Any] | str | None = None
    original_payload: dict[str, Any] = Field(default_factory=dict, exclude=True)


class FBIListResponse(BaseModel):
    items: list[FBICaseRecord]
    page: int = 1
    total: int = 0


class NormalizedFBICase(BaseModel):
    external_id: str
    title: str
    description: str | None
    details: str | None
    remarks: str | None
    caution: str | None
    warning_message: str | None
    reward_text: str | None
    status: str | None
    classification: str | None
    subjects: list[str]
    aliases: list[str]
    dates_of_birth: list[str]
    place_of_birth: str | None
    nationality: str | None
    sex: str | None
    race: str | None
    hair: str | None
    eyes: str | None
    field_offices: list[str]
    locations: list[str]
    publication: datetime | None
    modified: datetime | None
    source_url: str
    image_url: str | None
    already_imported: bool = False
    imported_case_id: str | None = None
    original_payload: dict[str, Any] = Field(exclude=True)


class FBICasePage(BaseModel):
    items: list[NormalizedFBICase]
    page: int
    total: int
    has_next: bool


class FBIImportResult(BaseModel):
    already_imported: bool
    case_id: str
    message: str
