"""Tests for Zone 1 — Sentinel validator."""

from src.contracts.golden_schema import DriftReport, UserProfile
from src.sentinel.validator import KNOWN_ALIASES, apply_aliases, validate_payload


CLEAN_ROW = {
    "user_id": 1,
    "user_email": "alice@example.com",
    "full_name": "Alice Johnson",
    "department": "Engineering",
    "created_at": "2024-01-15T10:30:00",
}

DRIFTED_ROW = {
    "user_id": 1,
    "customer_contact": "alice@example.com",  # renamed field
    "full_name": "Alice Johnson",
    "department": "Engineering",
    "created_at": "01/15/2024",  # wrong date format
}


class TestSentinelPass:
    def test_clean_data_passes(self):
        result = validate_payload([CLEAN_ROW])
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], UserProfile)

    def test_multiple_clean_rows(self):
        result = validate_payload([CLEAN_ROW] * 5)
        assert isinstance(result, list)
        assert len(result) == 5


class TestSentinelFail:
    def test_missing_field_produces_report(self):
        row = {k: v for k, v in CLEAN_ROW.items() if k != "user_email"}
        result = validate_payload([row])
        assert isinstance(result, DriftReport)
        assert result.failed_rows == 1
        assert any(e.field == "user_email" and e.error_type == "missing" for e in result.errors)

    def test_drifted_row_produces_report(self):
        result = validate_payload([DRIFTED_ROW])
        assert isinstance(result, DriftReport)
        assert result.failed_rows == 1

    def test_drifted_report_has_dirty_sample(self):
        result = validate_payload([DRIFTED_ROW])
        assert isinstance(result, DriftReport)
        assert len(result.dirty_sample) == 1
        # dirty_sample keeps original (pre-alias) data for Diagnostician
        assert "customer_contact" in result.dirty_sample[0]

    def test_mixed_rows_reports_partial_failure(self):
        result = validate_payload([CLEAN_ROW, DRIFTED_ROW])
        assert isinstance(result, DriftReport)
        assert result.total_rows == 2
        assert result.failed_rows == 1

    def test_invalid_email_detected(self):
        row = {**CLEAN_ROW, "user_email": "not-an-email"}
        result = validate_payload([row])
        assert isinstance(result, DriftReport)
        assert any(e.field == "user_email" for e in result.errors)

    def test_bad_date_format_detected(self):
        row = {**CLEAN_ROW, "created_at": "01/15/2024"}
        result = validate_payload([row])
        assert isinstance(result, DriftReport)
        assert any(e.field == "created_at" for e in result.errors)

    def test_summary_is_readable(self):
        result = validate_payload([DRIFTED_ROW])
        assert isinstance(result, DriftReport)
        summary = result.to_summary()
        assert "Schema Drift Detected" in summary


class TestAliasResolution:
    def test_apply_aliases_renames_known_fields(self):
        row = {"customer_contact": "a@b.com", "full_name": "Alice"}
        result = apply_aliases([row])
        assert "user_email" in result[0]
        assert "customer_contact" not in result[0]

    def test_apply_aliases_preserves_unknown_fields(self):
        row = {"user_id": 1, "extra_field": "x"}
        result = apply_aliases([row])
        assert "extra_field" in result[0]

    def test_alias_resolved_date_still_fails(self):
        """After alias, date format error is still caught."""
        result = validate_payload([DRIFTED_ROW])
        assert isinstance(result, DriftReport)
        assert any(e.field == "created_at" for e in result.errors)
