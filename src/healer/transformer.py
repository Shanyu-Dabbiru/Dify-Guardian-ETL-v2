"""Zone 4 — Healer: apply corrective mappings to dirty data."""

from __future__ import annotations

from datetime import datetime


def apply_corrections(
    data: list[dict],
    corrections: list[dict],
    date_fixes: list[dict] | None = None,
) -> list[dict]:
    """Apply field renames and date format corrections to raw data rows.

    Args:
        data: List of raw dicts (the dirty data).
        corrections: List of {"old_field": str, "new_field": str, "reason": str}.
        date_fixes: Optional list of {"field": str, "input_format": str, "output_format": str}.

    Returns:
        New list of dicts with corrections applied.
    """
    date_fixes = date_fixes or []

    # Build rename map: old_field → new_field
    rename_map: dict[str, str] = {c["old_field"]: c["new_field"] for c in corrections}

    # Build date format map: field → (input_format, output_format)
    date_format_map: dict[str, tuple[str, str]] = {}
    for fix in date_fixes:
        date_format_map[fix["field"]] = (fix["input_format"], fix["output_format"])

    corrected: list[dict] = []
    for row in data:
        new_row: dict = {}
        for key, value in row.items():
            target_key = rename_map.get(key, key)
            new_row[target_key] = value

        # Apply date fixes
        for field, (input_fmt, output_fmt) in date_format_map.items():
            if field in new_row and isinstance(new_row[field], str):
                try:
                    dt = datetime.strptime(new_row[field], input_fmt)
                    new_row[field] = (
                        dt.isoformat() if output_fmt == "iso8601"
                        else dt.strftime(output_fmt)
                    )
                except ValueError:
                    pass  # leave as-is if parse fails

        corrected.append(new_row)

    return corrected
