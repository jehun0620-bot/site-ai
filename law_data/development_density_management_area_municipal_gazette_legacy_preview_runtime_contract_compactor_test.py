# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S18
Offline compactor for S17 preview runtime evidence.
Reads only the local S17 JSON and extracts high-value expressions showing
how fn/rs participate in preview resource construction.
No network, no state mutation, no legal promotion.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
IN = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_legacy_preview_runtime_focused_contract.json"
OUT = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_legacy_preview_runtime_contract_compactor.json"

TOKENS = (
    "result/attach", "preview/result", "location.search", "urlsearchparams",
    "getparameter", "fn", "rs", "ajax", "fetch", "$.get", "page",
    ".xml", ".json", ".txt", "resource",
)


def score(s: str) -> int:
    low = s.lower()
    sc = 0
    for t in TOKENS:
        if t in low:
            sc += 1
    if ("fn" in low and "rs" in low):
        sc += 3
    if any(x in low for x in ("+", "concat", "replace", "substring", "split", "encodeuri")):
        sc += 2
    if any(x in low for x in ("ajax", "fetch", "$.get")):
        sc += 2
    if any(x in low for x in (".xml", ".json", ".txt", "result/attach", "preview/result")):
        sc += 2
    return sc


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("LEGACY PREVIEW RUNTIME CONTRACT COMPACTOR")
    print("=" * 60)
    print("Network: DISABLED")
    print("State mutation: DISABLED")
    print()

    if not IN.exists():
        raise FileNotFoundError(IN)

    data = json.loads(IN.read_text(encoding="utf-8"))
    viewer = data.get("focused", {}).get("viewer", {})

    pool = []
    for x in viewer.get("assignments", []):
        pool.append(("assignment", normalize(str(x))))
    for x in viewer.get("literals", []):
        pool.append(("literal", normalize(str(x))))
    for anchor, vals in viewer.get("contexts", {}).items():
        for x in vals:
            pool.append((f"context:{anchor}", normalize(str(x))))

    seen = set()
    ranked = []
    for kind, text in pool:
        if not text or text in seen:
            continue
        seen.add(text)
        ranked.append({"kind": kind, "score": score(text), "text": text})

    ranked.sort(key=lambda r: (-r["score"], len(r["text"])))
    top = [r for r in ranked if r["score"] >= 4][:40]

    formula_like = []
    for r in top:
        low = r["text"].lower()
        if ("fn" in low or "rs" in low) and any(k in low for k in ("+", "concat", "replace", "substring", "split", "url", "ajax", "fetch", "$.get")):
            formula_like.append(r)

    path_like = []
    for r in top:
        low = r["text"].lower()
        if any(k in low for k in ("result/attach", "preview/result", ".xml", ".json", ".txt", "page", "resource")):
            path_like.append(r)

    print("TOP CONTRACT EVIDENCE")
    for i, r in enumerate(top[:20], 1):
        print(f"[{i}] score={r['score']} kind={r['kind']}")
        print(r["text"][:2600])
        print()

    print("FORMULA-LIKE")
    for i, r in enumerate(formula_like[:15], 1):
        print(f"[{i}] {r['text'][:2600]}")
    print()

    print("PATH-LIKE")
    for i, r in enumerate(path_like[:15], 1):
        print(f"[{i}] {r['text'][:2600]}")
    print()

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S18",
        "source": str(IN),
        "top_contract_evidence": top,
        "formula_like": formula_like,
        "path_like": path_like,
        "network_request_count": 0,
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "S17 input exists": IN.exists(),
        "viewer evidence loaded": bool(pool),
        "compacted evidence present": bool(top),
        "network disabled": output["network_request_count"] == 0,
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("SUMMARY")
    print("Evidence pool:", len(pool))
    print("Top compacted:", len(top))
    print("Formula-like:", len(formula_like))
    print("Path-like:", len(path_like))
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("preview runtime contract compactor validation failed")


if __name__ == "__main__":
    main()
