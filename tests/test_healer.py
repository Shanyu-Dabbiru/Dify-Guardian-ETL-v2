"""Tests for Zone 4 — Healer transformer."""

from src.healer.transformer import apply_corrections


class TestFieldRename:
    def test_single_field_rename(self):
        data = [{"customer_contact": "alice@example.com", "name": "Alice"}]
        corrections = [{"old_field": "customer_contact", "new_field": "user_email", "reason": "renamed"}]
        result = apply_corrections(data, corrections)
        assert result[0].get("user_email") == "alice@example.com"
        assert "customer_contact" not in result[0]

    def test_multiple_renames(self):
        data = [{"customer_contact": "a@b.com", "client_name": "Alice"}]
        corrections = [
            {"old_field": "customer_contact", "new_field": "user_email", "reason": "renamed"},
            {"old_field": "client_name", "new_field": "full_name", "reason": "renamed"},
        ]
        result = apply_corrections(data, corrections)
        assert result[0]["user_email"] == "a@b.com"
        assert result[0]["full_name"] == "Alice"

    def test_no_corrections_passes_through(self):
        data = [{"user_email": "a@b.com"}]
        result = apply_corrections(data, [])
        assert result == data


class TestDateFix:
    def test_us_date_to_iso(self):
        data = [{"created_at": "01/15/2024"}]
        date_fixes = [{"field": "created_at", "input_format": "%m/%d/%Y", "output_format": "iso8601"}]
        result = apply_corrections(data, [], date_fixes)
        assert result[0]["created_at"] == "2024-01-15T00:00:00"

    def test_already_iso_passes_through(self):
        data = [{"created_at": "2024-01-15T10:30:00"}]
        date_fixes = [{"field": "created_at", "input_format": "%m/%d/%Y", "output_format": "iso8601"}]
        result = apply_corrections(data, [], date_fixes)
        # parse fails → leaves as-is
        assert result[0]["created_at"] == "2024-01-15T10:30:00"


class TestCombined:
    def test_rename_and_date_fix(self):
        data = [{"customer_contact": "a@b.com", "created_at": "03/10/2024"}]
        corrections = [{"old_field": "customer_contact", "new_field": "user_email", "reason": "renamed"}]
        date_fixes = [{"field": "created_at", "input_format": "%m/%d/%Y", "output_format": "iso8601"}]
        result = apply_corrections(data, corrections, date_fixes)
        assert result[0]["user_email"] == "a@b.com"
        assert result[0]["created_at"] == "2024-03-10T00:00:00"
