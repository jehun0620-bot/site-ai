# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"

S227B = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_archive_coverage_canonical_enumeration.json"
S227C = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_canonical_metadata_uqq700_discovery.json"
S227D = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_canonical_attachment_uqq700_content_scan.json"
S227E = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_uqq700_weak_hit_context_identity_review.json"
S227G = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_uqq700_hwp5_internal_text_recovery.json"
S227J = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_legacy_pdf_asis_physical_storage_replay.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_source_family_terminal_reconciliation.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE"
NEXT_SOURCE_FAMILY = "SEONGNAM_CITY_COUNCIL_OFFICIAL_RECORD"


def load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def as_int(d: dict, *keys: str, default: int = 0) -> int:
    for k in keys:
        if k in d and d.get(k) is not None:
            try:
                return int(d.get(k))
            except Exception:
                pass
    return default


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY PLANNING DOCUMENT SOURCE FAMILY TERMINAL RECONCILIATION - S227K")
    print("=" * 78)
    print("Purpose: reconcile S227B/C/D/E/G/J without additional download or search")
    print("Archived binary access unknown != legal absence")
    print("Planning document no-hit != designation absence")
    print("SITE FALSE inference: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 final resolution: UNKNOWN")

    b = load(S227B)
    c = load(S227C)
    d = load(S227D)
    e = load(S227E)
    g = load(S227G)
    j = load(S227J)

    canonical_posts = as_int(b, "canonical_post_count")
    canonical_attachments = as_int(b, "canonical_attachment_count")
    archive_inventory_qualified = bool(b.get("canonical_document_inventory_qualified") or b.get("canonical_inventory_qualified"))

    metadata_exact = as_int(c, "exact_target_metadata_hit_count", "exact_metadata_hit_count")
    metadata_variant = as_int(c, "variant_metadata_hit_count")
    metadata_weak = as_int(c, "weak_keyword_hit_count", "weak_metadata_hit_count")

    d_exact = as_int(d, "exact_content_hit_count")
    d_variant = as_int(d, "variant_content_hit_count")
    d_weak = as_int(d, "weak_content_hit_count")
    d_no_hit = as_int(d, "content_no_hit_count")
    d_unknown = as_int(d, "technical_unknown_count")
    d_non_text = as_int(d, "non_text_attachment_count")

    weak_review_complete = bool(e.get("review_complete"))
    weak_notice_candidates = as_int(e, "possible_notice_identity_context_count")
    weak_designation_candidates = as_int(e, "possible_designation_context_count")
    weak_review_unknown = as_int(e, "review_technical_unknown_count")

    hwp_targets = as_int(g, "target_hwp_count")
    hwp_recovered = as_int(g, "recovered_hwp_count")
    hwp_remaining = as_int(g, "remaining_hwp_technical_unknown_count")
    hwp_exact = as_int(g, "exact_content_hit_count")
    hwp_variant = as_int(g, "variant_content_hit_count")
    hwp_weak = as_int(g, "weak_content_hit_count")
    hwp_no_hit = as_int(g, "content_no_hit_count")

    legacy_targets = as_int(j, "target_count")
    physical_identity_count = as_int(j, "physical_storage_identity_count")
    legacy_recovered = as_int(j, "recovered_pdf_count")
    legacy_remaining = as_int(j, "remaining_technical_unknown_count")
    legacy_exact = as_int(j, "exact_content_hit_count")
    legacy_variant = as_int(j, "variant_content_hit_count")
    legacy_weak = as_int(j, "weak_content_hit_count")
    legacy_no_hit = as_int(j, "content_no_hit_count")

    verified_exact_or_variant = metadata_exact + metadata_variant + d_exact + d_variant + hwp_exact + hwp_variant + legacy_exact + legacy_variant
    verified_notice_identity_candidate_count = weak_notice_candidates
    verified_designation_context_candidate_count = weak_designation_candidates

    # The source is exhausted for current/public archive mechanics and content reachable through them,
    # but six metadata-identified legacy PDFs remain inaccessible over public HTTP.
    archive_mechanics_verified = archive_inventory_qualified and canonical_posts > 0 and canonical_attachments > 0
    weak_branch_resolved = weak_review_complete and weak_review_unknown == 0 and weak_notice_candidates == 0 and weak_designation_candidates == 0
    hwp_branch_resolved = hwp_targets > 0 and hwp_recovered == hwp_targets and hwp_remaining == 0
    archived_binary_access_unknown = legacy_targets > 0 and legacy_remaining > 0 and physical_identity_count == legacy_targets

    source_family_fully_closed = False
    source_family_operationally_exhausted_except_archived_binary_access = (
        archive_mechanics_verified
        and weak_branch_resolved
        and hwp_branch_resolved
        and archived_binary_access_unknown
    )

    operational_status = (
        "PARTIALLY_CLOSED_WITH_ARCHIVED_BINARY_ACCESS_TECHNICAL_UNKNOWN"
        if source_family_operationally_exhausted_except_archived_binary_access
        else "TECHNICAL_RECONCILIATION_INCOMPLETE"
    )

    if source_family_operationally_exhausted_except_archived_binary_access:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_SOURCE_FAMILY_PARTIALLY_CLOSED_ARCHIVED_BINARY_ACCESS_TECHNICAL_UNKNOWN"
        semantic = "CURRENT_PUBLIC_PLANNING_ARCHIVE_AND_REACHABLE_TEXT_CONTENT_WERE_EXHAUSTED_NON_NEGATIVELY_WHILE_SIX_METADATA_IDENTIFIED_LEGACY_PDFS_REMAIN_PUBLICLY_INACCESSIBLE"
        next_action = "MOVE_TO_SEONGNAM_CITY_COUNCIL_OFFICIAL_RECORD_WHILE_CARRYING_FORWARD_SIX_ARCHIVED_BINARY_ACCESS_TECHNICAL_UNKNOWNS_WITHOUT_LEGAL_ABSENCE_INFERENCE"
    else:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_SOURCE_FAMILY_TERMINAL_RECONCILIATION_TECHNICAL_UNKNOWN"
        semantic = "ONE_OR_MORE_REQUIRED_RECONCILIATION_PRECONDITIONS_WERE_NOT_VERIFIED"
        next_action = "HARDEN_ONLY_THE_FAILED_RECONCILIATION_PRECONDITIONS_WITHOUT_NEGATIVE_INFERENCE"

    unresolved_legacy = []
    for row in j.get("results", []) or []:
        if row.get("status") == "ASIS_PHYSICAL_BINARY_ACCESS_TECHNICAL_UNKNOWN":
            unresolved_legacy.append({
                "pstSn": row.get("pstSn"),
                "fileNo": row.get("fileNo"),
                "name": row.get("name"),
                "flpth": row.get("flpth"),
                "streFileNm": row.get("streFileNm"),
                "expected_size": row.get("expected_size"),
                "physical_url": row.get("physical_url"),
                "http": row.get("http"),
                "status": row.get("status"),
            })

    out = {
        "step": "STEP 17-21-C-16-8-T-156-S227K",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "input_files": {
            "S227B": str(S227B),
            "S227C": str(S227C),
            "S227D": str(S227D),
            "S227E": str(S227E),
            "S227G": str(S227G),
            "S227J": str(S227J),
        },
        "archive": {
            "canonical_post_count": canonical_posts,
            "canonical_attachment_count": canonical_attachments,
            "canonical_inventory_qualified": archive_inventory_qualified,
            "archive_mechanics_verified": archive_mechanics_verified,
        },
        "metadata_discovery": {
            "exact_hit_count": metadata_exact,
            "variant_hit_count": metadata_variant,
            "weak_hit_count": metadata_weak,
        },
        "initial_content_scan": {
            "exact_hit_count": d_exact,
            "variant_hit_count": d_variant,
            "weak_hit_count": d_weak,
            "content_no_hit_count": d_no_hit,
            "technical_unknown_count": d_unknown,
            "non_text_attachment_count": d_non_text,
        },
        "weak_hit_context_review": {
            "review_complete": weak_review_complete,
            "possible_notice_identity_context_count": weak_notice_candidates,
            "possible_designation_context_count": weak_designation_candidates,
            "review_technical_unknown_count": weak_review_unknown,
            "resolved_non_designation_context": weak_branch_resolved,
        },
        "hwp5_recovery": {
            "target_count": hwp_targets,
            "recovered_count": hwp_recovered,
            "remaining_technical_unknown_count": hwp_remaining,
            "exact_hit_count": hwp_exact,
            "variant_hit_count": hwp_variant,
            "weak_hit_count": hwp_weak,
            "content_no_hit_count": hwp_no_hit,
            "branch_resolved": hwp_branch_resolved,
        },
        "legacy_pdf_asis": {
            "target_count": legacy_targets,
            "physical_storage_identity_count": physical_identity_count,
            "recovered_pdf_count": legacy_recovered,
            "remaining_technical_unknown_count": legacy_remaining,
            "exact_hit_count": legacy_exact,
            "variant_hit_count": legacy_variant,
            "weak_hit_count": legacy_weak,
            "content_no_hit_count": legacy_no_hit,
            "archived_binary_access_unknown": archived_binary_access_unknown,
            "unresolved": unresolved_legacy,
        },
        "verified_exact_or_variant_uqq700_hit_count": verified_exact_or_variant,
        "verified_notice_identity_candidate_count": verified_notice_identity_candidate_count,
        "verified_designation_context_candidate_count": verified_designation_context_candidate_count,
        "source_family_fully_closed": source_family_fully_closed,
        "source_family_operationally_exhausted_except_archived_binary_access": source_family_operationally_exhausted_except_archived_binary_access,
        "operational_status": operational_status,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "next_source_family": NEXT_SOURCE_FAMILY,
            "search_content_finding": "NO_VERIFIED_UQQ700_DESIGNATION_NOTICE_IDENTITY_IN_REACHABLE_PLANNING_ARCHIVE_CONTENT",
            "unresolved_archived_binary_count": legacy_remaining,
            "planning_document_presence_equals_designation_notice": False,
            "planning_document_no_hit_equals_legal_absence": False,
            "source_family_partial_closure_equals_legal_absence": False,
            "archived_binary_access_unknown_equals_legal_absence": False,
            "archived_binary_access_unknown_equals_site_false": False,
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

    print("\nSOURCE FAMILY RECONCILIATION")
    print("-" * 78)
    print(f"CANONICAL POSTS: {canonical_posts}")
    print(f"CANONICAL ATTACHMENTS: {canonical_attachments}")
    print(f"ARCHIVE MECHANICS VERIFIED: {archive_mechanics_verified}")
    print(f"METADATA EXACT/VARIANT/WEAK: {metadata_exact}/{metadata_variant}/{metadata_weak}")
    print(f"INITIAL CONTENT EXACT/VARIANT/WEAK: {d_exact}/{d_variant}/{d_weak}")
    print(f"WEAK REVIEW COMPLETE: {weak_review_complete}")
    print(f"WEAK NOTICE IDENTITY CANDIDATES: {weak_notice_candidates}")
    print(f"WEAK DESIGNATION CONTEXT CANDIDATES: {weak_designation_candidates}")
    print(f"HWP RECOVERED: {hwp_recovered}/{hwp_targets}")
    print(f"LEGACY PDF ASIS IDENTITY: {physical_identity_count}/{legacy_targets}")
    print(f"LEGACY PDF PUBLICLY INACCESSIBLE: {legacy_remaining}")
    print(f"VERIFIED EXACT/VARIANT UQQ700 HIT COUNT: {verified_exact_or_variant}")
    print(f"SOURCE FAMILY FULLY CLOSED: {source_family_fully_closed}")
    print(f"OPERATIONALLY EXHAUSTED EXCEPT ARCHIVED BINARY ACCESS: {source_family_operationally_exhausted_except_archived_binary_access}")
    print(f"OPERATIONAL STATUS: {operational_status}")

    print("\nUNRESOLVED LEGACY PDF CARRY-FORWARD")
    print("-" * 78)
    for r in unresolved_legacy:
        print(json.dumps(r, ensure_ascii=False))

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print(f"Next source family: {NEXT_SOURCE_FAMILY}")
    print("Source family fully closed: False")
    print("Archived binary access unknown == legal absence: False")
    print("Planning document no-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "all reconciliation inputs exist": all(p.exists() for p in [S227B, S227C, S227D, S227E, S227G, S227J]),
        "archive mechanics verified": archive_mechanics_verified,
        "weak branch resolved": weak_branch_resolved,
        "HWP branch resolved": hwp_branch_resolved,
        "legacy archived binary access unknown retained": archived_binary_access_unknown,
        "legacy unresolved carry-forward count matches": len(unresolved_legacy) == legacy_remaining,
        "source family not fully closed": out["source_family_fully_closed"] is False,
        "partial operational exhaustion emitted": out["source_family_operationally_exhausted_except_archived_binary_access"] is True,
        "planning no-hit not legal absence": out["summary"]["planning_document_no_hit_equals_legal_absence"] is False,
        "partial closure not legal absence": out["summary"]["source_family_partial_closure_equals_legal_absence"] is False,
        "archive unknown not legal absence": out["summary"]["archived_binary_access_unknown_equals_legal_absence"] is False,
        "archive unknown not SITE FALSE": out["summary"]["archived_binary_access_unknown_equals_site_false"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "SEONGNAM_CITY_PLANNING_DOCUMENT_SOURCE_FAMILY_PARTIALLY_CLOSED_ARCHIVED_BINARY_ACCESS_TECHNICAL_UNKNOWN",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_SOURCE_FAMILY_TERMINAL_RECONCILIATION_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S227K validation failed")


if __name__ == "__main__":
    main()
