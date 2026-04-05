"""Golden Schema — the single source of truth for valid user-profile payloads."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, field_validator


class UserProfile(BaseModel):
    """Expected shape of a single user-profile record."""

    user_id: int
    user_email: str
    full_name: str
    department: str
    created_at: str

    @field_validator("user_email")
    @classmethod
    def email_must_be_valid(cls, v: str) -> str:
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(pattern, v):
            raise ValueError(f"invalid email format: {v}")
        return v

    @field_validator("created_at")
    @classmethod
    def created_at_must_be_iso(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError(
                f"created_at must be ISO 8601 (e.g. 2024-01-15T10:30:00), got: {v}"
            )
        return v


class FieldError(BaseModel):
    """A single field-level validation error."""

    field: str
    error_type: str  # "missing" | "invalid"
    expected: str
    got: str | None = None


class DriftReport(BaseModel):
    """Structured diff produced by the Sentinel when validation fails."""

    valid: bool = False
    total_rows: int
    failed_rows: int
    errors: list[FieldError]
    dirty_sample: list[dict]  # first few offending rows for the Diagnostician

    def to_summary(self) -> str:
        lines = [f"Schema Drift Detected: {self.failed_rows}/{self.total_rows} rows invalid"]
        for e in self.errors:
            got = f" (got: {e.got})" if e.got else ""
            lines.append(f"  - [{e.error_type}] {e.field}: expected {e.expected}{got}")
        return "\n".join(lines)
