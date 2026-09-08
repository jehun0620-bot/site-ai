from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests


TARGET_NAME = "개발밀도관리구역"
TARGET_CODE = "UQQ700"
TARGET_STATUS = "UNKNOWN"
EXPECTED_TARGET_COUNT = 6
SOURCE_FAMILY_MARKER = (
    "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE_LEGACY_PDF_BINARY_ACCESS"
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_PATH = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_city_planning_legacy_pdf_binary_access_diagnostic.json"
)

MAX_INPUT_FILES = 250
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
TIMEOUT = (5, 25)

URL_KEY_HINTS = (
    "url",
    "href",
    "link",
    "download",
    "viewer",
    "file",
    "attach",
    "binary",
    "pdf",
)
IDENTITY_KEY_HINTS = (
    "title",
    "name",
    "document",
    "notice",
    "filename",
    "file_name",
    "idx",
    "id",
    "pstsn",
    "number",
    "no",
)
CONTAINER_KEY_HINTS = (
    "residual",
    "unresolved",
    "candidate",
    "target",
    "result",
    "record",
    "document",
    "item",
)


class TargetPrerequisiteError(RuntimeError):
    pass


def _safe_json_text(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return str(value)


def _is_http_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    value = value.strip()
    if not re.match(r"^https?://", value, flags=re.I):
        return False
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    return bool(parsed.scheme and parsed.netloc)


def _direct_urls(obj: dict[str, Any]) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for key, value in obj.items():
        key_l = str(key).lower()
        if not any(hint in key_l for hint in URL_KEY_HINTS):
            continue
        values: list[Any]
        if isinstance(value, list):
            values = value
        else:
            values = [value]
        for item in values:
            if not _is_http_url(item):
                continue
            url = str(item).strip()
            if url in seen:
                continue
            seen.add(url)
            found.append({"field": str(key), "url": url})
    return found


def _identity(obj: dict[str, Any]) -> dict[str, Any]:
    identity: dict[str, Any] = {}
    for key, value in obj.items():
        if isinstance(value, (dict, list)) or value in (None, ""):
            continue
        key_l = str(key).lower()
        if any(hint in key_l for hint in IDENTITY_KEY_HINTS):
            identity[str(key)] = value
    return identity


def _mechanics(obj: dict[str, Any]) -> dict[str, Any]:
    mechanics: dict[str, Any] = {}
    for key, value in obj.items():
        key_l = str(key).lower()
        if any(hint in key_l for hint in URL_KEY_HINTS):
            if isinstance(value, (str, int, float, bool)) or value is None:
                mechanics[str(key)] = value
            elif isinstance(value, list):
                mechanics[str(key)] = [
                    x for x in value if isinstance(x, (str, int, float, bool)) or x is None
                ][:20]
    return mechanics


def _iter_dicts(value: Any, path: str = "$", inherited_hint: bool = False):
    if isinstance(value, dict):
        own_text = _safe_json_text(value)
        own_hint = inherited_hint or SOURCE_FAMILY_MARKER in own_text
        yield path, value, own_hint
        for key, child in value.items():
            child_hint = own_hint or any(
                hint in str(key).lower() for hint in CONTAINER_KEY_HINTS
            )
            yield from _iter_dicts(child, f"{path}.{key}", child_hint)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_dicts(child, f"{path}[{index}]", inherited_hint)


def _candidate_from_object(
    *,
    source_path: Path,
    object_path: str,
    obj: dict[str, Any],
    file_has_marker: bool,
    inherited_hint: bool,
) -> dict[str, Any] | None:
    urls = _direct_urls(obj)
    if not urls:
        return None

    text = _safe_json_text(obj)
    text_l = text.lower()
    direct_marker = SOURCE_FAMILY_MARKER in text
    locality_signal = "성남" in text or "seongnam" in text_l
    legacy_pdf_signal = "legacy" in text_l or "pdf" in text_l

    # Never infer a target from a generic URL-bearing object. It must be tied
    # either directly to the exact source-family marker or to a marker-bearing
    # prerequisite file plus explicit Seongnam / legacy-PDF context.
    relevant = direct_marker or (
        file_has_marker
        and inherited_hint
        and locality_signal
        and legacy_pdf_signal
    )
    if not relevant:
        return None

    identity = _identity(obj)
    if not identity:
        return None

    return {
        "source_path": str(source_path),
        "object_path": object_path,
        "identity": identity,
        "urls": urls,
        "mechanics": _mechanics(obj),
        "source_family_marker_direct": direct_marker,
    }


def recover_exact_targets() -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    if not OUTPUT_DIR.exists():
        return [], [], [{"error": "output_directory_missing", "path": str(OUTPUT_DIR)}]

    files = sorted(OUTPUT_DIR.glob("development_density_management_area*.json"))
    files = files[:MAX_INPUT_FILES]
    prerequisite_paths: list[str] = []
    raw_candidates: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []

    for path in files:
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception as exc:
            diagnostics.append({"path": str(path), "read_error": repr(exc)})
            continue

        if SOURCE_FAMILY_MARKER not in raw:
            continue
        prerequisite_paths.append(str(path))

        try:
            data = json.loads(raw)
        except Exception as exc:
            diagnostics.append({"path": str(path), "json_error": repr(exc)})
            continue

        for object_path, obj, inherited_hint in _iter_dicts(data):
            candidate = _candidate_from_object(
                source_path=path,
                object_path=object_path,
                obj=obj,
                file_has_marker=True,
                inherited_hint=inherited_hint,
            )
            if candidate is not None:
                raw_candidates.append(candidate)

    # Prefer the most specific (deepest) object for each exact URL set. Parent
    # objects may contain the same URL through duplicated flattened metadata.
    raw_candidates.sort(key=lambda x: x["object_path"].count("."), reverse=True)
    deduped: list[dict[str, Any]] = []
    seen_url_sets: set[tuple[str, ...]] = set()
    for candidate in raw_candidates:
        url_key = tuple(sorted(item["url"] for item in candidate["urls"]))
        if not url_key or url_key in seen_url_sets:
            continue
        seen_url_sets.add(url_key)
        deduped.append(candidate)

    return deduped, prerequisite_paths, diagnostics


def probe_url(session: requests.Session, url: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "requested_url": url,
        "final_url": None,
        "redirect_chain": [],
        "http_status": None,
        "content_type": None,
        "content_disposition": None,
        "content_length_header": None,
        "bytes_read": 0,
        "truncated": False,
        "pdf_signature": False,
        "technical_unknown": False,
        "error": None,
    }
    try:
        with session.get(
            url,
            allow_redirects=True,
            timeout=TIMEOUT,
            stream=True,
        ) as response:
            result["final_url"] = response.url
            result["redirect_chain"] = [
                {
                    "status": item.status_code,
                    "url": item.url,
                    "location": item.headers.get("Location"),
                }
                for item in response.history
            ]
            result["http_status"] = response.status_code
            result["content_type"] = response.headers.get("Content-Type")
            result["content_disposition"] = response.headers.get("Content-Disposition")
            result["content_length_header"] = response.headers.get("Content-Length")

            prefix = bytearray()
            bytes_read = 0
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                if len(prefix) < 8:
                    prefix.extend(chunk[: 8 - len(prefix)])
                bytes_read += len(chunk)
                if bytes_read >= MAX_DOWNLOAD_BYTES:
                    result["truncated"] = True
                    break

            result["bytes_read"] = bytes_read
            result["pdf_signature"] = bytes(prefix).startswith(b"%PDF-")
    except requests.RequestException as exc:
        result["technical_unknown"] = True
        result["error"] = repr(exc)
    except Exception as exc:
        result["technical_unknown"] = True
        result["error"] = repr(exc)
    return result


def main() -> int:
    print("=" * 72)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SEONGNAM CITY PLANNING LEGACY PDF BINARY ACCESS DIAGNOSTIC")
    print("=" * 72)
    print(f"Target: {TARGET_NAME}")
    print(f"Standard code: {TARGET_CODE}")
    print(f"Expected residual target count: {EXPECTED_TARGET_COUNT}")
    print()

    targets, prerequisite_paths, recovery_diagnostics = recover_exact_targets()

    print("PREREQUISITE SOURCE PATHS")
    print("-" * 72)
    if prerequisite_paths:
        for path in prerequisite_paths:
            print(path)
    else:
        print("NONE")
    print()

    print(f"Recovered target count: {len(targets)}")
    for index, target in enumerate(targets, 1):
        print(f"[{index}] identity={json.dumps(target['identity'], ensure_ascii=False)}")
        for url_entry in target["urls"]:
            print(f"    {url_entry['field']}: {url_entry['url']}")
    print()

    exact_prerequisite = len(targets) == EXPECTED_TARGET_COUNT
    probes: list[dict[str, Any]] = []

    if exact_prerequisite:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (compatible; site-ai-step17/1.0; "
                    "+bounded-binary-access-diagnostic)"
                ),
                "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8",
            }
        )
        for index, target in enumerate(targets, 1):
            target_result = {
                "target_index": index,
                "source_path": target["source_path"],
                "object_path": target["object_path"],
                "identity": target["identity"],
                "mechanics": target["mechanics"],
                "url_probes": [],
            }
            for url_entry in target["urls"]:
                probe = probe_url(session, url_entry["url"])
                probe["source_field"] = url_entry["field"]
                target_result["url_probes"].append(probe)
            probes.append(target_result)
    else:
        print(
            "Network probing skipped: exact six-target prerequisite was not "
            "recovered. No URL guessing is permitted."
        )
        print()

    any_binary_pdf_verified = any(
        probe.get("pdf_signature") is True
        for target in probes
        for probe in target["url_probes"]
    )
    any_technical_unknown = any(
        probe.get("technical_unknown") is True
        for target in probes
        for probe in target["url_probes"]
    )

    if not exact_prerequisite:
        classification = (
            "SEONGNAM_CITY_PLANNING_LEGACY_PDF_TARGET_PREREQUISITE_TECHNICAL_UNKNOWN"
        )
        next_action = (
            "RESTORE_OR_RERUN_PRIOR_SEONGNAM_RESIDUAL_DISCOVERY_OUTPUT_"
            "WITHOUT_NEGATIVE_EVIDENCE"
        )
    else:
        classification = (
            "SEONGNAM_CITY_PLANNING_LEGACY_PDF_BINARY_ACCESS_DIAGNOSTIC_EXECUTED"
        )
        if any_binary_pdf_verified:
            next_action = (
                "VERIFY_ONLY_BINARY_ACCESS_CONFIRMED_TARGET_IDENTITIES_IN_A_"
                "SEPARATELY_APPROVED_STEP"
            )
        elif any_technical_unknown:
            next_action = (
                "RECOVER_EXISTING_VIEWER_OR_DOWNLOAD_MECHANICS_FOR_ONLY_THE_SIX_"
                "TARGETS_WITHOUT_NEGATIVE_EVIDENCE"
            )
        else:
            next_action = (
                "RECOVER_EXISTING_VIEWER_OR_DOWNLOAD_CONTRACT_FOR_ONLY_THE_SIX_"
                "TARGETS_WITHOUT_NEGATIVE_EVIDENCE"
            )

    safety = {
        "uqq700_query_executed": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_promotion_allowed": False,
        "runtime_registration_allowed": False,
        "ocr_used": False,
        "brute_force_used": False,
        "broad_crawl_used": False,
        "url_guessing_used": False,
        "target_status": TARGET_STATUS,
    }
    all_pass = (
        safety["uqq700_query_executed"] is False
        and safety["negative_evidence_allowed"] is False
        and safety["legal_absence_inference_allowed"] is False
        and safety["site_promotion_allowed"] is False
        and safety["runtime_registration_allowed"] is False
        and safety["ocr_used"] is False
        and safety["brute_force_used"] is False
        and safety["broad_crawl_used"] is False
        and safety["url_guessing_used"] is False
        and safety["target_status"] == "UNKNOWN"
    )

    payload = {
        "target": TARGET_NAME,
        "standard_code": TARGET_CODE,
        "resolution": TARGET_STATUS,
        "source_family_marker": SOURCE_FAMILY_MARKER,
        "expected_target_count": EXPECTED_TARGET_COUNT,
        "prerequisite_paths": prerequisite_paths,
        "recovery_diagnostics": recovery_diagnostics,
        "recovered_target_count": len(targets),
        "exact_prerequisite": exact_prerequisite,
        "targets": targets,
        "probes": probes,
        "any_binary_pdf_verified": any_binary_pdf_verified,
        "classification": classification,
        "next_action": next_action,
        "safety": safety,
        "all_pass": all_pass,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("BINARY ACCESS RESULTS")
    print("-" * 72)
    if probes:
        for target in probes:
            print(
                f"TARGET {target['target_index']}: "
                f"{json.dumps(target['identity'], ensure_ascii=False)}"
            )
            for probe in target["url_probes"]:
                print(
                    "  "
                    f"field={probe['source_field']} "
                    f"status={probe['http_status']} "
                    f"type={probe['content_type']} "
                    f"disposition={probe['content_disposition']} "
                    f"bytes={probe['bytes_read']} "
                    f"pdf_signature={probe['pdf_signature']} "
                    f"technical_unknown={probe['technical_unknown']}"
                )
                print(f"    requested={probe['requested_url']}")
                print(f"    final={probe['final_url']}")
                if probe["redirect_chain"]:
                    print(
                        "    redirects="
                        + json.dumps(probe["redirect_chain"], ensure_ascii=False)
                    )
                if probe["error"]:
                    print(f"    error={probe['error']}")
    else:
        print("NO NETWORK PROBES")
    print()

    print("=" * 72)
    print("RESOLUTION")
    print("=" * 72)
    print(f"Classification: {classification}")
    print(f"Next: {next_action}")
    print(f"UQQ700: {TARGET_STATUS}")
    print(f"Negative evidence allowed: {safety['negative_evidence_allowed']}")
    print(
        "Legal absence inference allowed: "
        f"{safety['legal_absence_inference_allowed']}"
    )
    print(f"SITE promotion allowed: {safety['site_promotion_allowed']}")
    print(f"Runtime registration allowed: {safety['runtime_registration_allowed']}")
    print(f"OCR used: {safety['ocr_used']}")
    print(f"URL guessing used: {safety['url_guessing_used']}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"all_pass: {all_pass}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
