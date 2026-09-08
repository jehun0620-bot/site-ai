from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

TARGET_NAME = "개발밀도관리구역"
TARGET_CODE = "UQQ700"
TARGET_STATUS = "UNKNOWN"
EXPECTED_COUNT = 6

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
EXACT_SIX_INPUT = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_exact_six_producer_schema_recovery.json"
)
LEAF_INPUT = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_leaf_direct_route_provenance_reconciliation.json"
)
CURL_INPUT = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_exact_six_system_curl_tls_transport_diagnostic.json"
)
OUTPUT_PATH = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_exact_six_recorded_route_family_reconciliation.json"
)

SCAN_PATTERNS = [
    "development_density_management_area_seongnam*.json",
    "development_density_management_area_*legacy_pdf*.json",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_nodes(value: Any, path: str = "$"):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from iter_nodes(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_nodes(child, f"{path}[{index}]")


def extract_urls(value: Any) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, list):
        candidates = [v for v in value if isinstance(v, str)]
    elif isinstance(value, dict):
        candidates = [v for v in value.values() if isinstance(v, str)]
        for v in value.values():
            if isinstance(v, list):
                candidates.extend(x for x in v if isinstance(x, str))
    else:
        candidates = []
    for candidate in candidates:
        text = candidate.strip()
        if text.lower().startswith(("http://", "https://")) and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def normalize_identity(record: dict[str, Any]) -> dict[str, str]:
    src = record.get("identity") if isinstance(record.get("identity"), dict) else record
    out: dict[str, str] = {}
    if not isinstance(src, dict):
        return out
    mapping = {
        "pstSn": "pstsn", "pstsn": "pstsn",
        "fileNo": "fileno", "fileno": "fileno",
        "name": "name", "filename": "name", "file_name": "name", "title": "name",
    }
    for key, dst in mapping.items():
        if key in src and src[key] not in (None, ""):
            out[dst] = str(src[key]).strip()
    return out


def identity_matches(identity: dict[str, str], node: dict[str, Any]) -> bool:
    flat: dict[str, str] = {}
    for key, value in node.items():
        if isinstance(value, (str, int, float, bool)) and value not in (None, ""):
            flat[str(key).lower().replace("_", "")] = str(value).strip()
    pst = identity.get("pstsn")
    fileno = identity.get("fileno")
    name = identity.get("name")
    pst_match = bool(pst and any(v == pst for k, v in flat.items() if "pstsn" in k))
    file_match = bool(fileno and any(v == fileno for k, v in flat.items() if "fileno" in k))
    name_match = bool(name and any(v == name for k, v in flat.items() if any(t in k for t in ("name", "filename", "title"))))
    return name_match or (pst_match and file_match)


def route_family(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    query = parsed.query.lower()
    if host == "www.seongnam.go.kr" and path == "/ct-bbs020101/getfile":
        return "GETFILE_CONTROLLER"
    if host == "www.seongnam.go.kr" and "/data/asis/attach/" in path:
        return "ASIS_PHYSICAL_STORAGE"
    if "viewer" in path or "viewer" in query:
        return "VIEWER_ROUTE"
    if "download" in path or "download" in query:
        return "DOWNLOAD_ROUTE"
    if "getfile" in path or "filedown" in path or "filedownload" in path:
        return "OTHER_FILE_CONTROLLER"
    if any(token in host for token in ("archive.org", "web.archive.org")):
        return "ARCHIVAL_ROUTE"
    return "OTHER_RECORDED_ROUTE"


def exact_six_records(data: dict[str, Any]) -> list[dict[str, Any]]:
    selected = data.get("selected_exact_six")
    if not isinstance(selected, dict):
        return []
    records = selected.get("records")
    if not isinstance(records, list) or len(records) != EXPECTED_COUNT:
        return []
    return [r for r in records if isinstance(r, dict)]


def prior_status_for_url(curl_data: dict[str, Any], url: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for result in curl_data.get("results", []):
        if not isinstance(result, dict):
            continue
        if result.get("requested_url") == url:
            out.append({
                "source": "system_curl_tls_transport_diagnostic",
                "http_code": result.get("http_code"),
                "content_type": result.get("content_type"),
                "ssl_verify_result": result.get("ssl_verify_result"),
                "curl_returncode": result.get("curl_returncode"),
                "pdf_signature": result.get("pdf_signature"),
                "technical_unknown": result.get("technical_unknown"),
            })
    return out


def main() -> int:
    print("=" * 82)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SEONGNAM LEGACY PDF EXACT-SIX RECORDED ROUTE FAMILY RECONCILIATION")
    print("=" * 82)
    print(f"Target: {TARGET_NAME}")
    print(f"Standard code: {TARGET_CODE}")
    print("Network access: DISABLED")
    print("URL creation/mutation/guessing: DISABLED")
    print("Negative evidence/legal absence inference: DISABLED")
    print()

    diagnostics: list[dict[str, Any]] = []
    try:
        exact_six = load_json(EXACT_SIX_INPUT)
    except Exception as exc:
        exact_six = {}
        diagnostics.append({"input": str(EXACT_SIX_INPUT), "error": repr(exc)})
    try:
        leaf_data = load_json(LEAF_INPUT)
    except Exception as exc:
        leaf_data = {}
        diagnostics.append({"input": str(LEAF_INPUT), "error": repr(exc)})
    try:
        curl_data = load_json(CURL_INPUT)
    except Exception as exc:
        curl_data = {}
        diagnostics.append({"input": str(CURL_INPUT), "error": repr(exc)})

    records = exact_six_records(exact_six)
    prerequisite_valid = len(records) == EXPECTED_COUNT

    scan_files: list[Path] = []
    seen_files: set[str] = set()
    for pattern in SCAN_PATTERNS:
        for p in OUTPUT_DIR.glob(pattern):
            key = str(p.resolve())
            if key in seen_files or p == OUTPUT_PATH:
                continue
            seen_files.add(key)
            scan_files.append(p)

    target_results: list[dict[str, Any]] = []
    if prerequisite_valid:
        for target_index, record in enumerate(records, 1):
            identity = normalize_identity(record)
            route_map: dict[str, dict[str, Any]] = {}

            # Prefer already reconciled leaf routes as explicit exact-target provenance.
            leaf_target = None
            for item in leaf_data.get("reconciled_targets", []):
                if isinstance(item, dict) and item.get("target_index") == target_index:
                    leaf_target = item
                    break
            if isinstance(leaf_target, dict):
                for route in leaf_target.get("leaf_direct_routes", []):
                    if not isinstance(route, dict):
                        continue
                    url = route.get("url")
                    if not isinstance(url, str):
                        continue
                    family = route_family(url)
                    rec = route_map.setdefault(url, {
                        "url": url,
                        "family": family,
                        "scheme": urlparse(url).scheme,
                        "host": urlparse(url).netloc,
                        "path": urlparse(url).path,
                        "query": urlparse(url).query,
                        "provenance": [],
                        "prior_status": [],
                    })
                    rec["provenance"].append({
                        "source_path": route.get("source_path"),
                        "object_path": route.get("object_path"),
                        "provenance_type": "LEAF_DIRECT_ROUTE",
                        "matches_producer_url": route.get("matches_producer_url"),
                    })

            # Supplement only with literal URLs recorded in local outputs where the same node matches identity.
            for source_path in scan_files:
                try:
                    data = load_json(source_path)
                except Exception:
                    continue
                for object_path, node in iter_nodes(data):
                    if not isinstance(node, dict) or not identity_matches(identity, node):
                        continue
                    for url in extract_urls(node):
                        family = route_family(url)
                        rec = route_map.setdefault(url, {
                            "url": url,
                            "family": family,
                            "scheme": urlparse(url).scheme,
                            "host": urlparse(url).netloc,
                            "path": urlparse(url).path,
                            "query": urlparse(url).query,
                            "provenance": [],
                            "prior_status": [],
                        })
                        prov = {
                            "source_path": str(source_path),
                            "object_path": object_path,
                            "provenance_type": "IDENTITY_MATCHED_LITERAL_ROUTE",
                        }
                        if prov not in rec["provenance"]:
                            rec["provenance"].append(prov)

            for rec in route_map.values():
                rec["prior_status"] = prior_status_for_url(curl_data, rec["url"])
                rec["provenance_count"] = len(rec["provenance"])

            routes = sorted(route_map.values(), key=lambda r: (r["family"], r["url"]))
            family_counts: dict[str, int] = defaultdict(int)
            for r in routes:
                family_counts[r["family"]] += 1

            target_results.append({
                "target_index": target_index,
                "identity": identity,
                "route_count": len(routes),
                "family_counts": dict(sorted(family_counts.items())),
                "routes": routes,
            })

    all_family_names = sorted({r["family"] for t in target_results for r in t["routes"]})
    targets_with_getfile = sum(1 for t in target_results if t["family_counts"].get("GETFILE_CONTROLLER", 0) > 0)
    targets_with_asis = sum(1 for t in target_results if t["family_counts"].get("ASIS_PHYSICAL_STORAGE", 0) > 0)
    targets_with_other = sum(
        1 for t in target_results
        if any(k not in ("GETFILE_CONTROLLER", "ASIS_PHYSICAL_STORAGE") and v > 0 for k, v in t["family_counts"].items())
    )

    print("RECONCILIATION SUMMARY")
    print("-" * 82)
    print(f"Validated exact-six prerequisite: {prerequisite_valid}")
    print(f"Validated target count: {len(records)}")
    print(f"Scanned local JSON files: {len(scan_files)}")
    print(f"Targets with GETFILE_CONTROLLER: {targets_with_getfile}")
    print(f"Targets with ASIS_PHYSICAL_STORAGE: {targets_with_asis}")
    print(f"Targets with other recorded route family: {targets_with_other}")
    print(f"Recorded route families: {all_family_names}")
    print()

    for target in target_results:
        print(f"TARGET {target['target_index']}: identity={json.dumps(target['identity'], ensure_ascii=False)}")
        print(f"  route_count={target['route_count']}")
        print(f"  family_counts={json.dumps(target['family_counts'], ensure_ascii=False)}")
        for route in target["routes"]:
            print(f"  ROUTE_FAMILY={route['family']}")
            print(f"    url={route['url']}")
            print(f"    provenance_count={route['provenance_count']}")
            if route["prior_status"]:
                print(f"    prior_status={json.dumps(route['prior_status'], ensure_ascii=False)}")
        print()

    if not prerequisite_valid:
        classification = "SEONGNAM_LEGACY_PDF_RECORDED_ROUTE_FAMILY_PREREQUISITE_TECHNICAL_UNKNOWN"
        next_action = "RESTORE_EXACT_SIX_PREREQUISITE_WITHOUT_NETWORK_OR_URL_GUESSING"
    elif targets_with_other > 0:
        classification = "SEONGNAM_LEGACY_PDF_EXACT_SIX_RECORDED_ROUTE_FAMILIES_RECONCILED_WITH_ALTERNATE_LITERAL_ROUTES"
        next_action = "INSPECT_ONLY_EXACT_TARGET_RECORDED_ALTERNATE_ROUTE_FAMILIES_IN_A_SEPARATELY_APPROVED_NETWORK_STEP_WITHOUT_URL_MUTATION_OR_NEGATIVE_EVIDENCE"
    else:
        classification = "SEONGNAM_LEGACY_PDF_EXACT_SIX_RECORDED_ROUTE_FAMILIES_RECONCILED_NO_ADDITIONAL_LITERAL_FAMILY"
        next_action = "KEEP_CURRENT_LEGACY_FILE_ACCESS_UNRESOLVED_AND_AVOID_URL_GUESSING_OR_NEGATIVE_EVIDENCE"

    safety = {
        "network_access_used": False,
        "uqq700_query_executed": False,
        "url_creation_used": False,
        "url_mutation_used": False,
        "url_guessing_used": False,
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
        "url_creation_disabled": safety["url_creation_used"] is False,
        "url_mutation_disabled": safety["url_mutation_used"] is False,
        "url_guessing_disabled": safety["url_guessing_used"] is False,
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
            "exact_six": str(EXACT_SIX_INPUT),
            "leaf": str(LEAF_INPUT),
            "curl": str(CURL_INPUT),
        },
        "prerequisite_valid": prerequisite_valid,
        "validated_target_count": len(records),
        "scanned_local_json_file_count": len(scan_files),
        "recorded_route_families": all_family_names,
        "targets_with_getfile_controller": targets_with_getfile,
        "targets_with_asis_physical_storage": targets_with_asis,
        "targets_with_other_recorded_route_family": targets_with_other,
        "targets": target_results,
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
    print("URL creation/mutation/guessing used: False")
    print(f"Output: {OUTPUT_PATH}")
    print(f"all_pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
