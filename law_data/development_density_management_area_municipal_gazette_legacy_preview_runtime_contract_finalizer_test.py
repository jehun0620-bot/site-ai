# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S19
Final offline reduction of S18 preview runtime evidence.
Prints only the strongest URL-construction formulas and path-like candidates.
No network, no state mutation, no legal promotion.
"""
from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
IN = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_legacy_preview_runtime_contract_compactor.json"
OUT = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_legacy_preview_runtime_contract_finalizer.json"


def uniq_rows(rows):
    out = []
    seen = set()
    for r in rows:
        text = str(r.get("text", "")).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(r)
    return out


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("LEGACY PREVIEW RUNTIME CONTRACT FINALIZER")
    print("=" * 60)
    print("Network: DISABLED")
    print("State mutation: DISABLED")
    print()

    if not IN.exists():
        raise FileNotFoundError(IN)

    data = json.loads(IN.read_text(encoding="utf-8"))
    formula = uniq_rows(data.get("formula_like", []))
    path = uniq_rows(data.get("path_like", []))

    # Prefer rows that jointly expose fn/rs plus path/network construction.
    def fscore(r):
        t = r.get("text", "").lower()
        s = int(r.get("score", 0))
        if "fn" in t and "rs" in t:
            s += 5
        if any(x in t for x in ("result/attach", "preview/result")):
            s += 5
        if any(x in t for x in ("ajax", "fetch", "$.get", "url:")):
            s += 3
        if any(x in t for x in (".xml", ".json", ".txt", "page")):
            s += 3
        if any(x in t for x in ("+", "concat", "replace", "substring", "split")):
            s += 2
        return s

    formula.sort(key=lambda r: (-fscore(r), len(r.get("text", ""))))
    path.sort(key=lambda r: (-fscore(r), len(r.get("text", ""))))

    strongest_formula = formula[:10]
    strongest_path = path[:10]

    print("STRONGEST FORMULAS")
    for i, r in enumerate(strongest_formula, 1):
        print(f"[{i}] score={fscore(r)} kind={r.get('kind','')}")
        print(r.get("text", "")[:3600])
        print()

    print("STRONGEST PATH CANDIDATES")
    for i, r in enumerate(strongest_path, 1):
        print(f"[{i}] score={fscore(r)} kind={r.get('kind','')}")
        print(r.get("text", "")[:3600])
        print()

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S19",
        "source": str(IN),
        "strongest_formulas": strongest_formula,
        "strongest_path_candidates": strongest_path,
        "network_request_count": 0,
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "S18 input exists": IN.exists(),
        "formula evidence present": bool(strongest_formula),
        "path evidence present": bool(strongest_path),
        "network disabled": output["network_request_count"] == 0,
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("SUMMARY")
    print("Strongest formulas:", len(strongest_formula))
    print("Strongest path candidates:", len(strongest_path))
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("preview runtime contract finalizer validation failed")


if __name__ == "__main__":
    main()
