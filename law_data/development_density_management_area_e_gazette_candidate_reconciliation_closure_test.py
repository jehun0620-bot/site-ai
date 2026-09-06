# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
S221R = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_designation_query_family_replay.json"
S221Q = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_pdf_term_context_classification.json"
S221I = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_subject_desc_target_query_replay.json"
S221H = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_target_query_replay.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_candidate_reconciliation_closure.json"

TARGET = "개발밀도관리구역"
EXPECTED_QUERY_FAMILY = [
    "개발밀도관리구역 성남",
    "개발밀도관리구역 성남시",
    "개발밀도관리구역 지정",
    "개발밀도관리구역 결정",
    "개발밀도관리구역 지형도면",
]


def main():
    print("=" * 78)
    print("E-GAZETTE CANDIDATE RECONCILIATION / BOUNDED CLOSURE - S221S")
    print("=" * 78)
    print("Purpose: reconcile S221R candidate with the already-qualified S221Q document")
    print("Operational source-family closure != legal absence")
    print("Search no-hit != SITE FALSE")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s221r = json.loads(S221R.read_text(encoding="utf-8"))
    s221q = json.loads(S221Q.read_text(encoding="utf-8"))
    s221i = json.loads(S221I.read_text(encoding="utf-8"))
    s221h = json.loads(S221H.read_text(encoding="utf-8"))

    gate_r = (
        s221r.get("classification") == "DESIGNATION_QUERY_FAMILY_CANDIDATES_DISCOVERED"
        and (s221r.get("summary") or {}).get("technical_unknown_count") == 0
        and (s221r.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
        and s221r.get("official_designation_identity_verified") is False
    )
    gate_q = (
        s221q.get("classification") == "NATIONAL_REGULATORY_POLICY_LIST_CONTEXT"
        and (s221q.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
        and s221q.get("official_designation_identity_verified") is False
    )
    gate_i = (
        s221i.get("classification") == "TARGET_HIT"
        and (s221i.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    gate_h = (
        s221h.get("classification") == "TARGET_NO_HIT"
        and (s221h.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    if not all([gate_r, gate_q, gate_i, gate_h]):
        raise AssertionError("S221S prerequisite gate not satisfied")

    ranked = s221r.get("ranked_candidates") or []
    if len(ranked) != 1:
        raise AssertionError(f"Expected exactly 1 canonical S221R candidate, got {len(ranked)}")

    r_candidate = ranked[0]
    r_item = r_candidate.get("item") or {}
    r_toc = str(r_item.get("stored_toc_seq") or "")
    r_subject = str(r_item.get("stored_field_subject") or "")

    q_candidate = s221q.get("candidate") or {}
    q_toc = str(q_candidate.get("toc_id") or "")
    q_subject = str(q_candidate.get("subject") or "")

    toc_identity_match = bool(r_toc and q_toc and r_toc == q_toc)
    subject_identity_match = bool(r_subject and q_subject and r_subject == q_subject)
    same_document_identity = toc_identity_match and subject_identity_match

    matched_queries = r_candidate.get("matched_queries") or []
    designation_query_hits_are_existing_doc = (
        same_document_identity
        and "개발밀도관리구역 지정" in matched_queries
        and "개발밀도관리구역 결정" in matched_queries
    )

    query_results = s221r.get("query_results") or []
    query_result_map = {str(q.get("term")): q for q in query_results if isinstance(q, dict)}
    query_family_exact = s221r.get("query_terms") == EXPECTED_QUERY_FAMILY
    bounded_query_coverage = all(term in query_result_map for term in EXPECTED_QUERY_FAMILY)
    all_bounded_queries_resolved = all(
        (query_result_map.get(term) or {}).get("classification") in {"QUERY_HIT", "QUERY_NO_HIT"}
        for term in EXPECTED_QUERY_FAMILY
    )

    exact_subject_no_hit = s221h.get("classification") == "TARGET_NO_HIT"
    exact_subject_desc_hit = s221i.get("classification") == "TARGET_HIT"

    q_summary = s221q.get("summary") or {}
    inherited_context = s221q.get("classification")
    designation_candidate_excluded = q_summary.get("designation_candidate_excluded") is True
    historical_context_verified = q_summary.get("historical_legal_context_verified") is True

    no_new_document_identity = len(ranked) == 1 and same_document_identity
    bounded_search_exhausted = all([
        query_family_exact,
        bounded_query_coverage,
        all_bounded_queries_resolved,
        exact_subject_no_hit,
        exact_subject_desc_hit,
        no_new_document_identity,
        designation_candidate_excluded,
        historical_context_verified,
    ])

    if bounded_search_exhausted:
        classification = "E_GAZETTE_BOUNDED_DESIGNATION_SEARCH_EXHAUSTED_NO_QUALIFIED_DESIGNATION_DOCUMENT"
        semantic = "E_GAZETTE_BOUNDED_SEARCH_OPERATIONALLY_CLOSED_WITHOUT_LEGAL_ABSENCE_INFERENCE"
        next_action = "PROCEED_TO_GYEONGGI_OFFICIAL_RECORD_SOURCE_FAMILY_WITH_UQQ700_UNKNOWN"
    else:
        classification = "E_GAZETTE_BOUNDED_DESIGNATION_SEARCH_RECONCILIATION_UNRESOLVED"
        semantic = "E_GAZETTE_BOUNDED_SEARCH_RECONCILIATION_UNRESOLVED"
        next_action = "RESOLVE_E_GAZETTE_RECONCILIATION_BEFORE_SOURCE_FAMILY_TRANSITION"

    coverage = {
        "exact_subject": {
            "status": "NO_HIT" if exact_subject_no_hit else "UNRESOLVED",
            "source_step": "S221H",
        },
        "exact_subject_desc": {
            "status": "HIT_EXISTING_NON_DESIGNATION_CONTEXT" if exact_subject_desc_hit and same_document_identity else "UNRESOLVED",
            "source_step": "S221I/S221Q",
        },
        "target_plus_seongnam": {
            "status": (query_result_map.get("개발밀도관리구역 성남") or {}).get("classification"),
            "source_step": "S221R",
        },
        "target_plus_seongnam_city": {
            "status": (query_result_map.get("개발밀도관리구역 성남시") or {}).get("classification"),
            "source_step": "S221R",
        },
        "target_plus_designation": {
            "status": "HIT_EXISTING_S221Q_DOCUMENT" if "개발밀도관리구역 지정" in matched_queries and same_document_identity else (query_result_map.get("개발밀도관리구역 지정") or {}).get("classification"),
            "source_step": "S221R/S221Q",
        },
        "target_plus_decision": {
            "status": "HIT_EXISTING_S221Q_DOCUMENT" if "개발밀도관리구역 결정" in matched_queries and same_document_identity else (query_result_map.get("개발밀도관리구역 결정") or {}).get("classification"),
            "source_step": "S221R/S221Q",
        },
        "target_plus_topographic_map": {
            "status": (query_result_map.get("개발밀도관리구역 지형도면") or {}).get("classification"),
            "source_step": "S221R",
        },
    }

    out = {
        "step": "STEP 17-21-C-16-8-T-134-S221S",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "reconciliation": {
            "s221r_toc_id": r_toc,
            "s221q_toc_id": q_toc,
            "toc_identity_match": toc_identity_match,
            "s221r_subject": r_subject,
            "s221q_subject": q_subject,
            "subject_identity_match": subject_identity_match,
            "same_document_identity": same_document_identity,
            "matched_queries": matched_queries,
            "designation_query_hits_are_existing_document": designation_query_hits_are_existing_doc,
            "inherited_context_classification": inherited_context,
            "designation_candidate_excluded": designation_candidate_excluded,
            "historical_legal_context_verified": historical_context_verified,
            "no_new_document_identity": no_new_document_identity,
        },
        "coverage": coverage,
        "bounded_search_exhausted": bounded_search_exhausted,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "operational_source_family_closure": bounded_search_exhausted,
            "operational_closure_equals_legal_absence": False,
            "search_no_hit_equals_site_false": False,
            "search_hit_equals_designation_identity": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "legal_absence": False,
            "site_false_inference_allowed": False,
            "official_designation_identity_verified": False,
            "current_validity_verified": False,
            "site_spatial_inclusion_verified": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "official_designation_identity_verified": False,
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("S221R TOC ID:", r_toc)
    print("S221Q TOC ID:", q_toc)
    print("TOC IDENTITY MATCH:", toc_identity_match)
    print("SUBJECT IDENTITY MATCH:", subject_identity_match)
    print("SAME DOCUMENT IDENTITY:", same_document_identity)
    print("MATCHED QUERIES:", matched_queries)
    print("DESIGNATION QUERY HITS ARE EXISTING DOCUMENT:", designation_query_hits_are_existing_doc)
    print("INHERITED CONTEXT:", inherited_context)
    print("DESIGNATION CANDIDATE EXCLUDED:", designation_candidate_excluded)
    print("HISTORICAL LEGAL CONTEXT VERIFIED:", historical_context_verified)
    print("NO NEW DOCUMENT IDENTITY:", no_new_document_identity)
    print("BOUNDED SEARCH EXHAUSTED:", bounded_search_exhausted)
    print("CLASSIFICATION:", classification)

    print("\nCOVERAGE")
    for key, value in coverage.items():
        print(f"{key}: {json.dumps(value, ensure_ascii=False)}")

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("Operational source-family closure:", bounded_search_exhausted)
    print("Legal absence inference allowed: False")
    print("SITE FALSE inference allowed: False")
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S221R candidate gate": gate_r,
        "S221Q context gate": gate_q,
        "S221I subjectDesc gate": gate_i,
        "S221H exact subject gate": gate_h,
        "single canonical candidate": len(ranked) == 1,
        "toc identity reconciled": toc_identity_match,
        "subject identity reconciled": subject_identity_match,
        "same document identity": same_document_identity,
        "designation/decision hits are existing document": designation_query_hits_are_existing_doc,
        "query family exact": query_family_exact,
        "bounded query coverage complete": bounded_query_coverage,
        "all bounded queries resolved": all_bounded_queries_resolved,
        "S221Q context inherited": inherited_context == "NATIONAL_REGULATORY_POLICY_LIST_CONTEXT",
        "designation candidate excluded": designation_candidate_excluded,
        "historical context retained": historical_context_verified,
        "no new document identity": no_new_document_identity,
        "bounded search operationally exhausted": bounded_search_exhausted,
        "operational closure not legal absence": out["summary"]["operational_closure_equals_legal_absence"] is False,
        "search no-hit not SITE FALSE": out["summary"]["search_no_hit_equals_site_false"] is False,
        "search hit not designation identity": out["summary"]["search_hit_equals_designation_identity"] is False,
        "negative evidence disabled": not out["summary"]["negative_evidence_allowed"],
        "legal absence inference disabled": not out["summary"]["legal_absence_inference_allowed"],
        "legal absence false": out["summary"]["legal_absence"] is False,
        "SITE FALSE inference disabled": not out["summary"]["site_false_inference_allowed"],
        "designation identity not promoted": out["official_designation_identity_verified"] is False,
        "current validity not promoted": out["current_validity_verified"] is False,
        "site inclusion not promoted": out["site_spatial_inclusion_verified"] is False,
        "SITE promotion blocked": not out["site_positive_allowed"] and not out["site_negative_allowed"],
        "runtime registration blocked": not out["runtime_registration_allowed"],
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nVALIDATION")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("all_pass:", all(checks.values()))
    if not all(checks.values()):
        raise AssertionError("S221S E-GAZETTE reconciliation/closure failed")


if __name__ == "__main__":
    main()
