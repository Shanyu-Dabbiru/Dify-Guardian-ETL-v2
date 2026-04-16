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


def run_pipeline(csv_path: str, *, simulate_approval: bool = False) -> str:
    """Run the 4-step guardrailed pipeline on a CSV file.

    Returns a human-readable summary string.
    """
    raw_data = load_csv(csv_path)

    # ── Step 1: Validation ─────────────────────────────────────────────
    result = validate_payload(raw_data)

    if isinstance(result, list):
        # All rows valid — clean ingest path
        return (
            f"[VALIDATION] PASS — {len(result)} rows match the master schema.\n"
            f"[REPAIR] No fixes needed."
        )

    # Drift detected
    drift_report: DriftReport = result
    summary = [f"[VALIDATION] FAIL: Schema drift detected in {drift_report.failed_rows} rows."]

    # ── Step 2: Reasoning (AI Models) ──────────────────────────────────
    prompt = build_drift_prompt(drift_report)
    mapping = _get_llm_diagnosis(prompt)

    if USE_SIMULATED_LLM:
        summary.append(f"\n[AI REASONING] Simulated mapping proposal:\n{json.dumps(mapping, indent=2)}")
    else:
        summary.append("[AI REASONING] Correction proposal generated.")

    # ── Step 3: Review Gate (HITL) ─────────────────────────────────────
    corrections = mapping["corrections"]
    date_fixes = mapping.get("date_fixes", [])

    md_proposal = "PROPOSED CORRECTIONS:\n"
    for c in corrections:
        md_proposal += f"  • {c['old_field']} -> {c['new_field']} ({c['reason']})\n"
    for d in date_fixes:
        md_proposal += f"  • {d['field']}: Convert {d['input_format']} -> {d['output_format']}\n"

    summary.append(f"\n[REVIEW] Proposed fixes:\n{md_proposal}")
    
    # Print the current summary so the user sees the proposal before the input prompt
    print("\n".join(summary))
    
    approval = "y"
    if not simulate_approval:
        approval = input("\n> Approve these fixes to repair the data? (y/n): ").lower().strip()
    
    if approval != "y":
        return "[REVIEW] REJECTED — Pipeline halted. Data not pushed to Knowledge Base."

    print("[REVIEW] APPROVED — Applying repairs...")
    summary_final = ["[REVIEW] APPROVED — Applying repairs..."]

    # ── Step 4: Repair ──────────────────────────────────────────────────
    healed = apply_corrections(raw_data, corrections, date_fixes)

    # Validate healed data against Master Schema
    healed_result = validate_payload(healed)
    if isinstance(healed_result, list):
        summary_final.append(f"[REPAIR] SUCCESS: {len(healed_result)} rows repaired and verified.")

        # Optional: upload to Dify KB
        if healed:
            upload_msg = _upload_to_dify_kb(healed)
            if upload_msg:
                summary_final.append(f"[REPAIR] {upload_msg}")
    else:
        summary_final.append(f"[REPAIR] ERROR: Healed data still fails validation.")
        return "\n".join(summary_final)

    return "\n".join(summary_final)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.orchestrator <csv_path>")
        print("  demo/golden.csv  — clean data (passes validation)")
        print("  demo/drifted.csv — broken data (triggers heal pipeline)")
        sys.exit(1)

    csv_path = sys.argv[1]
    output = run_pipeline(csv_path)
    print(output)
