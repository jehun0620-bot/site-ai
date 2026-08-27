# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-24
Development Density Management Area
Municipal Gazette UQQ700 Metadata Candidate Filter

Filter the canonical municipal gazette row registry using row-local metadata only.
No network requests, no detail execution, no validity/spatial inference, no SITE promotion.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
T23_PATH = OUT_DIR / "development_density_management_area_municipal_gazette_historical_row_registry_recovery.json"
OUT_PATH = OUT_DIR / "development_density_management_area_municipal_gazette_uqq700_metadata_candidate_filter.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

DIRECT_PATTERNS = [
    re.compile(r"개발\s*밀도\s*관리\s*구역"),
    re.compile(r"개발밀도관리구역"),
]

RELATED_TERMS = [
    "개발밀도",
    "밀도관리",
    "기반시설부담",
    "기반시설 용량",
    "기반시설용량",
]

URBAN_CONTEXT_TERMS = [
    "도시관리계획",
    "도시계획",
    "도시기본계획",
    "지구단위계획",
    "용도지역",
    "용도지구",
    "용도구역",
    "국토의 계획 및 이용에 관한 법률",
    "국토계획법",
]

DESIGNATION_TERMS = [
    "지정",
    "결정",
    "변경",
    "고시",
    "해제",
]


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def contains_direct(text: str) -> bool:
    return any(pattern.search(text) for pattern in DIRECT_PATTERNS)


def hits(text: str, terms: List[str]) -> List[str]:
    return [term for term in terms if term in text]


def classify(row: Dict[str, Any]) -> Dict[str, Any] | None:
    text = norm(row.get("row_text"))
    direct = contains_direct(text)
    related = hits(text, RELATED_TERMS)
    urban = hits(text, URBAN_CONTEXT_TERMS)
    designation = hits(text, DESIGNATION_TERMS)

    tier = None
    reasons: List[str] = []
    if direct:
        tier = "DIRECT_UQQ700_METADATA_MATCH"
        reasons.append("DIRECT_TARGET_IDENTITY_MATCH")
    elif related and designation:
        tier = "RELATED_DENSITY_DESIGNATION_METADATA_MATCH"
        reasons.extend([f"RELATED:{x}" for x in related])
        reasons.extend([f"DESIGNATION:{x}" for x in designation])
    elif urban and designation and any(term in text for term in ["개발", "밀도", "기반시설"]):
        tier = "URBAN_CONTEXT_WEAK_METADATA_MATCH"
        reasons.extend([f"URBAN:{x}" for x in urban])
        reasons.extend([f"DESIGNATION:{x}" for x in designation])

    if tier is None:
        return None

    return {
        "source_family": row.get("source_family"),
        "gazette_number": row.get("gazette_number"),
        "date": row.get("date"),
        "pstSn": row.get("pstSn"),
        "page_number": row.get("page_number"),
        "row_text": text,
        "candidate_tier": tier,
        "reasons": reasons,
        "metadata_only": True,
        "detail_request_executed": False,
        "document_identity_verified": False,
        "validity_verified": False,
        "spatial_inclusion_verified": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE UQQ700 METADATA CANDIDATE FILTER")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Network requests: DISABLED")
    print("Detail execution: DISABLED")
    print()

    if not T23_PATH.exists():
        raise FileNotFoundError(T23_PATH)
    t23 = json.loads(T23_PATH.read_text(encoding="utf-8"))
    rows = t23.get("canonical_gazette_rows") or []
    if not rows:
        raise AssertionError("T-23 canonical gazette row registry missing")

    candidates = [c for row in rows if (c := classify(row)) is not None]
    direct = [c for c in candidates if c["candidate_tier"] == "DIRECT_UQQ700_METADATA_MATCH"]
    related = [c for c in candidates if c["candidate_tier"] == "RELATED_DENSITY_DESIGNATION_METADATA_MATCH"]
    weak = [c for c in candidates if c["candidate_tier"] == "URBAN_CONTEXT_WEAK_METADATA_MATCH"]

    next_stage = direct if direct else related
    resolution = (
        "MUNICIPAL_GAZETTE_DIRECT_UQQ700_METADATA_CANDIDATE_FOUND"
        if direct
        else "MUNICIPAL_GAZETTE_RELATED_METADATA_CANDIDATE_FOUND"
        if related
        else "MUNICIPAL_GAZETTE_NO_UQQ700_METADATA_CANDIDATE"
    )

    output = {
        "step": "STEP 17-21-C-16-8-T-24 Municipal Gazette UQQ700 Metadata Candidate Filter",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": NEGATIVE_EVIDENCE_ALLOWED,
            "no_candidate_site_status": "UNKNOWN",
        },
        "method": {
            "input_row_count": len(rows),
            "network_requests_enabled": False,
            "detail_execution_enabled": False,
            "metadata_only_filter": True,
        },
        "summary": {
            "input_row_count": len(rows),
            "candidate_count": len(candidates),
            "direct_candidate_count": len(direct),
            "related_candidate_count": len(related),
            "weak_candidate_count": len(weak),
            "next_stage_candidate_count": len(next_stage),
        },
        "direct_candidates": direct,
        "related_candidates": related,
        "weak_candidates": weak,
        "next_stage_candidate_pool": next_stage,
        "resolution": resolution,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    duplicate_pst = len(candidates) - len({str(c.get("pstSn")) for c in candidates})
    unsafe = sum(1 for c in candidates if any([
        c.get("detail_request_executed"),
        c.get("document_identity_verified"),
        c.get("validity_verified"),
        c.get("spatial_inclusion_verified"),
        c.get("verified_positive"),
        c.get("runtime_registration_allowed"),
        c.get("site_positive_allowed"),
        c.get("site_negative_allowed"),
        c.get("final_positive_promotion_allowed"),
    ]))

    validations = {
        "T-23 input exists": T23_PATH.exists(),
        "canonical gazette rows loaded": len(rows) > 0,
        "network requests disabled": True,
        "detail execution disabled": True,
        "candidate pstSn unique": duplicate_pst == 0,
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "unsafe promotion leakage zero": unsafe == 0,
        "output written": OUT_PATH.exists() and OUT_PATH.stat().st_size > 0,
    }

    print("Input row count:", len(rows))
    print("Candidate count:", len(candidates))
    print("Direct UQQ700 candidates:", len(direct))
    print("Related density/designation candidates:", len(related))
    print("Weak urban-context candidates:", len(weak))
    print("Next-stage candidate count:", len(next_stage))
    print()
    for i, c in enumerate((direct or related or weak)[:10], start=1):
        print(f"CANDIDATE {i}")
        print("Tier:", c["candidate_tier"])
        print("Gazette:", c["gazette_number"])
        print("Date:", c["date"])
        print("pstSn:", c["pstSn"])
        print("Page:", c["page_number"])
        print("Text:", c["row_text"])
        print("Reasons:", c["reasons"])
        print()
    print("Resolution:", resolution)
    print("Output:", OUT_PATH)
    print()
    print("VALIDATION")
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print("Duplicate pstSn leakage:", duplicate_pst)
    print("Unsafe promotion leakage:", unsafe)
    print("all_pass:", all(validations.values()))

    if not all(validations.values()):
        raise AssertionError("municipal gazette UQQ700 metadata candidate filter failed")


if __name__ == "__main__":
    main()
