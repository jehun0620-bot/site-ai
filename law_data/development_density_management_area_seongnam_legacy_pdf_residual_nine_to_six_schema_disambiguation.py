from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TARGET_NAME = "개발밀도관리구역"
TARGET_CODE = "UQQ700"
TARGET_STATUS = "UNKNOWN"
EXPECTED_INPUT_COUNT = 9
EXPECTED_LEAF_COUNT = 6

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
INPUT_PATH = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_residual_six_target_prerequisite_recovery.json"
)
OUTPUT_PATH = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_residual_nine_to_six_schema_disambiguation.json"
)


def safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def normalize_url_set(item: dict[str, Any]) -> set[str]:
    return {
        str(url).strip()
        for url in safe_list(item.get("urls"))
        if isinstance(url, str) and url.strip()
    }


def path_depth(path: str) -> int:
    if not path:
        return -1
    return path.count(".") + path.count("[")


def is_ancestor_path(parent: str, child: str) -> bool:
    if not parent or not child or parent == child:
        return False
    return child.startswith(parent + ".") or child.startswith(parent + "[")


def provenance_rows(item: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw in safe_list(item.get("provenance")):
        if not isinstance(raw, dict):
            continue
        rows.append(
            {
                "source_type": str(raw.get("source_type") or ""),
                "source_path": str(raw.get("source_path") or ""),
                "object_path": str(raw.get("object_path") or ""),
            }
        )
    return rows


def identity_specificity(item: dict[str, Any]) -> int:
    identity = safe_dict(item.get("identity"))
    return sum(1 for value in identity.values() if value not in (None, "", [], {}))


def pair_relation(parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any] | None:
    parent_urls = normalize_url_set(parent)
    child_urls = normalize_url_set(child)
    if not parent_urls or not child_urls:
        return None
    if not child_urls.issubset(parent_urls):
        return None
    if parent_urls == child_urls:
        return None

    best: dict[str, Any] | None = None
    for p in provenance_rows(parent):
        for c in provenance_rows(child):
            if p["source_path"] != c["source_path"]:
                continue
            if not is_ancestor_path(p["object_path"], c["object_path"]):
                continue
            relation = {
                "same_source_path": p["source_path"],
                "parent_object_path": p["object_path"],
                "child_object_path": c["object_path"],
                "parent_url_count": len(parent_urls),
                "child_url_count": len(child_urls),
                "parent_depth": path_depth(p["object_path"]),
                "child_depth": path_depth(c["object_path"]),
            }
            if best is None or relation["child_depth"] > best["child_depth"]:
                best = relation
    return best


def same_identity(a: dict[str, Any], b: dict[str, Any]) -> bool:
    ai = safe_dict(a.get("identity"))
    bi = safe_dict(b.get("identity"))
    if not ai or not bi:
        return False
    common = set(ai).intersection(bi)
    if not common:
        return False
    meaningful = 0
    for key in common:
        av = ai.get(key)
        bv = bi.get(key)
        if av in (None, "") or bv in (None, ""):
            continue
        if str(av).strip() != str(bv).strip():
            return False
        meaningful += 1
    return meaningful > 0


def main() -> int:
    print("=" * 78)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SEONGNAM LEGACY PDF RESIDUAL NINE-TO-SIX SCHEMA DISAMBIGUATION")
    print("=" * 78)
    print(f"Target: {TARGET_NAME}")
    print(f"Standard code: {TARGET_CODE}")
    print(f"Input: {INPUT_PATH}")
    print("Network access: DISABLED")
    print("URL guessing: DISABLED")
    print()

    input_exists = INPUT_PATH.exists()
    input_error: str | None = None
    data: dict[str, Any] = {}
    if input_exists:
        try:
            loaded = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
            else:
                input_error = "input_root_not_object"
        except Exception as exc:
            input_error = repr(exc)
    else:
        input_error = "input_missing"

    candidates = [x for x in safe_list(data.get("candidates")) if isinstance(x, dict)]
    input_count = len(candidates)

    enriched: list[dict[str, Any]] = []
    for index, item in enumerate(candidates, 1):
        enriched.append(
            {
                "candidate_index": index,
                "identity": safe_dict(item.get("identity")),
                "urls": sorted(normalize_url_set(item)),
                "url_count": len(normalize_url_set(item)),
                "mechanics": safe_dict(item.get("mechanics")),
                "source_has_marker": bool(item.get("source_has_marker")),
                "provenance": provenance_rows(item),
                "max_object_path_depth": max(
                    [path_depth(x["object_path"]) for x in provenance_rows(item)] or [-1]
                ),
                "identity_specificity": identity_specificity(item),
            }
        )

    aggregate_indices: set[int] = set()
    aggregate_reasons: list[dict[str, Any]] = []
    parent_child_relations: list[dict[str, Any]] = []

    for parent in enriched:
        for child in enriched:
            if parent["candidate_index"] == child["candidate_index"]:
                continue
            relation = pair_relation(parent, child)
            if relation is None:
                continue
            relation.update(
                {
                    "parent_candidate_index": parent["candidate_index"],
                    "child_candidate_index": child["candidate_index"],
                    "same_identity": same_identity(parent, child),
                }
            )
            parent_child_relations.append(relation)
            aggregate_indices.add(parent["candidate_index"])
            aggregate_reasons.append(
                {
                    "candidate_index": parent["candidate_index"],
                    "reason": "ancestor_object_with_strict_url_superset",
                    "child_candidate_index": child["candidate_index"],
                    "source_path": relation["same_source_path"],
                    "parent_object_path": relation["parent_object_path"],
                    "child_object_path": relation["child_object_path"],
                }
            )

    leaf_candidates = [
        item for item in enriched if item["candidate_index"] not in aggregate_indices
    ]

    # Secondary diagnostics only: identical identity with differing URL sets is
    # reported, never auto-dropped, because it may represent distinct historical
    # records that happen to share a title or number.
    identity_overlap_pairs: list[dict[str, Any]] = []
    for i, left in enumerate(enriched):
        for right in enriched[i + 1 :]:
            if same_identity(left, right):
                identity_overlap_pairs.append(
                    {
                        "left_candidate_index": left["candidate_index"],
                        "right_candidate_index": right["candidate_index"],
                        "left_urls": left["urls"],
                        "right_urls": right["urls"],
                    }
                )

    exact_input_nine = input_count == EXPECTED_INPUT_COUNT
    exact_leaf_six = len(leaf_candidates) == EXPECTED_LEAF_COUNT
    structurally_disambiguated = (
        input_error is None
        and exact_input_nine
        and exact_leaf_six
        and len(aggregate_indices) == EXPECTED_INPUT_COUNT - EXPECTED_LEAF_COUNT
    )

    print("SCHEMA COMPARISON")
    print("-" * 78)
    print(f"Input candidate count: {input_count}")
    print(f"Aggregate/parent candidate count: {len(aggregate_indices)}")
    print(f"Leaf candidate count: {len(leaf_candidates)}")
    print(f"Exact nine input: {exact_input_nine}")
    print(f"Exact six leaf candidates: {exact_leaf_six}")
    print(f"Structurally disambiguated nine-to-six: {structurally_disambiguated}")
    print()

    for item in enriched:
        role = "AGGREGATE_PARENT" if item["candidate_index"] in aggregate_indices else "LEAF_CANDIDATE"
        print(f"CANDIDATE {item['candidate_index']} | {role}")
        print(f"  identity={json.dumps(item['identity'], ensure_ascii=False)}")
        print(f"  urls={json.dumps(item['urls'], ensure_ascii=False)}")
        print(f"  url_count={item['url_count']}")
        print(f"  identity_specificity={item['identity_specificity']}")
        for provenance in item["provenance"]:
            print(
                "  provenance="
                f"{provenance['source_type']} | "
                f"{provenance['source_path']} | "
                f"{provenance['object_path']}"
            )
        print()

    print("PARENT-CHILD RELATIONS")
    print("-" * 78)
    if parent_child_relations:
        for relation in parent_child_relations:
            print(
                f"P{relation['parent_candidate_index']} -> "
                f"C{relation['child_candidate_index']} | "
                f"urls {relation['parent_url_count']}->{relation['child_url_count']} | "
                f"{relation['parent_object_path']} -> {relation['child_object_path']}"
            )
    else:
        print("NONE")
    print()

    print("SELECTED LEAF SIX")
    print("-" * 78)
    if leaf_candidates:
        for index, item in enumerate(leaf_candidates, 1):
            print(
                f"LEAF {index}: source_candidate={item['candidate_index']} "
                f"identity={json.dumps(item['identity'], ensure_ascii=False)}"
            )
            print(f"  urls={json.dumps(item['urls'], ensure_ascii=False)}")
    else:
        print("NONE")
    print()

    if structurally_disambiguated:
        classification = "SEONGNAM_LEGACY_PDF_RESIDUAL_NINE_TO_SIX_STRUCTURALLY_DISAMBIGUATED"
        next_action = (
            "RUN_SEPARATELY_APPROVED_BINARY_ACCESS_DIAGNOSTIC_ONLY_FOR_THE_"
            "STRUCTURALLY_RECOVERED_SIX_LEAF_TARGETS"
        )
    else:
        classification = "SEONGNAM_LEGACY_PDF_RESIDUAL_NINE_TO_SIX_NOT_STRUCTURALLY_RESOLVED"
        next_action = (
            "INSPECT_PARENT_CHILD_RELATIONS_AND_PRODUCER_SCHEMA_WITHOUT_NETWORK_"
            "URL_GUESSING_OR_NEGATIVE_EVIDENCE"
        )

    safety = {
        "network_access_used": False,
        "uqq700_query_executed": False,
        "url_guessing_used": False,
        "ocr_used": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_promotion_allowed": False,
        "runtime_registration_allowed": False,
        "uqq700_resolution": TARGET_STATUS,
    }

    validation = {
        "target_name": TARGET_NAME == "개발밀도관리구역",
        "standard_code": TARGET_CODE == "UQQ700",
        "input_path_fixed": INPUT_PATH.name.endswith("six_target_prerequisite_recovery.json"),
        "network_disabled": safety["network_access_used"] is False,
        "uqq700_not_queried": safety["uqq700_query_executed"] is False,
        "url_guessing_disabled": safety["url_guessing_used"] is False,
        "ocr_disabled": safety["ocr_used"] is False,
        "negative_evidence_disabled": safety["negative_evidence_allowed"] is False,
        "legal_absence_inference_disabled": safety["legal_absence_inference_allowed"] is False,
        "site_promotion_disabled": safety["site_promotion_allowed"] is False,
        "runtime_registration_blocked": safety["runtime_registration_allowed"] is False,
        "uqq700_remains_unknown": safety["uqq700_resolution"] == "UNKNOWN",
    }
    all_pass = all(validation.values())

    payload = {
        "target": TARGET_NAME,
        "standard_code": TARGET_CODE,
        "resolution": TARGET_STATUS,
        "input_path": str(INPUT_PATH),
        "input_exists": input_exists,
        "input_error": input_error,
        "expected_input_count": EXPECTED_INPUT_COUNT,
        "expected_leaf_count": EXPECTED_LEAF_COUNT,
        "input_candidate_count": input_count,
        "exact_nine_input": exact_input_nine,
        "aggregate_candidate_indices": sorted(aggregate_indices),
        "aggregate_reasons": aggregate_reasons,
        "aggregate_candidate_count": len(aggregate_indices),
        "leaf_candidate_count": len(leaf_candidates),
        "exact_six_leaf_candidates": exact_leaf_six,
        "structurally_disambiguated": structurally_disambiguated,
        "candidates": enriched,
        "parent_child_relations": parent_child_relations,
        "identity_overlap_pairs": identity_overlap_pairs,
        "selected_leaf_candidates": leaf_candidates,
        "classification": classification,
        "next_action": next_action,
        "safety": safety,
        "validation": validation,
        "all_pass": all_pass,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print(f"UQQ700: {TARGET_STATUS}")
    print("Negative evidence allowed: False")
    print("Legal absence inference allowed: False")
    print("SITE promotion allowed: False")
    print("Runtime registration allowed: False")
    print("Network access used: False")
    print("URL guessing used: False")
    print(f"Output: {OUTPUT_PATH}")
    print(f"all_pass: {all_pass}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
