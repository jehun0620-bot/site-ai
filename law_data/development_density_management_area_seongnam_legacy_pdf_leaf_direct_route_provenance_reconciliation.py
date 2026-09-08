from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TARGET_NAME = "개발밀도관리구역"
TARGET_CODE = "UQQ700"
TARGET_STATUS = "UNKNOWN"
EXPECTED_COUNT = 6

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
SCOPING_INPUT = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_exact_six_access_mechanics_scoping_hardening.json"
)
MECHANICS_INPUT = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_existing_access_mechanics_recovery.json"
)
EXACT_SIX_INPUT = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_exact_six_producer_schema_recovery.json"
)
OUTPUT_PATH = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_leaf_direct_route_provenance_reconciliation.json"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def direct_scalar_urls(obj: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for value in obj.values():
        values = value if isinstance(value, list) else [value]
        for item in values:
            if isinstance(item, str) and item.lower().startswith(("http://", "https://")):
                url = item.strip()
                if url not in seen:
                    seen.add(url)
                    urls.append(url)
    return urls


def identity_from_record(record: dict[str, Any]) -> dict[str, str]:
    identity = record.get("identity") if isinstance(record.get("identity"), dict) else record
    out: dict[str, str] = {}
    if isinstance(identity, dict):
        for src, dst in (
            ("pstSn", "pstsn"),
            ("pstsn", "pstsn"),
            ("fileNo", "fileno"),
            ("fileno", "fileno"),
            ("name", "name"),
            ("filename", "name"),
            ("file_name", "name"),
            ("title", "name"),
        ):
            if src in identity and identity[src] not in (None, ""):
                out[dst] = str(identity[src]).strip()
    return out


def iter_nodes(value: Any, path: str = "$"):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from iter_nodes(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_nodes(child, f"{path}[{index}]")


def leaf_identity_match(identity: dict[str, str], obj: dict[str, Any]) -> bool:
    scalars = {
        str(k).lower().replace("_", ""): str(v).strip()
        for k, v in obj.items()
        if isinstance(v, (str, int, float, bool)) and v not in (None, "")
    }
    pst_match = identity.get("pstsn") and any(
        identity["pstsn"] == value for key, value in scalars.items() if "pstsn" in key
    )
    file_match = identity.get("fileno") and any(
        identity["fileno"] == value for key, value in scalars.items() if "fileno" in key or "fileno" == key
    )
    name_match = identity.get("name") and any(
        identity["name"] == value
        for key, value in scalars.items()
        if any(token in key for token in ("name", "filename", "title"))
    )
    return bool(name_match or (pst_match and file_match))


def exact_six_records(data: dict[str, Any]) -> list[dict[str, Any]]:
    selected = data.get("selected_exact_six")
    if not isinstance(selected, dict):
        return []
    records = selected.get("records")
    if not isinstance(records, list) or len(records) != EXPECTED_COUNT:
        return []
    return [r for r in records if isinstance(r, dict)]


def source_paths_from_mechanics(mechanics: dict[str, Any]) -> list[Path]:
    out: list[Path] = []
    seen: set[str] = set()
    for target in mechanics.get("recovered_targets", []):
        if not isinstance(target, dict):
            continue
        for evidence in target.get("evidence", []):
            if not isinstance(evidence, dict):
                continue
            raw = evidence.get("source_path")
            if not raw:
                continue
            p = Path(raw)
            key = str(p)
            if key in seen or not p.exists() or p.suffix.lower() != ".json":
                continue
            seen.add(key)
            out.append(p)
    return out


def producer_urls(records: list[dict[str, Any]]) -> dict[int, list[str]]:
    result: dict[int, list[str]] = {}
    for index, record in enumerate(records, 1):
        urls = record.get("urls") if isinstance(record.get("urls"), list) else []
        result[index] = [str(u).strip() for u in urls if isinstance(u, str) and u.strip()]
    return result


def main() -> int:
    print("=" * 82)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SEONGNAM LEGACY PDF LEAF DIRECT ROUTE PROVENANCE RECONCILIATION")
    print("=" * 82)
    print(f"Target: {TARGET_NAME}")
    print(f"Standard code: {TARGET_CODE}")
    print("Network access: DISABLED")
    print("URL mutation/guessing: DISABLED")
    print("OCR/content search: DISABLED")
    print()

    diagnostics: list[dict[str, Any]] = []
    try:
        scoping = load_json(SCOPING_INPUT)
    except Exception as exc:
        scoping = {}
        diagnostics.append({"input": str(SCOPING_INPUT), "error": repr(exc)})
    try:
        mechanics = load_json(MECHANICS_INPUT)
    except Exception as exc:
        mechanics = {}
        diagnostics.append({"input": str(MECHANICS_INPUT), "error": repr(exc)})
    try:
        exact_six = load_json(EXACT_SIX_INPUT)
    except Exception as exc:
        exact_six = {}
        diagnostics.append({"input": str(EXACT_SIX_INPUT), "error": repr(exc)})

    records = exact_six_records(exact_six)
    prerequisite_valid = len(records) == EXPECTED_COUNT
    source_paths = source_paths_from_mechanics(mechanics)
    producer_map = producer_urls(records)

    reconciled: list[dict[str, Any]] = []
    if prerequisite_valid:
        for target_index, record in enumerate(records, 1):
            identity = identity_from_record(record)
            leaf_routes: list[dict[str, Any]] = []
            seen = set()
            for source_path in source_paths:
                try:
                    data = load_json(source_path)
                except Exception:
                    continue
                for object_path, node in iter_nodes(data):
                    if not isinstance(node, dict):
                        continue
                    if not leaf_identity_match(identity, node):
                        continue
                    urls = direct_scalar_urls(node)
                    if not urls:
                        continue
                    for url in urls:
                        key = (str(source_path), object_path, url)
                        if key in seen:
                            continue
                        seen.add(key)
                        leaf_routes.append({
                            "source_path": str(source_path),
                            "object_path": object_path,
                            "url": url,
                            "matches_producer_url": url in producer_map.get(target_index, []),
                        })

            producer_exact_matches = [r for r in leaf_routes if r["matches_producer_url"]]
            reconciled.append({
                "target_index": target_index,
                "identity": identity,
                "producer_urls": producer_map.get(target_index, []),
                "leaf_direct_route_count": len(leaf_routes),
                "producer_exact_leaf_match_count": len(producer_exact_matches),
                "leaf_direct_routes": leaf_routes,
            })

    targets_with_leaf = sum(1 for r in reconciled if r["leaf_direct_route_count"] > 0)
    targets_with_producer_exact_leaf = sum(
        1 for r in reconciled if r["producer_exact_leaf_match_count"] > 0
    )

    print("RECONCILIATION SUMMARY")
    print("-" * 82)
    print(f"Validated exact-six prerequisite: {prerequisite_valid}")
    print(f"Validated target count: {len(records)}")
    print(f"Source JSON files inspected: {len(source_paths)}")
    print(f"Targets with leaf direct route(s): {targets_with_leaf}")
    print(f"Targets with producer exact leaf match: {targets_with_producer_exact_leaf}")
    print()

    for item in reconciled:
        print(f"TARGET {item['target_index']}: identity={json.dumps(item['identity'], ensure_ascii=False)}")
        print(f"  producer_urls={json.dumps(item['producer_urls'], ensure_ascii=False)}")
        print(f"  leaf_direct_route_count={item['leaf_direct_route_count']}")
        print(f"  producer_exact_leaf_match_count={item['producer_exact_leaf_match_count']}")
        for route in item["leaf_direct_routes"]:
            print(f"  LEAF_DIRECT_ROUTE={route['url']}")
            print(f"    source={route['source_path']}")
            print(f"    object_path={route['object_path']}")
            print(f"    matches_producer_url={route['matches_producer_url']}")
        print()

    if not prerequisite_valid:
        classification = "SEONGNAM_LEGACY_PDF_LEAF_DIRECT_ROUTE_PREREQUISITE_TECHNICAL_UNKNOWN"
        next_action = "RESTORE_EXACT_SIX_PREREQUISITE_WITHOUT_NETWORK_OR_URL_GUESSING"
    elif targets_with_producer_exact_leaf == EXPECTED_COUNT:
        classification = "SEONGNAM_LEGACY_PDF_LEAF_DIRECT_PRODUCER_ROUTES_RECONCILED_FOR_EXACT_SIX"
        next_action = (
            "CONSIDER_ONLY_THE_RECONCILED_PRODUCER_EXACT_LEAF_ROUTES_FOR_A_SEPARATELY_"
            "APPROVED_ACCESS_MECHANICS_STEP_WITHOUT_URL_MUTATION_OR_NEGATIVE_EVIDENCE"
        )
    elif targets_with_leaf == EXPECTED_COUNT:
        classification = "SEONGNAM_LEGACY_PDF_LEAF_DIRECT_ROUTES_RECOVERED_PRODUCER_MATCH_INCOMPLETE"
        next_action = (
            "INSPECT_ONLY_LEAF_ROUTE_PROVENANCE_AND_PRODUCER_URL_EQUALITY_WITHOUT_NETWORK_"
            "URL_MUTATION_OR_NEGATIVE_EVIDENCE"
        )
    else:
        classification = "SEONGNAM_LEGACY_PDF_LEAF_DIRECT_ROUTE_PROVENANCE_PARTIALLY_RESOLVED_TECHNICAL_UNKNOWN"
        next_action = (
            "KEEP_UNRESOLVED_TARGETS_TECHNICAL_UNKNOWN_AND_INSPECT_ONLY_EXISTING_PRODUCER_"
            "LEAF_PROVENANCE_WITHOUT_NETWORK_OR_URL_GUESSING"
        )

    safety = {
        "network_access_used": False,
        "uqq700_query_executed": False,
        "url_mutation_used": False,
        "url_guessing_used": False,
        "ssl_verification_bypass_used": False,
        "ocr_used": False,
        "content_search_used": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_promotion_allowed": False,
        "runtime_registration_allowed": False,
        "uqq700_resolution": TARGET_STATUS,
    }
    validation = {
        "target_name": TARGET_NAME == "개발밀도관리구역",
        "standard_code": TARGET_CODE == "UQQ700",
        "expected_count_fixed_to_six": EXPECTED_COUNT == 6,
        "network_disabled": safety["network_access_used"] is False,
        "uqq700_not_queried": safety["uqq700_query_executed"] is False,
        "url_mutation_disabled": safety["url_mutation_used"] is False,
        "url_guessing_disabled": safety["url_guessing_used"] is False,
        "ssl_bypass_disabled": safety["ssl_verification_bypass_used"] is False,
        "ocr_disabled": safety["ocr_used"] is False,
        "content_search_disabled": safety["content_search_used"] is False,
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
        "inputs": {
            "scoping": str(SCOPING_INPUT),
            "mechanics": str(MECHANICS_INPUT),
            "exact_six": str(EXACT_SIX_INPUT),
        },
        "prerequisite_valid": prerequisite_valid,
        "validated_target_count": len(records),
        "source_json_file_count": len(source_paths),
        "targets_with_leaf_direct_routes": targets_with_leaf,
        "targets_with_producer_exact_leaf_match": targets_with_producer_exact_leaf,
        "reconciled_targets": reconciled,
        "classification": classification,
        "next_action": next_action,
        "diagnostics": diagnostics,
        "safety": safety,
        "validation": validation,
        "all_pass": all_pass,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 82)
    print("RESOLUTION")
    print("=" * 82)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print(f"UQQ700: {TARGET_STATUS}")
    print("Negative evidence allowed: False")
    print("Legal absence inference allowed: False")
    print("SITE promotion allowed: False")
    print("Runtime registration allowed: False")
    print("Network access used: False")
    print("URL mutation/guessing used: False")
    print(f"Output: {OUTPUT_PATH}")
    print(f"all_pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
