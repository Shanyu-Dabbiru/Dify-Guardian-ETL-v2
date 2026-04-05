"""Orchestrator — wires Zones 1-4 for local pipeline simulation.

Usage:
    python -m src.orchestrator demo/golden.csv
    python -m src.orchestrator demo/drifted.csv

Environment variables:
    USE_SIMULATED_LLM  — "true" to use hardcoded LLM response (default: false)
    LLM_PROVIDER       — "anthropic" (default) or "openai"
    ANTHROPIC_API_KEY   — for real LLM calls
    DIFY_DATASET_ID     — if set, upload healed data to Dify KB
    DIFY_BASE_URL       — Dify instance URL
    DIFY_API_KEY        — Dify API key
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys

from src.contracts.golden_schema import DriftReport, UserProfile
from src.sentinel.validator import validate_payload
from src.diagnostician.prompt_template import build_drift_prompt, SYSTEM_PROMPT
from src.healer.transformer import apply_corrections


# ── Hardcoded LLM response for local simulation ────────────────────────────
# In Dify, this would come from the LLM Node (Claude Sonnet).
SIMULATED_LLM_RESPONSE = {
    "corrections": [
        {
            "old_field": "customer_contact",
            "new_field": "user_email",
            "reason": "Field renamed from customer_contact to user_email",
        }
    ],
    "date_fixes": [
        {
            "field": "created_at",
            "input_format": "%m/%d/%Y",
            "output_format": "iso8601",
        }
    ],
}

USE_SIMULATED_LLM = os.environ.get("USE_SIMULATED_LLM", "false").lower() == "true"


def load_csv(path: str) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _get_llm_diagnosis(prompt: str) -> dict:
    """Call real LLM or fall back to simulation."""
    if USE_SIMULATED_LLM:
        return SIMULATED_LLM_RESPONSE

    from src.diagnostician.llm_client import diagnose

    try:
        return diagnose(prompt, SYSTEM_PROMPT)
    except Exception as exc:
        print(f"[DIAGNOSTICIAN] LLM call failed: {exc}\nFalling back to simulation.")
        return SIMULATED_LLM_RESPONSE


def _upload_to_dify_kb(healed: list[dict]) -> str | None:
    """Upload healed data to Dify Knowledge Base if configured."""
    dataset_id = os.environ.get("DIFY_DATASET_ID")
    if not dataset_id:
        return None

    try:
        from src.healer.dify_client import DifyKBClient

        with DifyKBClient() as client:
            result = client.upload_csv(dataset_id, healed, name="guardian_healed.csv")
            doc = result.get("document", {})
            return f"Uploaded document '{doc.get('name', 'unknown')}' (id: {doc.get('id', '?')})"
    except Exception as exc:
        return f"Dify upload skipped: {exc}"


def run_pipeline(csv_path: str, *, simulate_approval: bool = True) -> str:
    """Run the full 4-zone pipeline on a CSV file.

    Returns a human-readable summary string.
    """
    raw_data = load_csv(csv_path)

    # ── Zone 1: Sentinel ───────────────────────────────────────────────
    result = validate_payload(raw_data)

    if isinstance(result, list):
        # All rows valid — clean ingest path
        return (
            f"[SENTINEL] PASS — {len(result)} rows validated. "
            f"Proceeding to Knowledge Base ingestion.\n"
            f"[HEALER] Data is clean, no transformation needed."
        )

    # Drift detected
    drift_report: DriftReport = result
    summary = [drift_report.to_summary()]

    # ── Zone 2: Diagnostician (real LLM or simulation) ─────────────────
    prompt = build_drift_prompt(drift_report)
    mapping = _get_llm_diagnosis(prompt)

    if USE_SIMULATED_LLM:
        summary.append(f"\n[DIAGNOSTICIAN] Simulated LLM response:\n{json.dumps(mapping, indent=2)}")
    else:
        summary.append("[DIAGNOSTICIAN] Real LLM response received.")

    # ── Zone 3: HITL Gate ──────────────────────────────────────────────
    corrections = mapping["corrections"]
    date_fixes = mapping.get("date_fixes", [])

    md_proposal = "## Proposed Corrections\n\n"
    for c in corrections:
        md_proposal += f"- **{c['old_field']}** → **{c['new_field']}**: {c['reason']}\n"
    for d in date_fixes:
        md_proposal += f"- **{d['field']}**: Convert `{d['input_format']}` → `{d['output_format']}`\n"

    summary.append(f"\n[HITL] Proposal for admin review:\n{md_proposal}")

    if not simulate_approval:
        summary.append("[HITL] REJECTED — pipeline halted.")
        return "\n".join(summary)

    summary.append("[HITL] APPROVED — applying corrections.")

    # ── Zone 4: Healer ──────────────────────────────────────────────────
    healed = apply_corrections(raw_data, corrections, date_fixes)

    # Validate healed data against Golden Schema
    healed_result = validate_payload(healed)
    if isinstance(healed_result, list):
        summary.append(f"[HEALER] {len(healed_result)} rows healed and validated.")

        # Show healed data as CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=healed[0].keys())
        writer.writeheader()
        writer.writerows(healed)
        summary.append(f"\n[OUTPUT] Healed CSV:\n{output.getvalue()}")

        # Optional: upload to Dify KB
        if healed:
            upload_msg = _upload_to_dify_kb(healed)
            if upload_msg:
                summary.append(f"[HEALER] {upload_msg}")
    else:
        summary.append(f"[HEALER] ERROR — healed data still has errors:\n{healed_result.to_summary()}")
        summary.append("[HEALER] PIPELINE HALTED — data not uploaded.")
        return "\n".join(summary)

    return "\n".join(summary)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.orchestrator <csv_path>")
        print("  demo/golden.csv  — clean data (passes validation)")
        print("  demo/drifted.csv — broken data (triggers heal pipeline)")
        sys.exit(1)

    csv_path = sys.argv[1]
    output = run_pipeline(csv_path)
    print(output)
