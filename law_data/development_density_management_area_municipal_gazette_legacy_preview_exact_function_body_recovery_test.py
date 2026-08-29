# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S24
Offline recovery of exact function bodies from S21 captured function-like text.
Targets getContextPath() and getInfoURL() first, plus isModuleType().
Uses brace balancing and a small JS-string-aware scanner.

No network, no cumulative state mutation, no legal promotion.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
IN = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_legacy_preview_module_path_contract.json"
OUT = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_legacy_preview_exact_function_body_recovery.json"

TARGETS = ("isModuleType", "getContextPath", "getInfoURL")


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def extract_balanced_function(text: str, name: str) -> str | None:
    patterns = [
        rf"this\.{re.escape(name)}\s*=\s*function\s*\([^)]*\)\s*\{{",
        rf"{re.escape(name)}\s*=\s*function\s*\([^)]*\)\s*\{{",
    ]
    start = -1
    brace = -1
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            start = m.start()
            brace = text.find("{", m.start(), m.end()+1)
            break
    if start < 0 or brace < 0:
        return None

    depth = 0
    quote = None
    escape = False
    i = brace
    while i < len(text):
        ch = text[i]
        if quote is not None:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                quote = None
        else:
            if ch in ("'", '"', "`"):
                quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return normalize(text[start:i+1])
        i += 1
    return None


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("LEGACY PREVIEW EXACT FUNCTION BODY RECOVERY")
    print("=" * 60)
    print("Network: DISABLED")
    print("State mutation: DISABLED")
    print()

    if not IN.exists():
        raise FileNotFoundError(IN)
    data = json.loads(IN.read_text(encoding="utf-8"))
    evidence = data.get("evidence", {})

    recovered = {}
    for name in TARGETS:
        body = None
        candidates = evidence.get(name, {}).get("function_like", [])
        for text in candidates:
            body = extract_balanced_function(str(text), name)
            if body:
                break
        recovered[name] = body
        print(f"-- {name} --")
        print(body or "NOT RECOVERED")
        print()

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S24",
        "source": str(IN),
        "recovered": recovered,
        "network_request_count": 0,
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "S21 input exists": IN.exists(),
        "isModuleType recovered": bool(recovered.get("isModuleType")),
        "getContextPath recovered": bool(recovered.get("getContextPath")),
        "getInfoURL recovered": bool(recovered.get("getInfoURL")),
        "network disabled": output["network_request_count"] == 0,
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("SUMMARY")
    for k in TARGETS:
        print(k, "recovered:", bool(recovered.get(k)))
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("exact function body recovery validation failed")


if __name__ == "__main__":
    main()
