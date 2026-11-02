"""Shared schema helpers and pagination envelope."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class PageMeta(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int


class Message(BaseModel):
    message: str
    detail: str | None = None


class Ref(BaseModel):
    id: str
    label: str
    sublabel: str | None = None


class Warning(BaseModel):
    code: str
    message: str = Field(description="Human readable explanation shown in the UI")
