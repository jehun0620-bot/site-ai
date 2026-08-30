# -*- coding: utf-8 -*-
"""S78: network-disabled triage of S77 Seongnam notice discovery-context candidates.

Ranks candidates using only S77 canonical metadata/provenance. This stage does
not fetch detail pages, download attachments, mutate state, or create legal
negative evidence. It prepares a bounded priority pool for S79 detail-text
inspection.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
INPUT_PATH = OUTPUT_DIR / "development_density_management_area_seongnam_notice_reverse_lookup_candidate_collection.json"
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_seongnam_notice_candidate_triage.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "NOTICE_NUMBER_REVERSE_LOOKUP"
MAX_PRIORITY_POOL = 40

YEAR_RE = re.compile(r"(?:고시|공고)\s*제?\s*(\d{4})\s*[-－]")

STRONG_TITLE_TERMS = {
    "개발밀도관리구역": 100,
    "개발밀도": 70,
    "용도구역": 30,
    "도시관리계획": 22,
    "도시계획": 18,
    "지형도면": 18,
    "결정(변경)": 14,
    "결정 변경": 14,
    "결정": 10,
    "변경": 8,
    "고시": 3,
}

DOWNRANK_TERMS = {
    "도로": -12,
    "공원": -12,
    "하천": -12,
    "주차장": -10,
    "학교": -10,
    "철도": -10,
    "개발행위허가 제한": -8,
    "지구단위계획": -4,
}


def norm(v):
    return re.sub(r"\s+", " ", str(v or "")).strip()


def extract_year(notice_number: str):
    m = YEAR_RE.search(notice_number or "")
    return int(m.group(1)) if m else None


def score_candidate(c):
    title = norm(c.get("title"))
    notice = norm(c.get("notice_number"))
    combined = f"{title} {notice}"
    score = 0
    reasons = []
    for term, weight in STRONG_TITLE_TERMS.items():
        if term.replace(" ", "") in combined.replace(" ", ""):
            score += weight
            reasons.append(f"TITLE_TERM:{term}:{weight:+d}")
    for term, weight in DOWNRANK_TERMS.items():
        if term.replace(" ", "") in combined.replace(" ", ""):
            score += weight
            reasons.append(f"DOWNRANK:{term}:{weight:+d}")
    year = extract_year(notice)
    if year is not None:
        if year <= 2010:
            score += 25; reasons.append("HISTORICAL_YEAR<=2010:+25")
        elif year <= 2015:
            score += 18; reasons.append("HISTORICAL_YEAR<=2015:+18")
        elif year <= 2020:
            score += 8; reasons.append("HISTORICAL_YEAR<=2020:+8")
    prov = c.get("provenance") or []
    queries = sorted({norm(p.get("query")) for p in prov if norm(p.get("query"))})
    if "도시관리계획" in queries and "지형도면" in queries:
        score += 12; reasons.append("MULTI_QUERY_URBAN+MAP:+12")
    if any(norm(p.get("srchKey")) == "cn" for p in prov):
        score += 5; reasons.append("CONTENT_SEARCH_HIT:+5")
    return score, reasons, year, queries


def main():
    print("=" * 60)
    print("SEONGNAM NOTICE CANDIDATE TRIAGE - S78")
    print("=" * 60)
    print("Network: DISABLED")
    print("Attachment download: DISABLED")
    print("State mutation: DISABLED")
    print("Negative evidence: DISABLED")

    if not INPUT_PATH.exists():
        raise FileNotFoundError(INPUT_PATH)
    src = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    candidates = src.get("candidates") or []

    ranked = []
    year_counts = Counter()
    class_counts = Counter()
    for c in candidates:
        score, reasons, year, queries = score_candidate(c)
        if year is not None:
            year_counts[str(year)] += 1
        cls = norm(c.get("candidate_class")) or "UNKNOWN"
        class_counts[cls] += 1
        ranked.append({
            "document_id": norm(c.get("document_id")),
            "detail_url": norm(c.get("detail_url")),
            "notice_number": norm(c.get("notice_number")),
            "title": norm(c.get("title")),
            "candidate_class": cls,
            "notice_year": year,
            "triage_score": score,
            "triage_reasons": reasons,
            "discovery_queries": queries,
            "provenance_count": len(c.get("provenance") or []),
        })

    ranked.sort(key=lambda r: (-r["triage_score"], r["notice_year"] if r["notice_year"] is not None else 9999, int(r["document_id"]) if r["document_id"].isdigit() else 10**12))
    priority_pool = ranked[:MAX_PRIORITY_POOL]

    summary = {
        "input_candidate_count": len(candidates),
        "ranked_candidate_count": len(ranked),
        "priority_pool_count": len(priority_pool),
        "candidate_class_counts": dict(class_counts),
        "notice_year_counts": dict(sorted(year_counts.items())),
        "top_score": priority_pool[0]["triage_score"] if priority_pool else None,
        "network_executed": False,
    }

    payload = {
        "step": "STEP 17-21-C-16-8-T-35-S78",
        "target_name": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "input": str(INPUT_PATH),
        "priority_pool": priority_pool,
        "ranked_candidates": ranked,
        "summary": summary,
        "network_executed": False,
        "attachment_body_download_executed": False,
        "state_mutation_executed": False,
        "negative_evidence_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "input candidate count preserved": len(candidates) == len(ranked),
        "candidate ids unique": len(ranked) == len({r["document_id"] for r in ranked}),
        "priority pool bounded": len(priority_pool) <= MAX_PRIORITY_POOL,
        "network disabled": not payload["network_executed"],
        "attachment download disabled": not payload["attachment_body_download_executed"],
        "state mutation disabled": not payload["state_mutation_executed"],
        "negative evidence disabled": not payload["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not any(payload[k] for k in ["site_positive_allowed", "site_negative_allowed", "runtime_registration_allowed", "final_positive_promotion_allowed"]),
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print("\nSUMMARY")
    for k, v in summary.items():
        print(f"{k}: {v}")
    print("\nTOP PRIORITY")
    for r in priority_pool[:20]:
        print({"id": r["document_id"], "year": r["notice_year"], "score": r["triage_score"], "notice": r["notice_number"], "title": r["title"], "reasons": r["triage_reasons"]})
    print("Output:", OUTPUT_PATH)

    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("S78 candidate triage validation failed")


if __name__ == "__main__":
    main()
