# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
PRIOR_OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_archive_coverage_canonical_enumeration.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_canonical_metadata_uqq700_discovery.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE"

EXACT_TERMS = ["개발밀도관리구역"]
VARIANT_TERMS = ["개발밀도 관리구역"]
WEAK_TERMS = ["개발밀도", "밀도관리구역"]


def norm(s: object) -> str:
    return " ".join(str(s or "").split())


def classify_text(text: str) -> tuple[str, list[str]]:
    hits = [t for t in EXACT_TERMS if t in text]
    if hits:
        return "EXACT_TARGET_METADATA_HIT", hits
    hits = [t for t in VARIANT_TERMS if t in text]
    if hits:
        return "VARIANT_METADATA_HIT", hits
    hits = [t for t in WEAK_TERMS if t in text]
    if hits:
        return "WEAK_KEYWORD_HIT", hits
    return "NO_METADATA_HIT", []


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY PLANNING DOCUMENT CANONICAL METADATA UQQ700 DISCOVERY - S227C")
    print("=" * 78)
    print("Purpose: scan qualified canonical post/attachment metadata only")
    print("Binary download: NOT EXECUTED")
    print("Document content parsing: NOT EXECUTED")
    print("Metadata hit != designation notice/current validity/site inclusion")
    print("Metadata no-hit != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    if not PRIOR_OUT.exists():
        raise FileNotFoundError(PRIOR_OUT)
    prior = json.loads(PRIOR_OUT.read_text(encoding="utf-8"))

    prior_inventory_qualified = bool(prior.get("canonical_inventory_qualified"))
    posts = list(prior.get("canonical_posts") or [])
    attachments = list(prior.get("canonical_attachments") or [])

    post_results = []
    attachment_results = []

    for p in posts:
        title = norm(p.get("title"))
        cls, hits = classify_text(title)
        post_results.append({
            "pstSn": p.get("pstSn"),
            "title": title,
            "detail_url": p.get("detail_url"),
            "classification": cls,
            "matched_terms": hits,
        })

    for a in attachments:
        fields = {
            "orginlFileNm": norm(a.get("orginlFileNm")),
            "fileExtsn": norm(a.get("fileExtsn")),
            "pstSn": norm(a.get("pstSn")),
            "fileNo": norm(a.get("fileNo")),
        }
        text = " | ".join(fields.values())
        cls, hits = classify_text(text)
        attachment_results.append({
            "pstSn": a.get("pstSn"),
            "fileNo": a.get("fileNo"),
            "orginlFileNm": a.get("orginlFileNm"),
            "fileExtsn": a.get("fileExtsn"),
            "download_url": a.get("download_url"),
            "classification": cls,
            "matched_terms": hits,
        })

    exact_hits = [x for x in post_results + attachment_results if x["classification"] == "EXACT_TARGET_METADATA_HIT"]
    variant_hits = [x for x in post_results + attachment_results if x["classification"] == "VARIANT_METADATA_HIT"]
    weak_hits = [x for x in post_results + attachment_results if x["classification"] == "WEAK_KEYWORD_HIT"]

    if exact_hits:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_CANONICAL_METADATA_EXACT_UQQ700_HIT"
        semantic = "EXACT_UQQ700_TERM_OBSERVED_IN_QUALIFIED_CANONICAL_METADATA_ONLY"
        next_action = "RUN_BINARY_CONTENT_VERIFICATION_ONLY_FOR_EXACT_METADATA_HIT_DOCUMENTS_AND_TRACE_ANY_NOTICE_IDENTITY_TO_OFFICIAL_NOTICE"
    elif variant_hits:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_CANONICAL_METADATA_VARIANT_UQQ700_HIT"
        semantic = "UQQ700_SPACING_VARIANT_OBSERVED_IN_QUALIFIED_CANONICAL_METADATA_ONLY"
        next_action = "RUN_BINARY_CONTENT_VERIFICATION_ONLY_FOR_VARIANT_METADATA_HIT_DOCUMENTS_NON_NEGATIVELY"
    elif weak_hits:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_CANONICAL_METADATA_WEAK_KEYWORD_HIT_ONLY"
        semantic = "WEAK_UQQ700_RELATED_METADATA_TERM_OBSERVED_WITHOUT_EXACT_OR_VARIANT_IDENTITY"
        next_action = "RUN_BOUNDED_CONTENT_SCAN_PRIORITIZING_WEAK_METADATA_HITS_THEN_REMAINDER_WITHOUT_NEGATIVE_INFERENCE"
    else:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_CANONICAL_METADATA_NO_UQQ700_HIT"
        semantic = "NO_EXACT_VARIANT_OR_WEAK_UQQ700_TERM_OBSERVED_IN_QUALIFIED_CANONICAL_METADATA"
        next_action = "RUN_BOUNDED_CONTENT_SCAN_OVER_QUALIFIED_CANONICAL_ATTACHMENTS_WITHOUT_TREATING_METADATA_NO_HIT_AS_LEGAL_ABSENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-149-S227C",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "prior_input_exists": True,
        "prior_canonical_inventory_qualified": prior_inventory_qualified,
        "binary_download_executed": False,
        "document_content_parsing_executed": False,
        "canonical_post_count": len(posts),
        "canonical_attachment_count": len(attachments),
        "post_results": post_results,
        "attachment_results": attachment_results,
        "exact_hit_count": len(exact_hits),
        "variant_hit_count": len(variant_hits),
        "weak_hit_count": len(weak_hits),
        "exact_hits": exact_hits,
        "variant_hits": variant_hits,
        "weak_hits": weak_hits,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "metadata_hit_equals_designation_notice": False,
            "metadata_hit_equals_current_validity": False,
            "metadata_hit_equals_site_inclusion": False,
            "metadata_no_hit_equals_legal_absence": False,
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

    print("\nMETADATA DISCOVERY")
    print("-" * 78)
    print(f"CANONICAL POST COUNT: {len(posts)}")
    print(f"CANONICAL ATTACHMENT COUNT: {len(attachments)}")
    print(f"EXACT TARGET METADATA HIT COUNT: {len(exact_hits)}")
    print(f"VARIANT METADATA HIT COUNT: {len(variant_hits)}")
    print(f"WEAK KEYWORD HIT COUNT: {len(weak_hits)}")

    for label, rows in (("EXACT", exact_hits), ("VARIANT", variant_hits), ("WEAK", weak_hits)):
        print(f"\n{label} HITS")
        for r in rows[:50]:
            print(json.dumps(r, ensure_ascii=False))

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"PRIOR CANONICAL INVENTORY QUALIFIED: {prior_inventory_qualified}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Binary download executed: False")
    print("Document content parsing executed: False")
    print("Metadata no-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S227B inventory qualified": prior_inventory_qualified,
        "binary download not executed": out["binary_download_executed"] is False,
        "content parsing not executed": out["document_content_parsing_executed"] is False,
        "metadata hit not designation": out["summary"]["metadata_hit_equals_designation_notice"] is False,
        "metadata hit not validity": out["summary"]["metadata_hit_equals_current_validity"] is False,
        "metadata hit not site inclusion": out["summary"]["metadata_hit_equals_site_inclusion"] is False,
        "metadata no-hit not legal absence": out["summary"]["metadata_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
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
        raise AssertionError("S227C validation failed")


if __name__ == "__main__":
    main()
