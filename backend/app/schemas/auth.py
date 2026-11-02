"""Authentication contracts."""

from pydantic import BaseModel, Field, field_validator


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
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid email address.")
        return value


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
