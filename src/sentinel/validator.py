"""Zone 1 — Sentinel: deterministic schema validation against the Golden Schema."""

from __future__ import annotations

from pydantic import ValidationError

from src.contracts.golden_schema import DriftReport, FieldError, UserProfile


# Known aliases: fields that have been renamed upstream.
# The Sentinel reports these as "missing" — the Diagnostician proposes the mapping.
KNOWN_ALIASES: dict[str, str] = {
    "customer_contact": "user_email",
}


def apply_aliases(raw_data: list[dict]) -> list[dict]:
    """Rename known aliased fields before validation.

    This is a deterministic pre-processing step so the Sentinel can handle
    known drift patterns without invoking the Diagnostician LLM.
    """
    resolved: list[dict] = []
    for row in raw_data:
        new_row = {}
        for key, value in row.items():
            canonical_key = KNOWN_ALIASES.get(key, key)
            new_row[canonical_key] = value
        resolved.append(new_row)
    return resolved


def validate_payload(
    raw_data: list[dict],
    *,
    max_dirty_samples: int = 3,
) -> DriftReport | list[UserProfile]:
    """Validate a list of raw dicts against the Golden Schema.

    Returns:
        - list[UserProfile] if **every** row passes validation.
        - DriftReport if any row fails.
    """
    # Pre-process: resolve known aliases deterministically
    aliased_data = apply_aliases(raw_data)

    validated: list[UserProfile] = []
    all_errors: list[FieldError] = []
    dirty_sample: list[dict] = []

    for i, row in enumerate(aliased_data):
        try:
            validated.append(UserProfile.model_validate(row))
        except ValidationError as exc:
            if len(dirty_sample) < max_dirty_samples:
                # Keep original (pre-alias) data in dirty_sample for Diagnostician
                dirty_sample.append(raw_data[i])
            for err in exc.errors():
                field = str(err["loc"][0]) if err["loc"] else "unknown"
                all_errors.append(
                    FieldError(
                        field=field,
                        error_type=err["type"],
                        expected=str(err.get("input", "")),
                        got=str(row.get(field, None)),
                    )
                )

    if not all_errors:
        return validated

    # Deduplicate errors by (field, error_type) for cleaner report
    seen: set[tuple[str, str]] = set()
    unique_errors: list[FieldError] = []
    for e in all_errors:
        key = (e.field, e.error_type)
        if key not in seen:
            seen.add(key)
            unique_errors.append(e)

    return DriftReport(
        total_rows=len(raw_data),
        failed_rows=len(raw_data) - len(validated),
        errors=unique_errors,
        dirty_sample=dirty_sample,
    )
