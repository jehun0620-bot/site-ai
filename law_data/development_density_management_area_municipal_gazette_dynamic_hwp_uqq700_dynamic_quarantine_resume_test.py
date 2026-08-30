# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S49
Dynamic-quarantine wrapper for hardened S36-H2.

Loads every TECHNICAL_UNRESOLVED_QUARANTINED row from cumulative state and
injects it into H2's quarantine policy before H2 selects the next batch.
This prevents reconciled technical orphans from being retried and appended.
"""
from __future__ import annotations

import json
from pathlib import Path

from law_data import development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_quarantine_resume_test as h2

BASE_DIR = Path(__file__).resolve().parent.parent
STATE = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"


def norm(v) -> str:
    return str(v or "").strip()


def main() -> None:
    if not STATE.exists():
        raise FileNotFoundError(STATE)

    state = json.loads(STATE.read_text(encoding="utf-8"))
    results = state.get("results") or []
    dynamic = {}
    for r in results:
        if r.get("status") != "TECHNICAL_UNRESOLVED_QUARANTINED":
            continue
        pst = norm(r.get("pstSn"))
        if not pst:
            continue
        dynamic[pst] = {
            "gazette_number": r.get("gazette_number"),
            "reason": r.get("quarantine_reason") or r.get("reason") or r.get("error") or "TECHNICAL_UNRESOLVED_QUARANTINED",
            "status": "TECHNICAL_UNRESOLVED_QUARANTINED",
            "legal_negative_evidence": False,
        }

    if not dynamic:
        raise AssertionError("no dynamic quarantine rows found in cumulative state")

    original = dict(h2.QUARANTINE)
    h2.QUARANTINE.clear()
    h2.QUARANTINE.update(original)
    h2.QUARANTINE.update(dynamic)

    print("=" * 60)
    print("DYNAMIC QUARANTINE WRAPPER - S49")
    print("=" * 60)
    print("Static quarantine:", sorted(original))
    print("State quarantine:", sorted(dynamic))
    print("Effective quarantine:", sorted(h2.QUARANTINE))
    print("Negative evidence: DISABLED")

    if not set(dynamic).issubset(set(h2.QUARANTINE)):
        raise AssertionError("dynamic quarantine injection failed")

    h2.main()

    after = json.loads(STATE.read_text(encoding="utf-8"))
    after_results = after.get("results") or []
    pst_list = [norm(r.get("pstSn")) for r in after_results if norm(r.get("pstSn"))]
    duplicates = sorted({p for p in pst_list if pst_list.count(p) > 1})
    after_q = set(map(str, after.get("quarantined_pstSn") or []))
    after_processed = set(map(str, after.get("processed_pstSn") or []))

    vals = {
        "dynamic quarantine retained": set(dynamic).issubset(after_q),
        "dynamic quarantine not processed": not (set(dynamic) & after_processed),
        "no duplicate pstSn after batch": not duplicates,
        "negative evidence disabled": not after.get("negative_evidence_allowed", False),
    }
    print("\nS49 POST-VALIDATION")
    print("Duplicate pstSn:", duplicates)
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("dynamic quarantine wrapper post-validation failed")


if __name__ == "__main__":
    main()
