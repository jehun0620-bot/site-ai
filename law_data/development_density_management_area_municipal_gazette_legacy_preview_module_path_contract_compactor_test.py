# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S22
Offline compactor for S21 module path contract evidence.
Extracts only return expressions and assignments involving fn/rs/resultPath/fileName/contextPath/info URL.
No network, no cumulative state mutation, no legal promotion.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
IN = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_legacy_preview_module_path_contract.json"
OUT = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_legacy_preview_module_path_contract_compactor.json"

SYMBOLS = (
    "isModuleType", "getContextPath", "getInfoURL", "doAfterGetStatusForHTMLServer",
    "doAfterGetStatusForHTML", "resultPath", "fileName"
)

PATTERNS = [
    r"return\s+[^;]{0,1800};",
    r"(?:this\.)?(?:resultPath|fileName|contextPath|id)\s*=\s*[^;]{0,1800};",
    r"(?:var|let|const)\s+[A-Za-z_$][\w$]*\s*=\s*[^;]{0,1800}(?:fn|rs|resultPath|fileName|contextPath|info)[^;]{0,1800};",
]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def extract_from_text(text: str) -> list[str]:
    out = []
    seen = set()
    low = text.lower()
    if not any(k.lower() in low for k in ("fn", "rs", "resultpath", "filename", "contextpath", "info")):
        return out
    for pat in PATTERNS:
        for m in re.finditer(pat, text, flags=re.I | re.S):
            s = norm(m.group(0))
            sl = s.lower()
            if any(k in sl for k in ("fn", "rs", "resultpath", "filename", "contextpath", "getinfourl", "/info", "thumbnailxml")):
                if s not in seen:
                    seen.add(s)
                    out.append(s)
            if len(out) >= 30:
                return out
    return out


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("LEGACY PREVIEW MODULE PATH CONTRACT COMPACTOR")
    print("=" * 60)
    print("Network: DISABLED")
    print("State mutation: DISABLED")
    print()

    if not IN.exists():
        raise FileNotFoundError(IN)
    data = json.loads(IN.read_text(encoding="utf-8"))
    ev = data.get("evidence", {})

    compact = {}
    for sym in SYMBOLS:
        rows = []
        seen = set()
        src = ev.get(sym, {})
        for text in list(src.get("function_like", [])) + list(src.get("contexts", [])):
            for x in extract_from_text(str(text)):
                if x not in seen:
                    seen.add(x)
                    rows.append(x)
        compact[sym] = rows[:20]

    for sym in SYMBOLS:
        print(f"-- {sym} --")
        for i, x in enumerate(compact[sym], 1):
            print(f"[{i}] {x}")
        print()

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S22",
        "source": str(IN),
        "compact": compact,
        "network_request_count": 0,
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "S21 input exists": IN.exists(),
        "core compact evidence present": all(bool(compact[s]) for s in ("isModuleType", "getContextPath", "getInfoURL")),
        "network disabled": output["network_request_count"] == 0,
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("SUMMARY")
    for sym in SYMBOLS:
        print(sym, "compact rows:", len(compact[sym]))
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("legacy preview module path contract compactor validation failed")


if __name__ == "__main__":
    main()
