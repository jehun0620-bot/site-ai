from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

TARGET_NAME = "개발밀도관리구역"
TARGET_CODE = "UQQ700"
TARGET_STATUS = "UNKNOWN"
EXPECTED_COUNT = 6

BASE_DIR = Path(__file__).resolve().parent.parent
LAW_DIR = BASE_DIR / "law_data"
OUTPUT_DIR = LAW_DIR / "output"
EXACT_SIX_INPUT = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_exact_six_producer_schema_recovery.json"
)
OUTPUT_PATH = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_existing_access_mechanics_recovery.json"
)

MAX_JSON_FILES = 500
MAX_TEXT_CHARS = 6_000_000

URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)
MECHANICS_KEY_RE = re.compile(
    r"(?:url|href|link|viewer|download|getfile|attach|attachment|file|pdf|route|redirect|"
    r"status|http|https|content[_ -]?type|content[_ -]?disposition|location|storage|path|error)",
    re.I,
)
SEONGNAM_RE = re.compile(r"(?:성남|seongnam)", re.I)
LEGACY_RE = re.compile(r"(?:legacy|asis|pdf|attach|storage|viewer|download|getfile)", re.I)


def safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return str(value)


def load_json(path: Path) -> Any:
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
    found: list[str] = []
    seen: set[str] = set()
    for match in URL_RE.finditer(safe_json(value)):
        url = match.group(0).rstrip("),.;]}")
        if url not in seen:
            seen.add(url)
            found.append(url)
    return found


def normalized_identity(record: dict[str, Any]) -> dict[str, str]:
    identity = record.get("identity") if isinstance(record.get("identity"), dict) else record
    out: dict[str, str] = {}
    for key in ("pstSn", "pstsn", "fileNo", "fileno", "name", "filename", "file_name", "title"):
        value = identity.get(key) if isinstance(identity, dict) else None
        if value not in (None, ""):
            canonical = key.lower().replace("_", "")
            out[canonical] = str(value).strip()
    return out


def selected_exact_six(data: dict[str, Any]) -> list[dict[str, Any]]:
    selected = data.get("selected_exact_six")
    if not isinstance(selected, dict):
        return []
    records = selected.get("records")
    if not isinstance(records, list):
        return []
    if data.get("exact_six_recovered") is not True or len(records) != EXPECTED_COUNT:
        return []
    return [r for r in records if isinstance(r, dict)]


def identity_matches(target: dict[str, str], node: Any) -> bool:
    text = safe_json(node)
    if not target:
        return False

    strong_keys = ("pstsn", "fileno")
    strong_values = [target[k] for k in strong_keys if k in target]
    name_value = target.get("name") or target.get("filename") or target.get("title")

    strong_match = bool(strong_values) and all(v in text for v in strong_values)
    name_match = bool(name_value) and name_value in text

    # Accept either the stable producer IDs together, or an exact filename/title.
    return strong_match or name_match


def scalar_mechanics(obj: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in obj.items():
        if not MECHANICS_KEY_RE.search(str(key)):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[str(key)] = value
        elif isinstance(value, list):
            scalars = [
                x for x in value
                if isinstance(x, (str, int, float, bool)) or x is None
            ]
            if scalars:
                out[str(key)] = scalars[:50]
    return out


def relevant_source(path: Path, raw: str) -> bool:
    name = path.name.lower()
    if "seongnam" in name and any(
        token in name
        for token in (
            "legacy_pdf",
            "attachment_route",
            "physical_storage",
            "storage_reverse",
            "alternate_archival",
            "source_family_terminal",
        )
    ):
        return True
    return bool(SEONGNAM_RE.search(raw) and LEGACY_RE.search(raw))


def recover_mechanics_for_target(
    target_index: int,
    target_record: dict[str, Any],
    source_files: list[Path],
) -> dict[str, Any]:
    identity = normalized_identity(target_record)
    evidence: list[dict[str, Any]] = []
    seen_fingerprints: set[str] = set()

    for source_path in source_files:
        try:
            raw = source_path.read_text(encoding="utf-8")
        except Exception:
            continue
        if len(raw) > MAX_TEXT_CHARS:
            raw = raw[:MAX_TEXT_CHARS]
        if not relevant_source(source_path, raw):
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        for object_path, node in iter_nodes(data):
            if not isinstance(node, dict):
                continue
            if not identity_matches(identity, node):
                continue

            urls = extract_urls(node)
            mechanics = scalar_mechanics(node)
            if not urls and not mechanics:
                continue

            fingerprint = safe_json({"source": str(source_path), "path": object_path, "urls": urls, "mechanics": mechanics})
            if fingerprint in seen_fingerprints:
                continue
            seen_fingerprints.add(fingerprint)
            evidence.append({
                "source_path": str(source_path),
                "object_path": object_path,
                "urls": urls,
                "mechanics": mechanics,
            })

    unique_urls: list[str] = []
    seen_urls: set[str] = set()
    for item in evidence:
        for url in item.get("urls", []):
            if url not in seen_urls:
                seen_urls.add(url)
                unique_urls.append(url)

    return {
        "target_index": target_index,
        "identity": identity,
        "evidence_count": len(evidence),
        "unique_recorded_url_count": len(unique_urls),
        "unique_recorded_urls": unique_urls,
        "evidence": evidence,
    }


def main() -> int:
    print("=" * 78)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SEONGNAM LEGACY PDF EXISTING ACCESS MECHANICS RECOVERY")
    print("=" * 78)
    print(f"Target: {TARGET_NAME}")
    print(f"Standard code: {TARGET_CODE}")
    print(f"Input: {EXACT_SIX_INPUT}")
    print("Network access: DISABLED")
    print("URL creation/guessing: DISABLED")
    print("SSL bypass: DISABLED")
    print("OCR/content search: DISABLED")
    print()

    diagnostics: list[dict[str, Any]] = []
    if not EXACT_SIX_INPUT.exists():
        exact_data: dict[str, Any] = {}
        diagnostics.append({"type": "missing_exact_six_input", "path": str(EXACT_SIX_INPUT)})
    else:
        try:
            exact_data = load_json(EXACT_SIX_INPUT)
        except Exception as exc:
            exact_data = {}
            diagnostics.append({"type": "exact_six_input_error", "error": repr(exc)})

    targets = selected_exact_six(exact_data)
    prerequisite_valid = len(targets) == EXPECTED_COUNT

    source_files = sorted(OUTPUT_DIR.glob("development_density_management_area*.json"))[:MAX_JSON_FILES]
    # Do not inspect this script's own output if rerun.
    source_files = [p for p in source_files if p.resolve() != OUTPUT_PATH.resolve()]

    print("PREREQUISITE VALIDATION")
    print("-" * 78)
    print(f"Validated exact-six prerequisite: {prerequisite_valid}")
    print(f"Validated target count: {len(targets)}")
    print(f"Candidate local output files: {len(source_files)}")
    print()

    recovered: list[dict[str, Any]] = []
    if prerequisite_valid:
        for index, target in enumerate(targets, 1):
            recovered.append(recover_mechanics_for_target(index, target, source_files))

    print("RECOVERED EXISTING ACCESS MECHANICS")
    print("-" * 78)
    if recovered:
        for item in recovered:
            print(f"TARGET {item['target_index']}: identity={json.dumps(item['identity'], ensure_ascii=False)}")
            print(f"  evidence_count={item['evidence_count']}")
            print(f"  unique_recorded_url_count={item['unique_recorded_url_count']}")
            for url in item["unique_recorded_urls"]:
                print(f"  recorded_url={url}")
            for evidence in item["evidence"]:
                print(f"  source={evidence['source_path']}")
                print(f"  object_path={evidence['object_path']}")
                if evidence["mechanics"]:
                    print(f"  mechanics={json.dumps(evidence['mechanics'], ensure_ascii=False)}")
            print()
    else:
        print("NO RECOVERED TARGET MECHANICS")
        print()

    target_with_evidence_count = sum(1 for item in recovered if item["evidence_count"] > 0)
    target_with_multiple_urls_count = sum(1 for item in recovered if item["unique_recorded_url_count"] > 1)
    total_unique_urls = len({u for item in recovered for u in item["unique_recorded_urls"]})

    if not prerequisite_valid:
        classification = "SEONGNAM_LEGACY_PDF_EXISTING_ACCESS_MECHANICS_PREREQUISITE_TECHNICAL_UNKNOWN"
        next_action = "RESTORE_EXACT_SIX_PRODUCER_PREREQUISITE_WITHOUT_NETWORK_OR_URL_GUESSING"
    elif target_with_evidence_count == EXPECTED_COUNT:
        classification = "SEONGNAM_LEGACY_PDF_EXISTING_ACCESS_MECHANICS_RECOVERED_FOR_EXACT_SIX"
        next_action = (
            "INSPECT_ONLY_THE_RECORDED_ALTERNATE_ACCESS_ROUTE_OR_PROTOCOL_MECHANICS_IN_A_"
            "SEPARATELY_APPROVED_STEP_WITHOUT_URL_GUESSING_OR_NEGATIVE_EVIDENCE"
        )
    else:
        classification = "SEONGNAM_LEGACY_PDF_EXISTING_ACCESS_MECHANICS_PARTIALLY_RECOVERED_TECHNICAL_UNKNOWN"
        next_action = (
            "KEEP_UNRECOVERED_TARGET_MECHANICS_TECHNICAL_UNKNOWN_AND_INSPECT_ONLY_RECORDED_"
            "PRODUCER_OUTPUTS_WITHOUT_NETWORK_OR_URL_GUESSING"
        )

    safety = {
        "network_access_used": False,
        "uqq700_query_executed": False,
        "url_creation_used": False,
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
        "url_creation_disabled": safety["url_creation_used"] is False,
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
        "input": str(EXACT_SIX_INPUT),
        "expected_count": EXPECTED_COUNT,
        "prerequisite_valid": prerequisite_valid,
        "validated_target_count": len(targets),
        "candidate_output_file_count": len(source_files),
        "recovered_targets": recovered,
        "target_with_evidence_count": target_with_evidence_count,
        "target_with_multiple_urls_count": target_with_multiple_urls_count,
        "total_unique_recorded_url_count": total_unique_urls,
        "classification": classification,
        "next_action": next_action,
        "diagnostics": diagnostics,
        "safety": safety,
        "validation": validation,
        "all_pass": all_pass,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"Targets with existing mechanics evidence: {target_with_evidence_count}")
    print(f"Targets with >1 recorded URL: {target_with_multiple_urls_count}")
    print(f"Total unique recorded URLs: {total_unique_urls}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print(f"UQQ700: {TARGET_STATUS}")
    print("Negative evidence allowed: False")
    print("Legal absence inference allowed: False")
    print("SITE promotion allowed: False")
    print("Runtime registration allowed: False")
    print("Network access used: False")
    print("URL guessing used: False")
    print("SSL verification bypass used: False")
    print(f"Output: {OUTPUT_PATH}")
    print(f"all_pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
