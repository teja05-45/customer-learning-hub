"""Project membership administration."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ProjectRole
from app.schemas.common import Ref


class MembershipIn(BaseModel):
    user_id: str = Field(min_length=1, max_length=36)
    role: ProjectRole = ProjectRole.VIEWER


class MembershipUpdate(BaseModel):
    role: ProjectRole


class MembershipOut(BaseModel):
    id: str
    project_id: str
    user: Ref
    role: ProjectRole
    created_at: datetime
    email: str = ""
