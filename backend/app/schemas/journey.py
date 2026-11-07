"""Learning-journey board and timeline schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class JourneyCard(BaseModel):
    id: str
    code: str
    title: str
    subtitle: str = ""
    status: str
    href: str
    at: Optional[datetime | date] = None
    overdue: bool = False


class JourneyStage(BaseModel):
    key: str
    label: str
    description: str
    count: int = 0
    status: str = "not_started"
    items: list[JourneyCard] = Field(default_factory=list)


class JourneyTimelineItem(BaseModel):
    at: datetime | date
    kind: str
    title: str
    detail: str = ""
    href: Optional[str] = None
    state: str = "past"


class ProjectJourney(BaseModel):
    project_id: str
    project_name: str
    project_status: str
    generated_at: datetime
    stages: list[JourneyStage]
    timeline: list[JourneyTimelineItem]
    warnings: list[str] = Field(default_factory=list)
