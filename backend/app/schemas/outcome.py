"""Outcome measurement schemas.

The status is derived from the recorded values by the service layer, but it is
also part of the contract so a client can display it without recalculating the
business rule.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.enums import OutcomeDirection, OutcomeStatus
from app.schemas.common import ORMModel, Ref


class OutcomeCreate(BaseModel):
    name: str = Field(min_length=5, max_length=240)
    decision_id: str
    action_id: Optional[str] = None
    metric_definition: str = Field(min_length=5, max_length=4000)
    baseline_value: Optional[float] = None
    target_value: Optional[float] = None
    actual_value: Optional[float] = None
    unit: str = Field(default="", max_length=32)
    direction: OutcomeDirection = OutcomeDirection.INCREASE
    measurement_start: Optional[date] = None
    measurement_end: Optional[date] = None
    status: Optional[OutcomeStatus] = None
    owner_id: Optional[str] = None
    data_source: str = Field(default="", max_length=240)
    notes: str = Field(default="", max_length=8000)

    @model_validator(mode="after")
    def _window_ordered(self):
        if self.measurement_start and self.measurement_end and self.measurement_end < self.measurement_start:
            raise ValueError("The measurement end date cannot be before the start date")
        return self


class OutcomeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=5, max_length=240)
    action_id: Optional[str] = None
    metric_definition: Optional[str] = Field(default=None, min_length=5, max_length=4000)
    baseline_value: Optional[float] = None
    target_value: Optional[float] = None
    actual_value: Optional[float] = None
    unit: Optional[str] = Field(default=None, max_length=32)
    direction: Optional[OutcomeDirection] = None
    measurement_start: Optional[date] = None
    measurement_end: Optional[date] = None
    status: Optional[OutcomeStatus] = None
    owner_id: Optional[str] = None
    data_source: Optional[str] = Field(default=None, max_length=240)
    notes: Optional[str] = Field(default=None, max_length=8000)

    @model_validator(mode="after")
    def _window_ordered(self):
        if self.measurement_start and self.measurement_end and self.measurement_end < self.measurement_start:
            raise ValueError("The measurement end date cannot be before the start date")
        return self


class OutcomeOut(ORMModel):
    id: str
    code: str
    name: str
    decision_id: str
    action_id: Optional[str]
    metric_definition: str
    baseline_value: Optional[float]
    target_value: Optional[float]
    actual_value: Optional[float]
    unit: str
    direction: OutcomeDirection
    measurement_start: Optional[date]
    measurement_end: Optional[date]
    status: OutcomeStatus
    owner_id: Optional[str]
    data_source: str
    recorded_at: Optional[datetime]
    notes: str
    created_at: datetime
    updated_at: datetime
    decision: Optional[Ref] = None
    action: Optional[Ref] = None
    owner: Optional[Ref] = None
    project_id: Optional[str] = None
    is_overdue: bool = False
    status_reason: str = ""


class OutcomeListResponse(BaseModel):
    items: list[OutcomeOut]
    total: int
    status_counts: dict[str, int] = Field(default_factory=dict)
    measurement_due: int = 0
