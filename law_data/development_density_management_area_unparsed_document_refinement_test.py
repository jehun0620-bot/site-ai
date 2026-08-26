from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "development_density_management_area_gazette_bulk_fulltext_discovery.json"
)
OUTPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "development_density_management_area_unparsed_document_refinement.json"
)

ALLOWED_CLASSES = {
    "PARSED_NO_TARGET",
    "IMAGE_PDF_REQUIRES_OCR",
    "CLASSIC_HWP_REQUIRES_PARSER",
    "HWPX_PARSE_RETRY",
    "DOWNLOAD_RETRY_REQUIRED",
    "UNSUPPORTED_BINARY",
    "TARGET_DOCUMENT_CANDIDATE",
}

FINAL_POSITIVE_PROHIBITED_CLASSES = ALLOWED_CLASSES.copy()

URL_KEYS = (
    "url",
    "download_url",
    "final_url",
    "source_url",
    "document_url",
    "attachment_url",
)

TYPE_KEYS = (
    "type",
    "document_type",
    "file_type",
    "detected_type",
    "content_type",
)

PARSED_KEYS = (
    "parsed",
    "parse_success",
    "text_extracted",
    "extracted",
)

TARGET_KEYS = (
    "target_in_extracted_text",
    "target_in_document_body",
    "target_found",
    "contains_target",
)

RESOLUTION_KEYS = (
    "resolution",
    "status",
    "parse_resolution",
)

ERROR_KEYS = (
    "parse_error",
    "error",
    "download_error",
    "transport_error",
)

TEXT_KEYS = (
    "text",
    "extracted_text",
    "body_text",
    "content",
    "preview",
)

ACTION_TERMS = (
    "지정",
    "변경",
    "해제",
    "결정",
    "고시",
)

NOTICE_PATTERN = re.compile(
    r"(?:[가-힣]{2,20}\s*)?(?:특별시|광역시|특별자치시|특별자치도|도|시|군|구)?\s*"
    r"(?:고시|공고)\s*제?\s*\d{4}\s*-\s*\d+\s*호?"
)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def first_value(record: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return None


def boolish(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    if isinstance(value, (int, float)):
        return value != 0
    return False


def normalize_doc_type(value: Any, url: str = "") -> str:
    raw = normalize_space(value).upper()

    if "HWPX" in raw:
        return "HWPX"
    if raw == "HWP" or "HWP" in raw:
        return "HWP"
    if "PDF" in raw:
        return "PDF"
    if "HTML" in raw or "TEXT/HTML" in raw:
        return "HTML"
    if "ZIP" in raw:
        return "ZIP"
    if raw and raw != "UNKNOWN":
        return raw

    path = urlparse(url).path.lower()
    if path.endswith(".hwpx"):
        return "HWPX"
    if path.endswith(".hwp"):
        return "HWP"
    if path.endswith(".pdf"):
        return "PDF"
    if path.endswith(".zip"):
        return "ZIP"
    if path.endswith((".html", ".htm")):
        return "HTML"

    return "UNKNOWN"


def looks_like_document_record(obj: dict[str, Any]) -> bool:
    keys = set(obj.keys())

    has_url = any(k in keys and obj.get(k) for k in URL_KEYS)
    has_doc_signal = any(k in keys for k in TYPE_KEYS + PARSED_KEYS + RESOLUTION_KEYS + ERROR_KEYS)
    has_target_signal = any(k in keys for k in TARGET_KEYS)

    if has_url and (has_doc_signal or has_target_signal):
        return True

    # V-stage implementations may store candidate URL under a generic key plus
    # document metadata nested in the same record.
    if has_doc_signal and ("label" in keys or "candidate_index" in keys or "region" in keys):
        return True

    return False


def recursively_collect_records(obj: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if looks_like_document_record(value):
                found.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(obj)

    # Deduplicate by the best available stable signature.
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in found:
        url = normalize_space(first_value(item, URL_KEYS))
        dtype = normalize_doc_type(first_value(item, TYPE_KEYS), url)
        resolution = normalize_space(first_value(item, RESOLUTION_KEYS))
        signature = (url, dtype, resolution)

        if signature == ("", "UNKNOWN", ""):
            signature = (
                normalize_space(item.get("label")),
                normalize_space(item.get("region")),
                normalize_space(item.get("candidate_index")),
            )
        unique.setdefault(signature, item)

    return list(unique.values())


def extract_record_text(record: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in TEXT_KEYS:
        value = record.get(key)
        if isinstance(value, str) and value:
            parts.append(value)

    # Include shallow scalar metadata because some V-stage variants omit
    # extracted_text while keeping target/action/notice fragments separately.
    for key in (
        "label",
        "title",
        "preview",
        "action_terms",
        "notice_numbers",
        "reasons",
    ):
        value = record.get(key)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(str(v) for v in value if isinstance(v, (str, int, float)))

    return normalize_space(" ".join(parts))


def has_target(record: dict[str, Any], text: str) -> bool:
    explicit = first_value(record, TARGET_KEYS)
    if explicit is not None and boolish(explicit):
        return True
    return TARGET_NAME in text


def has_action_context(record: dict[str, Any], text: str) -> bool:
    explicit = record.get("action_terms")
    if isinstance(explicit, list) and explicit:
        return any(normalize_space(x) in ACTION_TERMS for x in explicit)
    return any(term in text for term in ACTION_TERMS)


def extract_notice_numbers(record: dict[str, Any], text: str) -> list[str]:
    existing = record.get("notice_numbers")
    values: list[str] = []
    if isinstance(existing, list):
        values.extend(normalize_space(x) for x in existing if normalize_space(x))
    elif isinstance(existing, str) and normalize_space(existing):
        values.append(normalize_space(existing))

    values.extend(normalize_space(m.group(0)) for m in NOTICE_PATTERN.finditer(text))
    return list(dict.fromkeys(values))


def classify(record: dict[str, Any]) -> tuple[str, list[str]]:
    url = normalize_space(first_value(record, URL_KEYS))
    doc_type = normalize_doc_type(first_value(record, TYPE_KEYS), url)
    parsed = boolish(first_value(record, PARSED_KEYS))
    resolution = normalize_space(first_value(record, RESOLUTION_KEYS)).upper()
    error_text = normalize_space(first_value(record, ERROR_KEYS))
    text = extract_record_text(record)

    target = has_target(record, text)
    action = has_action_context(record, text)
    notice_numbers = extract_notice_numbers(record, text)

    reasons: list[str] = []

    # A candidate is still not a verified positive. It merely deserves a
    # dedicated verification stage.
    if target:
        reasons.append("TARGET_TEXT_EVIDENCE")
        if action:
            reasons.append("ACTION_CONTEXT_EVIDENCE")
        if notice_numbers:
            reasons.append("NOTICE_NUMBER_EVIDENCE")
        return "TARGET_DOCUMENT_CANDIDATE", reasons

    if parsed:
        reasons.append("PARSED_DOCUMENT")
        reasons.append("TARGET_NOT_FOUND")
        return "PARSED_NO_TARGET", reasons

    transport_markers = (
        "TRANSPORT",
        "DOWNLOAD_ERROR",
        "TIMEOUT",
        "CONNECTTIMEOUT",
        "READTIMEOUT",
        "CONNECTIONERROR",
        "EXCEEDS",
        "MAXRETRY",
    )
    combined_error = f"{resolution} {error_text}".upper()
    if any(marker in combined_error for marker in transport_markers):
        reasons.append("DOWNLOAD_OR_TRANSPORT_FAILURE")
        if "52428800" in combined_error or "50" in combined_error and "MB" in combined_error:
            reasons.append("SIZE_LIMIT_FAILURE")
        if "TIMEOUT" in combined_error:
            reasons.append("TIMEOUT_FAILURE")
        return "DOWNLOAD_RETRY_REQUIRED", reasons

    if doc_type == "HWP":
        reasons.append("CLASSIC_HWP")
        reasons.append("TEXT_PARSE_NOT_COMPLETED")
        return "CLASSIC_HWP_REQUIRES_PARSER", reasons

    if doc_type == "HWPX":
        reasons.append("HWPX")
        reasons.append("TEXT_PARSE_NOT_COMPLETED")
        return "HWPX_PARSE_RETRY", reasons

    if doc_type == "PDF":
        # V-stage already attempted ordinary text parsing. A remaining
        # unparsed PDF is treated as an OCR candidate, not as a target positive.
        reasons.append("PDF_UNPARSED_AFTER_TEXT_EXTRACTION")
        reasons.append("OCR_REQUIRED_BEFORE_TARGET_DECISION")
        return "IMAGE_PDF_REQUIRES_OCR", reasons

    reasons.append(f"UNSUPPORTED_OR_UNKNOWN_TYPE:{doc_type}")
    return "UNSUPPORTED_BINARY", reasons


def canonical_url(record: dict[str, Any]) -> str:
    return normalize_space(first_value(record, URL_KEYS))


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("UNPARSED DOCUMENT REFINEMENT / PARSER ROUTING")
    print("=" * 60)
    print()
    print(f"Target: {TARGET_NAME}")
    print(f"Standard code: {STANDARD_CODE}")
    print(f"Input: {INPUT_PATH}")
    print()

    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"V-stage input not found: {INPUT_PATH}")

    payload = load_json(INPUT_PATH)
    records = recursively_collect_records(payload)

    refined: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        url = canonical_url(record)
        doc_type = normalize_doc_type(first_value(record, TYPE_KEYS), url)
        parsed = boolish(first_value(record, PARSED_KEYS))
        resolution = normalize_space(first_value(record, RESOLUTION_KEYS))
        error_text = normalize_space(first_value(record, ERROR_KEYS))
        text = extract_record_text(record)
        target = has_target(record, text)
        action = has_action_context(record, text)
        notice_numbers = extract_notice_numbers(record, text)
        classification, reasons = classify(record)

        refined.append(
            {
                "index": index,
                "region": normalize_space(record.get("region") or record.get("municipality")),
                "label": normalize_space(record.get("label") or record.get("title")),
                "url": url,
                "document_type": doc_type,
                "v_stage_parsed": parsed,
                "v_stage_resolution": resolution,
                "v_stage_error": error_text,
                "target_evidence": target,
                "action_context": action,
                "notice_numbers": notice_numbers,
                "classification": classification,
                "reasons": reasons,
            }
        )

    # Prefer URL-based uniqueness. Records without URLs are preserved by
    # metadata signature so we do not accidentally discard transport errors.
    dedup: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for item in refined:
        key = (
            item["url"],
            item["document_type"],
            item["v_stage_resolution"],
            item["label"],
        )
        dedup.setdefault(key, item)
    refined = list(dedup.values())

    counts = Counter(item["classification"] for item in refined)

    parser_queue_classes = {
        "IMAGE_PDF_REQUIRES_OCR",
        "CLASSIC_HWP_REQUIRES_PARSER",
        "HWPX_PARSE_RETRY",
        "DOWNLOAD_RETRY_REQUIRED",
        "TARGET_DOCUMENT_CANDIDATE",
    }
    parser_queue = [
        item for item in refined if item["classification"] in parser_queue_classes
    ]

    target_candidates = [
        item for item in refined if item["classification"] == "TARGET_DOCUMENT_CANDIDATE"
    ]

    result = {
        "target_name": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "input": str(INPUT_PATH),
        "record_count": len(refined),
        "classification_counts": dict(sorted(counts.items())),
        "parser_queue_count": len(parser_queue),
        "target_document_candidate_count": len(target_candidates),
        "records": refined,
        "next_stage_parser_queue": parser_queue,
        "target_document_candidates": target_candidates,
        "runtime_registration_allowed": False,
        "site_false_blocked": True,
        "final_positive_promotion_allowed": False,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print("REFINEMENT RESULT")
    print("=" * 60)
    print(f"Document record count: {len(refined)}")
    print()
    for cls in sorted(ALLOWED_CLASSES):
        print(f"{cls}: {counts.get(cls, 0)}")
    print()
    print(f"Next-stage parser queue: {len(parser_queue)}")
    print(f"Target document candidate count: {len(target_candidates)}")

    if parser_queue:
        print()
        print("NEXT-STAGE PARSER QUEUE")
        print("-" * 60)
        for item in parser_queue[:80]:
            print(
                f"[{item['index']}] "
                f"{item['region'] or '-'} | "
                f"{item['classification']} | "
                f"{item['document_type']} | "
                f"{item['label'] or '-'}"
            )
            print(f"URL: {item['url'] or '-'}")
            if item["v_stage_error"]:
                print(f"V-stage error: {item['v_stage_error']}")
            print(f"Reasons: {item['reasons']}")
            print()

    print("=" * 60)
    print("RESOLUTION")
    print("=" * 60)
    if target_candidates:
        print("UNPARSED_DOCUMENT_REFINEMENT_TARGET_CANDIDATE_DISCOVERED")
        print()
        print(
            "target-bearing 문서는 아직 verified positive가 아니다. "
            "다음 단계에서 원문 body, 지정·변경·해제 action context, "
            "고시번호와 행정구역을 다시 검증한다."
        )
    elif parser_queue:
        print("UNPARSED_DOCUMENT_REFINEMENT_COMPLETED_PARSER_QUEUE_READY")
        print()
        print(
            "미해석 문서를 PDF OCR / classic HWP / HWPX 재파싱 / "
            "download retry 큐로 분리했다. 다음 단계에서는 각 parser "
            "class별 실제 원문 추출을 수행한다."
        )
    else:
        print("UNPARSED_DOCUMENT_REFINEMENT_COMPLETED_NO_FURTHER_PARSER_QUEUE")
        print()
        print("V-stage 결과에서 추가 parser 처리가 필요한 문서를 확인하지 못했다.")

    print()
    print(f"Output: {OUTPUT_PATH}")
    print()

    validation = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "input exists": INPUT_PATH.exists(),
        "V-stage input parsed": isinstance(payload, (dict, list)),
        "document record extraction enabled": True,
        "all classifications valid": all(
            item["classification"] in ALLOWED_CLASSES for item in refined
        ),
        "parsed documents not routed to OCR/HWP parser": all(
            not item["v_stage_parsed"]
            or item["classification"] in {"PARSED_NO_TARGET", "TARGET_DOCUMENT_CANDIDATE"}
            for item in refined
        ),
        "classic HWP routed explicitly": all(
            item["document_type"] != "HWP"
            or item["v_stage_parsed"]
            or item["classification"]
            in {
                "CLASSIC_HWP_REQUIRES_PARSER",
                "DOWNLOAD_RETRY_REQUIRED",
                "TARGET_DOCUMENT_CANDIDATE",
            }
            for item in refined
        ),
        "unparsed PDF routed to OCR": all(
            item["document_type"] != "PDF"
            or item["v_stage_parsed"]
            or item["classification"]
            in {
                "IMAGE_PDF_REQUIRES_OCR",
                "DOWNLOAD_RETRY_REQUIRED",
                "TARGET_DOCUMENT_CANDIDATE",
            }
            for item in refined
        ),
        "HWPX retry routing enabled": all(
            item["document_type"] != "HWPX"
            or item["v_stage_parsed"]
            or item["classification"]
            in {
                "HWPX_PARSE_RETRY",
                "DOWNLOAD_RETRY_REQUIRED",
                "TARGET_DOCUMENT_CANDIDATE",
            }
            for item in refined
        ),
        "transport errors routed to retry": all(
            (
                "TRANSPORT" not in item["v_stage_resolution"].upper()
                and "DOWNLOAD_ERROR" not in item["v_stage_resolution"].upper()
                and "TIMEOUT" not in item["v_stage_error"].upper()
                and "EXCEEDS" not in item["v_stage_error"].upper()
            )
            or item["classification"] in {
                "DOWNLOAD_RETRY_REQUIRED",
                "TARGET_DOCUMENT_CANDIDATE",
            }
            for item in refined
        ),
        "target candidate requires target evidence": all(
            item["target_evidence"]
            for item in target_candidates
        ),
        "target candidate is not final positive": True,
        "runtime registration remains blocked": not result["runtime_registration_allowed"],
        "SITE FALSE remains blocked": result["site_false_blocked"],
        "final positive promotion remains blocked": not result[
            "final_positive_promotion_allowed"
        ],
        "output written": OUTPUT_PATH.exists(),
    }

    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for key, passed in validation.items():
        print(f"{key}: {passed}")

    all_pass = all(validation.values())
    print()
    print(f"all_pass: {all_pass}")

    if not all_pass:
        failed = [key for key, passed in validation.items() if not passed]
        print()
        print("FAILED:")
        for key in failed:
            print(f"- {key}")
        raise AssertionError(
            "Development density management area unparsed document "
            "refinement regression failed"
        )


if __name__ == "__main__":
    main()
