"""End-to-end tests for the full pipeline via orchestrator."""

from src.orchestrator import run_pipeline


class TestCleanPath:
    def test_golden_csv_passes_sentinel(self):
        result = run_pipeline("demo/golden.csv")
        assert "PASS" in result
        assert "5 rows validated" in result


class TestHealPath:
    def test_drifted_csv_triggers_heal(self):
        result = run_pipeline("demo/drifted.csv")
        assert "Drift Detected" in result
        assert "customer_contact" in result
        assert "APPROVED" in result
        assert "healed" in result.lower()

    def test_drifted_healed_csv_has_correct_fields(self):
        result = run_pipeline("demo/drifted.csv")
        # The healed CSV output should contain user_email, not customer_contact
        assert "user_email" in result
        assert "2024-01-15T00:00:00" in result  # ISO date


class TestRejectedPath:
    def test_rejection_halts_pipeline(self):
        result = run_pipeline("demo/drifted.csv", simulate_approval=False)
        assert "REJECTED" in result
        assert "healed" not in result.lower()
