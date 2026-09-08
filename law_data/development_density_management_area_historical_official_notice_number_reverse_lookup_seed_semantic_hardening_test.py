# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_S230C = OUT_DIR / "development_density_management_area_historical_official_notice_number_reverse_lookup_seed_extraction.json"
OUT = OUT_DIR / "development_density_management_area_historical_official_notice_number_reverse_lookup_seed_semantic_hardening.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_HISTORICAL_OFFICIAL_NOTICE_NUMBER_REVERSE_LOOKUP"

TARGET_TERMS = ["개발밀도관리구역", "개발밀도 관리구역"]
WEAK_TARGET_TERMS = ["개발밀도", "밀도관리구역"]
NOTICE_TERMS = ["고시", "고시문", "고시번호"]
PLANNING_TERMS = ["도시관리계획", "도시계획", "지형도면", "결정", "지정", "변경", "해제"]
CONTAMINATION_TERMS = [
    "검색결과", "검색 결과", "통합검색", "검색어", "query", "keyword", "search",
    "result_count", "reported_result_count", "query_echo", "raw_query_present",
    "candidate ranking", "reverse_lookup_eligible", "target_exact_occurrences",
]

# We reject generic 2026-heavy candidates unless there is stronger same-record evidence.
# This is not a legal/historical year rule; it is a contamination guard for the current corpus.
CURRENT_CORPUS_YEAR = 2026


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def source_stage_from_path(path: str) -> str:
    name = Path(path).name.lower()
    m = re.search(r"s(\d{2,3})", name)
    if m:
        return f"S{m.group(1)}"
    if "planning_plan_document" in name:
        return "S227_FAMILY"
    if "city_council" in name:
        return "S228_FAMILY"
    if "planning_research" in name:
        return "S229_FAMILY"
    return "UNKNOWN_STAGE"


def contamination_score(occ: dict) -> tuple[int, list[str]]:
    context = norm(occ.get("context", ""))
    path = str(occ.get("json_path", ""))
    source = str(occ.get("source_file", ""))
    joined = f"{context} {path} {source}".lower()
    score = 0
    reasons = []

    for term in CONTAMINATION_TERMS:
        if term.lower() in joined:
            score += 1
            reasons.append(f"contamination_term:{term}")

    if any(k in path.lower() for k in ["ranked_document_numbers", "reverse_lookup_eligible_seeds", "candidate", "search", "result"]):
        score += 3
        reasons.append("derived_or_search_result_path")

    if "development_density_management_area_historical_official_notice_number_reverse_lookup_seed_extraction" in source:
        score += 10
        reasons.append("self_derived_s230c_surface")

    return score, reasons


def identity_strength(occ: dict, year: int) -> tuple[int, list[str], bool]:
    context = norm(occ.get("context", ""))
    literal = norm(occ.get("literal", ""))
    path = str(occ.get("json_path", ""))
    source = str(occ.get("source_file", ""))

    score = 0
    reasons = []

    explicit_notice = occ.get("pattern_kind") == "NOTICE_FULL" and "고시" in literal
    exact_target = any(t in context for t in TARGET_TERMS)
    weak_target = any(t in context for t in WEAK_TARGET_TERMS)
    planning = any(t in context for t in PLANNING_TERMS)
    seongnam = "성남" in context or "seongnam" in source.lower()

    if explicit_notice:
        score += 4
        reasons.append("explicit_notice_literal")
    if exact_target:
        score += 6
        reasons.append("exact_target_same_context")
    elif weak_target:
        score += 2
        reasons.append("weak_target_same_context")
    if planning:
        score += 2
        reasons.append("planning_context_same_context")
    if seongnam:
        score += 2
        reasons.append("seongnam_context")

    # Prefer evidence rooted in record/document-like fields rather than ranked/search arrays.
    path_lower = path.lower()
    record_like = any(k in path_lower for k in [
        ".title", ".ttl", ".subject", ".document", ".notice", ".content", ".body",
        ".text", ".page_text", ".extracted_text", ".metadata", ".attachments", ".posts",
    ])
    if record_like:
        score += 3
        reasons.append("record_or_document_field")

    contam, contam_reasons = contamination_score(occ)
    score -= min(10, contam)
    reasons.extend(contam_reasons)

    if year == CURRENT_CORPUS_YEAR and not record_like:
        score -= 3
        reasons.append("current_year_without_record_evidence")

    strong_same_record = explicit_notice and exact_target and planning and record_like and contam == 0
    return score, reasons, strong_same_record


def classify_candidate(candidate: dict) -> dict:
    year = int(candidate.get("year") or 0)
    canonical = candidate.get("canonical_document_no")
    occs = candidate.get("occurrences") or []

    unique = {}
    evaluated = []
    for occ in occs:
        source = str(occ.get("source_file", ""))
        path = str(occ.get("json_path", ""))
        literal = norm(occ.get("literal", ""))
        context = norm(occ.get("context", ""))
        # Deduplicate exact repeated evidence from the same source/path/context.
        key = (source, path, literal, context)
        if key in unique:
            continue
        unique[key] = True
        score, reasons, strong = identity_strength(occ, year)
        evaluated.append({
            "source_file": source,
            "source_stage": source_stage_from_path(source),
            "json_path": path,
            "literal": literal,
            "context": context,
            "identity_score": score,
            "strong_same_record_evidence": strong,
            "reasons": reasons,
        })

    evaluated.sort(key=lambda x: (-x["identity_score"], x["source_file"], x["json_path"]))
    strong = [x for x in evaluated if x["strong_same_record_evidence"]]
    positive = [x for x in evaluated if x["identity_score"] >= 8]
    contaminated = [x for x in evaluated if any(r.startswith("contamination_term:") or r in {"derived_or_search_result_path", "self_derived_s230c_surface"} for r in x["reasons"])]

    independent_sources = sorted({x["source_file"] for x in positive})
    independent_stages = sorted({x["source_stage"] for x in positive})

    if strong and independent_sources:
        semantic_class = "QUALIFIED_SEED"
        reverse_lookup_allowed = True
        reason = "Explicit notice literal, exact target, planning context, and record/document field co-occur in non-contaminated evidence."
    elif positive:
        semantic_class = "CONTEXT_ONLY"
        reverse_lookup_allowed = False
        reason = "Some positive contextual evidence exists, but same-record notice identity linkage is not strong enough."
    else:
        semantic_class = "CONTAMINATED_OR_AMBIGUOUS"
        reverse_lookup_allowed = False
        reason = "Evidence is dominated by search/result/derived context, duplication, or weak proximity only."

    return {
        "canonical_document_no": canonical,
        "year": year,
        "sequence": candidate.get("sequence"),
        "s230c_rank_score": candidate.get("rank_score"),
        "s230c_occurrence_count": candidate.get("occurrence_count"),
        "s230c_explicit_notice_occurrence_count": candidate.get("explicit_notice_occurrence_count"),
        "s230c_target_exact_occurrence_count": candidate.get("target_exact_occurrence_count"),
        "s230c_target_weak_occurrence_count": candidate.get("target_weak_occurrence_count"),
        "unique_evidence_count": len(evaluated),
        "strong_same_record_evidence_count": len(strong),
        "positive_context_evidence_count": len(positive),
        "contaminated_evidence_count": len(contaminated),
        "independent_positive_source_count": len(independent_sources),
        "independent_positive_stage_count": len(independent_stages),
        "independent_positive_sources": independent_sources,
        "independent_positive_stages": independent_stages,
        "semantic_class": semantic_class,
        "reverse_lookup_allowed": reverse_lookup_allowed,
        "semantic_reason": reason,
        "best_evidence": evaluated[:8],
        "designation_identity_verified": False,
        "current_validity_verified": False,
        "site_inclusion_verified": False,
    }


def main() -> None:
    print("=" * 78)
    print("UQQ700 HISTORICAL NOTICE-NUMBER SEED SEMANTIC HARDENING - S230D")
    print("=" * 78)
    print("Purpose: remove duplication/search-result contamination from S230C seed candidates")
    print("HTTP/network search: DISABLED")
    print("Only QUALIFIED_SEED may proceed to official reverse lookup")
    print("Qualified seed != designation identity verified")
    print("No qualified seed != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    if not IN_S230C.exists():
        raise FileNotFoundError(f"Missing S230C output: {IN_S230C}")
    s230c = load_json(IN_S230C)
    ranked = s230c.get("ranked_document_numbers") or []

    hardened = [classify_candidate(c) for c in ranked]
    hardened.sort(key=lambda x: (
        0 if x["semantic_class"] == "QUALIFIED_SEED" else 1 if x["semantic_class"] == "CONTEXT_ONLY" else 2,
        -x["strong_same_record_evidence_count"],
        -x["positive_context_evidence_count"],
        -int(x.get("s230c_rank_score") or 0),
        x["year"],
        x["sequence"] or 0,
    ))

    qualified = [x for x in hardened if x["semantic_class"] == "QUALIFIED_SEED"]
    context_only = [x for x in hardened if x["semantic_class"] == "CONTEXT_ONLY"]
    contaminated = [x for x in hardened if x["semantic_class"] == "CONTAMINATED_OR_AMBIGUOUS"]

    if qualified:
        classification = "UQQ700_HISTORICAL_NOTICE_NUMBER_SEEDS_SEMANTICALLY_HARDENED_QUALIFIED"
        semantic = "ONE_OR_MORE_S230C_CANDIDATES_SURVIVED_DUPLICATION_AND_SEARCH_RESULT_CONTAMINATION_HARDENING_AS_SAME_RECORD_NOTICE_NUMBER_SEEDS"
        next_action = "QUALIFY_OFFICIAL_REVERSE_LOOKUP_ENDPOINTS_FOR_ONLY_S230D_QUALIFIED_SEEDS"
    else:
        classification = "UQQ700_HISTORICAL_NOTICE_NUMBER_SEEDS_SEMANTIC_HARDENING_NO_QUALIFIED_SEED"
        semantic = "S230C_RAW_SEEDS_DID_NOT_SURVIVE_SAME_RECORD_AND_CONTAMINATION_HARDENING_AS_QUALIFIED_NOTICE_NUMBER_SEEDS"
        next_action = "MOVE_TO_NEXT_RANKED_HIGH_VALUE_OFFICIAL_ARCHIVAL_SOURCE_WITHOUT_REVERSE_LOOKUP_OF_UNQUALIFIED_NUMBERS"

    out = {
        "step": "STEP 17-21-C-16-8-T-169-S230D",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "input_s230c": str(IN_S230C),
        "http_search_executed": False,
        "s230c_reverse_lookup_eligible_seed_count": s230c.get("reverse_lookup_eligible_seed_count"),
        "s230c_ranked_candidate_count": len(ranked),
        "semantic_hardened_candidate_count": len(hardened),
        "qualified_seed_count": len(qualified),
        "context_only_count": len(context_only),
        "contaminated_or_ambiguous_count": len(contaminated),
        "qualified_seeds": qualified,
        "context_only_candidates": context_only[:100],
        "contaminated_or_ambiguous_candidates": contaminated[:100],
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "raw_seed_equals_qualified_seed": False,
            "qualified_seed_equals_designation_identity": False,
            "qualified_seed_equals_current_validity": False,
            "qualified_seed_equals_site_inclusion": False,
            "no_qualified_seed_equals_legal_absence": False,
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
    print("SEMANTIC HARDENING")
    print("=" * 78)
    print(f"S230C RAW ELIGIBLE SEED COUNT: {s230c.get('reverse_lookup_eligible_seed_count')}")
    print(f"S230C RANKED CANDIDATE COUNT: {len(ranked)}")
    print(f"SEMANTIC HARDENED CANDIDATE COUNT: {len(hardened)}")
    print(f"QUALIFIED SEED COUNT: {len(qualified)}")
    print(f"CONTEXT ONLY COUNT: {len(context_only)}")
    print(f"CONTAMINATED / AMBIGUOUS COUNT: {len(contaminated)}")

    for i, r in enumerate(hardened[:25], 1):
        print(json.dumps({
            "rank": i,
            "document_no": r["canonical_document_no"],
            "semantic_class": r["semantic_class"],
            "reverse_lookup_allowed": r["reverse_lookup_allowed"],
            "unique_evidence_count": r["unique_evidence_count"],
            "strong_same_record_evidence_count": r["strong_same_record_evidence_count"],
            "positive_context_evidence_count": r["positive_context_evidence_count"],
            "contaminated_evidence_count": r["contaminated_evidence_count"],
            "independent_positive_source_count": r["independent_positive_source_count"],
            "independent_positive_stage_count": r["independent_positive_stage_count"],
        }, ensure_ascii=False))

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Raw seed == qualified seed: False")
    print("Qualified seed == designation identity verified: False")
    print("No qualified seed == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S230C loaded": IN_S230C.exists(),
        "no HTTP search": out["http_search_executed"] is False,
        "hardened count matches ranked input": len(hardened) == len(ranked),
        "partition count consistent": len(qualified) + len(context_only) + len(contaminated) == len(hardened),
        "only qualified seeds reverse lookup allowed": all(x["reverse_lookup_allowed"] is True for x in qualified) and all(x["reverse_lookup_allowed"] is False for x in context_only + contaminated),
        "raw seed not qualified seed by default": out["summary"]["raw_seed_equals_qualified_seed"] is False,
        "qualified seed not designation": out["summary"]["qualified_seed_equals_designation_identity"] is False,
        "qualified seed not validity": out["summary"]["qualified_seed_equals_current_validity"] is False,
        "qualified seed not site inclusion": out["summary"]["qualified_seed_equals_site_inclusion"] is False,
        "no qualified seed not legal absence": out["summary"]["no_qualified_seed_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "UQQ700_HISTORICAL_NOTICE_NUMBER_SEEDS_SEMANTICALLY_HARDENED_QUALIFIED",
            "UQQ700_HISTORICAL_NOTICE_NUMBER_SEEDS_SEMANTIC_HARDENING_NO_QUALIFIED_SEED",
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
        raise AssertionError("S230D validation failed")


if __name__ == "__main__":
    main()
