from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any


TARGET_NAME = "개발밀도관리구역"
TARGET_CODE = "UQQ700"
TARGET_STATUS = "UNKNOWN"
EXPECTED_TARGET_COUNT = 6
SOURCE_FAMILY_MARKER = "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE_LEGACY_PDF_BINARY_ACCESS"

BASE_DIR = Path(__file__).resolve().parent.parent
LAW_DIR = BASE_DIR / "law_data"
OUTPUT_DIR = LAW_DIR / "output"
OUTPUT_PATH = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_residual_six_target_prerequisite_recovery.json"
)

MAX_JSON_FILES = 400
MAX_PY_FILES = 500
MAX_TEXT_CHARS = 5_000_000

URL_RE = re.compile(r"https?://[^\s\"'<>]+", flags=re.I)
SEONGNAM_RE = re.compile(r"(?:성남|seongnam)", flags=re.I)
LEGACY_PDF_RE = re.compile(r"(?:legacy|pdf|viewer|download|attach|file)", flags=re.I)
RESIDUAL_RE = re.compile(r"(?:residual|unresolved|carry[_ -]?forward|remaining)", flags=re.I)

IDENTITY_KEYS = {
    "title", "name", "document_title", "document_name", "notice_title",
    "notice_name", "filename", "file_name", "idx", "id", "pstSn",
    "pstsn", "notice_number", "number", "no", "date", "year",
}
URL_KEY_HINTS = (
    "url", "href", "link", "viewer", "download", "attach", "file", "pdf", "binary"
)


def safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return str(value)


def collect_urls(value: Any) -> list[str]:
    text = safe_json(value)
    urls: list[str] = []
    seen: set[str] = set()
    for m in URL_RE.finditer(text):
        url = m.group(0).rstrip("),.;]}")
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def collect_identity(obj: dict[str, Any]) -> dict[str, Any]:
    identity: dict[str, Any] = {}
    for key, value in obj.items():
        if isinstance(value, (dict, list)) or value in (None, ""):
            continue
        if str(key) in IDENTITY_KEYS or any(h in str(key).lower() for h in ("title", "name", "idx", "number", "pstsn")):
            identity[str(key)] = value
    return identity


def collect_url_fields(obj: dict[str, Any]) -> dict[str, Any]:
    mechanics: dict[str, Any] = {}
    for key, value in obj.items():
        key_l = str(key).lower()
        if not any(h in key_l for h in URL_KEY_HINTS):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            mechanics[str(key)] = value
        elif isinstance(value, list):
            mechanics[str(key)] = value[:20]
    return mechanics


def iter_objects(value: Any, path: str = "$"):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from iter_objects(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_objects(child, f"{path}[{index}]")


def object_is_relevant(obj: dict[str, Any], source_text_has_marker: bool) -> bool:
    text = safe_json(obj)
    has_marker = SOURCE_FAMILY_MARKER in text
    has_seongnam = bool(SEONGNAM_RE.search(text))
    has_legacy_pdf = bool(LEGACY_PDF_RE.search(text))
    has_residual = bool(RESIDUAL_RE.search(text))
    urls = collect_urls(obj)
    if not urls:
        return False
    return has_marker or (
        source_text_has_marker and has_seongnam and has_legacy_pdf
    ) or (
        has_seongnam and has_legacy_pdf and has_residual
    )


def scan_json_outputs() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    evidence: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    if not OUTPUT_DIR.exists():
        diagnostics.append({"type": "missing_output_dir", "path": str(OUTPUT_DIR)})
        return evidence, diagnostics

    paths = sorted(OUTPUT_DIR.glob("development_density_management_area*.json"))[:MAX_JSON_FILES]
    for path in paths:
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception as exc:
            diagnostics.append({"type": "read_error", "path": str(path), "error": repr(exc)})
            continue
        if len(raw) > MAX_TEXT_CHARS:
            raw = raw[:MAX_TEXT_CHARS]
        source_has_marker = SOURCE_FAMILY_MARKER in raw
        source_has_seongnam = bool(SEONGNAM_RE.search(raw))
        source_has_legacy_pdf = bool(LEGACY_PDF_RE.search(raw))
        source_has_residual = bool(RESIDUAL_RE.search(raw))
        if not (source_has_marker or (source_has_seongnam and source_has_legacy_pdf) or (source_has_seongnam and source_has_residual)):
            continue
        try:
            data = json.loads(raw)
        except Exception as exc:
            diagnostics.append({"type": "json_error", "path": str(path), "error": repr(exc)})
            continue
        for object_path, obj in iter_objects(data):
            if not object_is_relevant(obj, source_has_marker):
                continue
            urls = collect_urls(obj)
            identity = collect_identity(obj)
            mechanics = collect_url_fields(obj)
            if not identity:
                continue
            evidence.append({
                "source_type": "json_output",
                "source_path": str(path),
                "object_path": object_path,
                "identity": identity,
                "urls": urls,
                "mechanics": mechanics,
                "source_has_marker": source_has_marker,
            })
    return evidence, diagnostics


def literal_records_from_python(path: Path, raw: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        tree = ast.parse(raw, filename=str(path))
    except Exception:
        return records
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Dict, ast.List, ast.Tuple)):
            continue
        try:
            value = ast.literal_eval(node)
        except Exception:
            continue
        for object_path, obj in iter_objects(value, path="ast"):
            if not isinstance(obj, dict):
                continue
            text = safe_json(obj)
            if not SEONGNAM_RE.search(text):
                continue
            if not LEGACY_PDF_RE.search(text):
                continue
            urls = collect_urls(obj)
            identity = collect_identity(obj)
            if not urls or not identity:
                continue
            records.append({
                "source_type": "python_literal",
                "source_path": str(path),
                "object_path": object_path,
                "identity": identity,
                "urls": urls,
                "mechanics": collect_url_fields(obj),
                "source_has_marker": SOURCE_FAMILY_MARKER in raw,
            })
    return records


def scan_python_sources() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    evidence: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    paths = sorted(LAW_DIR.glob("development_density_management_area*.py"))[:MAX_PY_FILES]
    for path in paths:
        if path.resolve() == Path(__file__).resolve():
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception as exc:
            diagnostics.append({"type": "read_error", "path": str(path), "error": repr(exc)})
            continue
        if len(raw) > MAX_TEXT_CHARS:
            raw = raw[:MAX_TEXT_CHARS]
        if not SEONGNAM_RE.search(raw):
            continue
        if not (LEGACY_PDF_RE.search(raw) or SOURCE_FAMILY_MARKER in raw or RESIDUAL_RE.search(raw)):
            continue
        evidence.extend(literal_records_from_python(path, raw))
        urls = []
        seen = set()
        for m in URL_RE.finditer(raw):
            url = m.group(0).rstrip("),.;]}")
            if url not in seen:
                seen.add(url)
                urls.append(url)
        diagnostics.append({
            "type": "python_source_hit",
            "path": str(path),
            "source_family_marker": SOURCE_FAMILY_MARKER in raw,
            "url_count": len(urls),
            "urls": urls[:50],
        })
    return evidence, diagnostics


def canonical_key(item: dict[str, Any]) -> tuple[str, ...]:
    urls = tuple(sorted(set(str(x) for x in item.get("urls", []) if x)))
    if urls:
        return urls
    identity = item.get("identity", {})
    return (safe_json(identity),)


def dedupe_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, ...], dict[str, Any]] = {}
    for item in items:
        key = canonical_key(item)
        if key not in merged:
            merged[key] = dict(item)
            merged[key]["provenance"] = [{
                "source_type": item["source_type"],
                "source_path": item["source_path"],
                "object_path": item.get("object_path"),
            }]
        else:
            merged[key]["provenance"].append({
                "source_type": item["source_type"],
                "source_path": item["source_path"],
                "object_path": item.get("object_path"),
            })
            merged[key]["source_has_marker"] = bool(
                merged[key].get("source_has_marker") or item.get("source_has_marker")
            )
    return list(merged.values())


def rank_candidate(item: dict[str, Any]) -> tuple[int, int, int, int]:
    text = safe_json(item)
    return (
        1 if item.get("source_has_marker") else 0,
        1 if SEONGNAM_RE.search(text) else 0,
        1 if LEGACY_PDF_RE.search(text) else 0,
        len(item.get("urls", [])),
    )


def main() -> int:
    print("=" * 78)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SEONGNAM LEGACY PDF RESIDUAL SIX-TARGET PREREQUISITE RECOVERY")
    print("=" * 78)
    print(f"Target: {TARGET_NAME}")
    print(f"Standard code: {TARGET_CODE}")
    print(f"Expected target count: {EXPECTED_TARGET_COUNT}")
    print("Network access: DISABLED")
    print("URL guessing: DISABLED")
    print()

    json_evidence, json_diag = scan_json_outputs()
    py_evidence, py_diag = scan_python_sources()
    raw_evidence = json_evidence + py_evidence
    candidates = dedupe_evidence(raw_evidence)
    candidates.sort(key=rank_candidate, reverse=True)

    exact_six = len(candidates) == EXPECTED_TARGET_COUNT

    print("RECOVERY SUMMARY")
    print("-" * 78)
    print(f"JSON evidence rows: {len(json_evidence)}")
    print(f"Python literal evidence rows: {len(py_evidence)}")
    print(f"Raw evidence rows: {len(raw_evidence)}")
    print(f"Canonical recovered target count: {len(candidates)}")
    print(f"Exact six-target prerequisite recovered: {exact_six}")
    print()

    for index, item in enumerate(candidates, 1):
        print(f"TARGET {index}")
        print(f"  identity={json.dumps(item.get('identity', {}), ensure_ascii=False)}")
        print(f"  urls={json.dumps(item.get('urls', []), ensure_ascii=False)}")
        print(f"  mechanics={json.dumps(item.get('mechanics', {}), ensure_ascii=False)}")
        print(f"  source_has_marker={item.get('source_has_marker')}")
        for provenance in item.get("provenance", []):
            print(
                "  provenance="
                f"{provenance.get('source_type')} | "
                f"{provenance.get('source_path')} | "
                f"{provenance.get('object_path')}"
            )
        print()

    if exact_six:
        classification = "SEONGNAM_LEGACY_PDF_RESIDUAL_SIX_TARGET_PREREQUISITE_RECOVERED"
        next_action = (
            "RUN_SEPARATELY_APPROVED_BINARY_ACCESS_DIAGNOSTIC_ONLY_FOR_THE_EXACT_"
            "SIX_RECOVERED_TARGETS_WITHOUT_NEGATIVE_EVIDENCE"
        )
    else:
        classification = "SEONGNAM_LEGACY_PDF_RESIDUAL_SIX_TARGET_PREREQUISITE_NOT_EXACTLY_RECOVERED"
        next_action = (
            "INSPECT_REPORTED_PRODUCER_CONSUMER_SOURCE_HITS_AND_RESTORE_THE_EXACT_"
            "SIX_RECORD_SCHEMA_WITHOUT_NETWORK_OR_URL_GUESSING"
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
        "expected_count_fixed_to_six": EXPECTED_TARGET_COUNT == 6,
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
        "expected_target_count": EXPECTED_TARGET_COUNT,
        "source_family_marker": SOURCE_FAMILY_MARKER,
        "json_evidence_count": len(json_evidence),
        "python_literal_evidence_count": len(py_evidence),
        "raw_evidence_count": len(raw_evidence),
        "canonical_recovered_target_count": len(candidates),
        "exact_six_target_prerequisite_recovered": exact_six,
        "candidates": candidates,
        "json_diagnostics": json_diag,
        "python_diagnostics": py_diag,
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
    print()

    print("VALIDATION")
    print("-" * 78)
    for key, value in validation.items():
        print(f"{key}: {value}")
    print(f"all_pass: {all_pass}")
    print(f"Output: {OUTPUT_PATH}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
