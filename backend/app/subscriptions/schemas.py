import uuid

from pydantic import BaseModel, ConfigDict


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str
    tier_level: int
    active_case_limit: int
    weekly_case_limit: int
    monthly_ai_run_limit: int
    storage_bytes_limit: int
    collaborator_limit: int
    daily_ai_case_limit: int
    lifetime_ai_case_limit: int
