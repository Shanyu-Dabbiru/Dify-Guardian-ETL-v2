"""Zone 2 — Diagnostician: LLM prompt template for drift analysis."""

from __future__ import annotations

import json

from src.contracts.golden_schema import DriftReport

SYSTEM_PROMPT = """You are a data schema analyst. You receive a drift report showing
validation errors between incoming data and an expected schema. Your job is to propose
a corrective field mapping that will transform the broken data to match the expected schema.

The expected schema fields are:
  - user_id: int
  - user_email: str (valid email format)
  - full_name: str
  - department: str
  - created_at: str (ISO 8601 format, e.g. 2024-01-15T10:30:00)

Rules:
1. Only propose mappings you are confident about.
2. If a field is missing, check if a renamed version exists in the dirty data.
3. If a date format is wrong, specify the format conversion.
4. Output ONLY valid JSON. No markdown fences, no explanation outside the JSON.

Output format:
{
  "corrections": [
    {
      "old_field": "<field_name_in_dirty_data>",
      "new_field": "<expected_field_name>",
      "reason": "<brief explanation>"
    }
  ],
  "date_fixes": [
    {
      "field": "created_at",
      "input_format": "%m/%d/%Y",
      "output_format": "iso8601"
    }
  ]
}"""


def build_drift_prompt(drift_report: DriftReport) -> str:
    """Build a user message containing the drift report and dirty sample for the LLM."""
    report_json = json.dumps(drift_report.model_dump(), indent=2, default=str)
    return (
        f"## Drift Report\n```json\n{report_json}\n```\n\n"
        f"Analyze the errors and dirty data sample. "
        f"Propose corrective mappings as JSON."
    )
