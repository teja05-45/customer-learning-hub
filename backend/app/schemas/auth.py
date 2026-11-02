"""Authentication contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Role = Literal["admin", "ceo", "business_owner", "researcher", "cx"]


def normalise_email(value: str) -> str:
    value = value.strip().lower()
    if "@" not in value or value.startswith("@") or value.endswith("@"):
        raise ValueError("Enter a valid email address.")
    return value


class DemoLoginRequest(BaseModel):
    user_id: str


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=160)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class RegisterRequest(BaseModel):
    """First-run claim of an empty workspace."""

    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=160)
    password: str = Field(min_length=10, max_length=200)
    organisation_name: str = Field(min_length=2, max_length=160)

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return normalise_email(value)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


class AuthUser(BaseModel):
    id: str
    name: str
    email: str
    role: str
    job_title: str
    initials: str


class AuthMessage(BaseModel):
    message: str


class MemberCreate(BaseModel):
    """An administrator creating an account for a colleague."""

    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=160)
    role: Role
    job_title: str = Field(default="", max_length=120)
    password: str = Field(min_length=10, max_length=200)

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return normalise_email(value)


class MemberUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    role: Role | None = None
    job_title: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None


class AdminPasswordReset(BaseModel):
    new_password: str = Field(min_length=10, max_length=200)


class MemberOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    job_title: str
    initials: str
    is_active: bool
    created_at: datetime
