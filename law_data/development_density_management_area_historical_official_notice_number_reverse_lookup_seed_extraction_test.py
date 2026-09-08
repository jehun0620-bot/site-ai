# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_historical_official_notice_number_reverse_lookup_seed_extraction.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_HISTORICAL_OFFICIAL_NOTICE_NUMBER_REVERSE_LOOKUP"

# Scan only local, previously produced evidence artifacts. No network requests.
INCLUDE_HINTS = [
    "development_density_management_area",
    "seongnam",
    "historical",
    "planning",
    "gazette",
    "notice",
    "ordinance",
    "council",
    "research",
]
EXCLUDE_NAMES = {OUT.name}

# Keep patterns intentionally strict enough to avoid arbitrary year-number pairs.
PATTERNS = [
    ("NOTICE_FULL", re.compile(r"(?:성남시|경기도|국토교통부|건설교통부|도시계획)?\s*고시\s*제?\s*(\d{4})\s*[-–]\s*(\d{1,5})\s*호")),
    ("PUBLIC_NOTICE_FULL", re.compile(r"(?:성남시|경기도|국토교통부|건설교통부)?\s*공고\s*제?\s*(\d{4})\s*[-–]\s*(\d{1,5})\s*호")),
    ("GENERIC_DOCUMENT_NO", re.compile(r"제\s*(\d{4})\s*[-–]\s*(\d{1,5})\s*호")),
]

TARGET_TERMS = [
    "개발밀도관리구역",
    "개발밀도 관리구역",
    "개발밀도",
    "밀도관리구역",
]
CONTEXT_TERMS = [
    "고시", "공고", "도시관리계획", "도시계획", "지형도면", "결정", "변경", "지정", "해제",
    "성남", "분당", "판교", "산성", "시행지침", "지구단위계획",
]
NEGATIVE_CONTEXT_TERMS = [
    "시험", "채용", "합격", "입찰", "계약", "인사", "모집",
]


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def iter_strings(node, path: str = "$", depth: int = 0):
    if depth > 12:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            yield from iter_strings(v, f"{path}.{k}", depth + 1)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from iter_strings(v, f"{path}[{i}]", depth + 1)
    elif isinstance(node, str):
        yield path, node


def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def make_window(text: str, start: int, end: int, radius: int = 220) -> str:
    return normalize_space(text[max(0, start - radius): min(len(text), end + radius)])


def canonical_no(year: str, seq: str) -> str:
    return f"{int(year):04d}-{int(seq)}"


def score_candidate(kind: str, literal: str, context: str, source_file: str) -> tuple[int, list[str]]:
    score = 0
    reasons = []
    if kind == "NOTICE_FULL":
        score += 35
        reasons.append("explicit_gosi_literal")
    elif kind == "PUBLIC_NOTICE_FULL":
        score += 20
        reasons.append("explicit_gongo_literal")
    else:
        score += 5
        reasons.append("generic_document_number_only")

    if any(t in context for t in TARGET_TERMS):
        score += 50
        reasons.append("target_term_nearby")
    elif "개발밀도" in context:
        score += 35
        reasons.append("weak_development_density_term_nearby")

    matched_context = [t for t in CONTEXT_TERMS if t in context]
    if matched_context:
        score += min(30, 5 * len(set(matched_context)))
        reasons.append("planning_or_notice_context")

    if "성남" in context or "seongnam" in source_file.lower():
        score += 15
        reasons.append("seongnam_context")

    if any(t in context for t in NEGATIVE_CONTEXT_TERMS):
        score -= 40
        reasons.append("negative_nonplanning_context")

    return score, reasons


def collect_candidates() -> tuple[list[dict], int, int]:
    rows = []
    scanned_files = 0
    scanned_strings = 0
    for p in sorted(OUT_DIR.glob("*.json")):
        if p.name in EXCLUDE_NAMES:
            continue
        name_lower = p.name.lower()
        if not any(h in name_lower for h in INCLUDE_HINTS):
            continue
        data = load_json(p)
        if data is None:
            continue
        scanned_files += 1
        for json_path, text in iter_strings(data):
            scanned_strings += 1
            for kind, pat in PATTERNS:
                for m in pat.finditer(text):
                    year, seq = m.group(1), m.group(2)
                    context = make_window(text, m.start(), m.end())
                    score, reasons = score_candidate(kind, m.group(0), context, p.name)
                    rows.append({
                        "source_file": str(p),
                        "json_path": json_path,
                        "pattern_kind": kind,
                        "literal": normalize_space(m.group(0)),
                        "canonical_document_no": canonical_no(year, seq),
                        "year": int(year),
                        "sequence": int(seq),
                        "context": context,
                        "target_exact_nearby": TARGET in context or "개발밀도 관리구역" in context,
                        "target_weak_nearby": "개발밀도" in context,
                        "notice_term_nearby": "고시" in context,
                        "planning_context_nearby": any(t in context for t in ["도시관리계획", "도시계획", "지형도면", "지정", "해제", "변경"]),
                        "seongnam_context_nearby": "성남" in context or "seongnam" in p.name.lower(),
                        "score": score,
                        "score_reasons": reasons,
                    })
    return rows, scanned_files, scanned_strings


def dedupe_and_rank(rows: list[dict]) -> list[dict]:
    bucket = {}
    for r in rows:
        key = r["canonical_document_no"]
        b = bucket.setdefault(key, {
            "canonical_document_no": key,
            "year": r["year"],
            "sequence": r["sequence"],
            "max_score": r["score"],
            "occurrence_count": 0,
            "explicit_notice_occurrence_count": 0,
            "target_exact_occurrence_count": 0,
            "target_weak_occurrence_count": 0,
            "source_files": set(),
            "occurrences": [],
        })
        b["max_score"] = max(b["max_score"], r["score"])
        b["occurrence_count"] += 1
        b["explicit_notice_occurrence_count"] += int(r["pattern_kind"] == "NOTICE_FULL")
        b["target_exact_occurrence_count"] += int(r["target_exact_nearby"])
        b["target_weak_occurrence_count"] += int(r["target_weak_nearby"])
        b["source_files"].add(r["source_file"])
        if len(b["occurrences"]) < 12:
            b["occurrences"].append(r)

    ranked = []
    for b in bucket.values():
        corroboration = min(20, max(0, len(b["source_files"]) - 1) * 5)
        explicit_bonus = min(15, b["explicit_notice_occurrence_count"] * 3)
        target_bonus = min(20, b["target_exact_occurrence_count"] * 10 + b["target_weak_occurrence_count"] * 3)
        rank_score = b["max_score"] + corroboration + explicit_bonus + target_bonus
        ranked.append({
            **{k: v for k, v in b.items() if k != "source_files"},
            "source_file_count": len(b["source_files"]),
            "source_files": sorted(b["source_files"]),
            "rank_score": rank_score,
            "reverse_lookup_eligible": (
                b["explicit_notice_occurrence_count"] > 0
                and (b["target_exact_occurrence_count"] > 0 or b["target_weak_occurrence_count"] > 0)
            ),
            "designation_identity_verified": False,
            "current_validity_verified": False,
            "site_inclusion_verified": False,
        })
    ranked.sort(key=lambda x: (-x["rank_score"], -x["explicit_notice_occurrence_count"], x["year"], x["sequence"]))
    return ranked


def main() -> None:
    print("=" * 78)
    print("UQQ700 HISTORICAL OFFICIAL NOTICE-NUMBER REVERSE LOOKUP SEED EXTRACTION - S230C")
    print("=" * 78)
    print("Purpose: extract document/notice-number seeds from existing local evidence only")
    print("HTTP/network search: DISABLED")
    print("Candidate notice number != designation identity verified")
    print("No candidate != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    rows, scanned_files, scanned_strings = collect_candidates()
    ranked = dedupe_and_rank(rows)
    eligible = [r for r in ranked if r["reverse_lookup_eligible"]]

    if eligible:
        classification = "UQQ700_HISTORICAL_OFFICIAL_NOTICE_NUMBER_REVERSE_LOOKUP_SEEDS_EXTRACTED"
        semantic = "ONE_OR_MORE_NOTICE_NUMBER_SEEDS_WITH_TARGET_NEARBY_CONTEXT_WERE_EXTRACTED_FROM_EXISTING_LOCAL_EVIDENCE_WITHOUT_LEGAL_PROMOTION"
        next_action = "QUALIFY_OFFICIAL_REVERSE_LOOKUP_ENDPOINTS_FOR_ONLY_THE_EXTRACTED_NOTICE_NUMBER_SEEDS"
    elif ranked:
        classification = "UQQ700_HISTORICAL_DOCUMENT_NUMBERS_OBSERVED_BUT_NO_TARGET_QUALIFIED_NOTICE_SEED"
        semantic = "DOCUMENT_NUMBER_LITERALS_EXIST_IN_LOCAL_EVIDENCE_BUT_NONE_QUALIFY_AS_TARGET_NEARBY_EXPLICIT_NOTICE_NUMBER_SEEDS"
        next_action = "MOVE_TO_NEXT_HIGH_VALUE_OFFICIAL_ARCHIVAL_ENTRY_OR_REVIEW_TOP_CONTEXTUAL_NUMBERS_WITHOUT_LEGAL_PROMOTION"
    else:
        classification = "UQQ700_HISTORICAL_OFFICIAL_NOTICE_NUMBER_REVERSE_LOOKUP_NO_SEED_OBSERVED"
        semantic = "NO_NOTICE_OR_DOCUMENT_NUMBER_SEED_WAS_EXTRACTED_FROM_THE_AVAILABLE_LOCAL_OUTPUT_CORPUS"
        next_action = "MOVE_TO_NEXT_RANKED_HIGH_VALUE_OFFICIAL_ARCHIVAL_SOURCE_AND_KEEP_UQQ700_UNKNOWN"

    out = {
        "step": "STEP 17-21-C-16-8-T-168-S230C",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "http_search_executed": False,
        "scanned_json_file_count": scanned_files,
        "scanned_string_count": scanned_strings,
        "raw_occurrence_count": len(rows),
        "canonical_document_number_count": len(ranked),
        "reverse_lookup_eligible_seed_count": len(eligible),
        "ranked_document_numbers": ranked[:100],
        "reverse_lookup_eligible_seeds": eligible[:50],
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "notice_number_candidate_equals_designation_identity": False,
            "document_found_equals_current_validity": False,
            "no_seed_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "official_designation_identity_verified": False,
            "current_validity_verified": False,
            "site_spatial_inclusion_verified": False,
            "runtime_registration_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print("CANDIDATE RANKING")
    print("=" * 78)
    print(f"SCANNED JSON FILE COUNT: {scanned_files}")
    print(f"SCANNED STRING COUNT: {scanned_strings}")
    print(f"RAW OCCURRENCE COUNT: {len(rows)}")
    print(f"CANONICAL DOCUMENT NUMBER COUNT: {len(ranked)}")
    print(f"REVERSE LOOKUP ELIGIBLE SEED COUNT: {len(eligible)}")
    for i, r in enumerate(ranked[:20], 1):
        print(json.dumps({
            "rank": i,
            "document_no": r["canonical_document_no"],
            "rank_score": r["rank_score"],
            "explicit_notice_occurrences": r["explicit_notice_occurrence_count"],
            "target_exact_occurrences": r["target_exact_occurrence_count"],
            "target_weak_occurrences": r["target_weak_occurrence_count"],
            "source_file_count": r["source_file_count"],
            "reverse_lookup_eligible": r["reverse_lookup_eligible"],
        }, ensure_ascii=False))

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Notice number candidate == designation identity verified: False")
    print("No seed == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "no HTTP search": out["http_search_executed"] is False,
        "candidate does not equal designation": out["summary"]["notice_number_candidate_equals_designation_identity"] is False,
        "document found not current validity": out["summary"]["document_found_equals_current_validity"] is False,
        "no seed not legal absence": out["summary"]["no_seed_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "UQQ700_HISTORICAL_OFFICIAL_NOTICE_NUMBER_REVERSE_LOOKUP_SEEDS_EXTRACTED",
            "UQQ700_HISTORICAL_DOCUMENT_NUMBERS_OBSERVED_BUT_NO_TARGET_QUALIFIED_NOTICE_SEED",
            "UQQ700_HISTORICAL_OFFICIAL_NOTICE_NUMBER_REVERSE_LOOKUP_NO_SEED_OBSERVED",
        },
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for k, v in validation.items():
        print(f"{k}: {v}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT}")
    if not all(validation.values()):
        raise AssertionError("S230C validation failed")


if __name__ == "__main__":
    main()
