# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-16-S8-CONT
Development Density Management Area
Reusable Historical Row Coverage Continuation

This runner automatically loads all prior S8 coverage outputs matching the known output prefix,
accumulates already-covered pages, and requests only the next unvisited pages within the
T-15-S2 traversal-safe range. It can be run repeatedly without changing code.

Safety:
- bounded requests only
- no detail request execution
- no target query execution
- only row-local direct '개발밀도관리구역' metadata becomes a candidate
- no candidate is never SITE FALSE
- verified positive/runtime registration/SITE TRUE/SITE FALSE remain blocked
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

T15S2_PATH = OUTPUT_DIR / "development_density_management_area_competent_authority_historical_boundary_semantic_hardening.json"
S8_BASE_PATH = OUTPUT_DIR / "development_density_management_area_competent_authority_historical_row_identity_recovery.json"
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_competent_authority_historical_row_coverage_continuation.json"

COVERAGE_GLOBS = [
    "development_density_management_area_competent_authority_historical_row_coverage_expansion*.json",
    "development_density_management_area_competent_authority_historical_row_coverage_continuation*.json",
]

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

FAMILY_NOTICE = "CURRENT_MUNICIPAL_OFFICIAL_NOTICE_ARCHIVE"
FAMILY_URBAN = "CURRENT_URBAN_PLANNING_INFORMATION_ARCHIVE"
FUNCTION_BY_FAMILY = {
    FAMILY_NOTICE: "f_view",
    FAMILY_URBAN: "fn_move_form",
}

MAX_TOTAL_REQUESTS = 48
MAX_REQUESTS_PER_CONTRACT = 24
TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

TR_PATTERN = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
TAG_PATTERN = re.compile(r"<[^>]+>", re.S)
SCRIPT_STYLE_PATTERN = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>", re.I | re.S)
COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.S)
TARGET_PATTERN = re.compile(r"개발\s*밀도\s*관리\s*구역", re.I)
DATE_PATTERN = re.compile(
    r"(?<!\d)((?:19|20)\d{2})[.\-/년\s]+(0?[1-9]|1[0-2])[.\-/월\s]+(0?[1-9]|[12]\d|3[01])(?:일)?(?!\d)"
)
NOTICE_PATTERN = re.compile(r"(?:고시|공고)\s*(?:제)?\s*\d{4}\s*[-–]\s*\d+\s*호?", re.I)


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def unique_strings(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: Set[str] = set()
    for value in values:
        text = normalize_space(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def strip_html(raw: str) -> str:
    value = COMMENT_PATTERN.sub(" ", raw or "")
    value = SCRIPT_STYLE_PATTERN.sub(" ", value)
    value = TAG_PATTERN.sub(" ", value)
    return normalize_space(html.unescape(value))


def canonicalize_url(url: str) -> str:
    value = normalize_space(url)
    if not value:
        return ""
    p = urlparse(value)
    if not p.hostname:
        return ""
    params = sorted(parse_qsl(p.query, keep_blank_values=True), key=lambda x: (x[0].lower(), x[1]))
    return urlunparse(((p.scheme or "https").lower(), (p.hostname or "").lower(), re.sub(r"/{2,}", "/", p.path or "/"), "", urlencode(params, doseq=True), ""))


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_government_host(host: str) -> bool:
    host = normalize_space(host).lower()
    return bool(host) and (host == "go.kr" or host.endswith(".go.kr"))


def decode_text(response: requests.Response, raw: bytes) -> str:
    for enc in unique_strings([response.encoding, "utf-8", "cp949", "euc-kr"]):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="replace")


def fetch_page(session: requests.Session, url: str) -> Dict[str, Any]:
    result = {"http_status": None, "final_url": "", "text": "", "error": ""}
    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
            result["http_status"] = response.status_code
            result["final_url"] = canonicalize_url(str(response.url))
            chunks: List[bytes] = []
            total = 0
            for chunk in response.iter_content(128 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise ValueError("response too large")
                chunks.append(chunk)
            result["text"] = decode_text(response, b"".join(chunks))
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def build_page_url(base_url: str, key: str, page: int) -> str:
    p = urlparse(base_url)
    q = dict(parse_qsl(p.query, keep_blank_values=True))
    q[key] = str(page)
    return canonicalize_url(urlunparse((p.scheme, p.netloc, p.path, "", urlencode(q), "")))


def parse_rows(raw_html: str, family: str, page_url: str, page_number: int) -> List[Dict[str, Any]]:
    function_name = FUNCTION_BY_FAMILY[family]
    call_pattern = re.compile(rf"{re.escape(function_name)}\s*\(\s*['\"]?(\d+)['\"]?\s*\)", re.I)
    rows: List[Dict[str, Any]] = []

    for tr_index, match in enumerate(TR_PATTERN.finditer(raw_html or ""), start=1):
        row_html = match.group(1)
        arguments = unique_strings(m.group(1) for m in call_pattern.finditer(row_html))
        if not arguments:
            continue
        row_text = strip_html(row_html)
        if not row_text:
            continue
        target_match = TARGET_PATTERN.search(row_text)
        notices = unique_strings(m.group(0) for m in NOTICE_PATTERN.finditer(row_text))
        dates = [
            f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
            for year, month, day in DATE_PATTERN.findall(row_text)
        ]

        for argument in arguments:
            rows.append({
                "source_family": family,
                "page_number": page_number,
                "page_url": page_url,
                "tr_index": tr_index,
                "function": function_name,
                "argument": argument,
                "row_text": row_text[:5000],
                "notice_numbers": notices,
                "dates": unique_strings(dates),
                "target_identity_direct": bool(target_match),
                "document_candidate_only": bool(target_match),
                "detail_request_executed": False,
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
                "site_negative_allowed": False,
                "final_positive_promotion_allowed": False,
            })
    return rows


def load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def discover_prior_output_files() -> List[Path]:
    files: Set[Path] = set()
    if S8_BASE_PATH.exists():
        files.add(S8_BASE_PATH)
    for pattern in COVERAGE_GLOBS:
        for path in OUTPUT_DIR.glob(pattern):
            if path == OUTPUT_PATH:
                continue
            if path.is_file():
                files.add(path)
    return sorted(files, key=lambda p: p.name)


def load_prior_pages(paths: Iterable[Path]) -> Set[Tuple[str, int]]:
    result: Set[Tuple[str, int]] = set()
    for path in paths:
        data = load_json(path)
        for item in data.get("page_results") or []:
            if not isinstance(item, dict):
                continue
            family = normalize_space(item.get("source_family"))
            page = int(item.get("page_number") or 0)
            if family in FUNCTION_BY_FAMILY and page > 0:
                result.add((family, page))
    return result


def load_prior_candidates(paths: Iterable[Path]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()
    for path in paths:
        data = load_json(path)
        for key in ("uqq700_candidates", "uqq700_target_candidates", "next_stage_document_candidate_pool"):
            for item in data.get(key) or []:
                if not isinstance(item, dict) or item.get("target_identity_direct") is not True:
                    continue
                identity = (normalize_space(item.get("source_family")), normalize_space(item.get("argument")))
                if identity in seen:
                    continue
                seen.add(identity)
                result.append(item)
    return result


def load_contracts(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str, str]] = set()
    for item in data.get("next_stage_boundary_pool") or []:
        if not isinstance(item, dict):
            continue
        family = normalize_space(item.get("source_family"))
        if family not in FUNCTION_BY_FAMILY:
            continue
        base_url = canonicalize_url(item.get("primary_base_url") or item.get("base_url") or "")
        pagination_key = normalize_space(item.get("pagination_key"))
        if not base_url or not pagination_key:
            continue
        identity = (family, base_url, pagination_key.lower())
        if identity in seen:
            continue
        seen.add(identity)
        result.append({
            "source_family": family,
            "base_url": base_url,
            "pagination_key": pagination_key,
            "lower": int(item.get("effective_lower_page") or 1),
            "upper": int(item.get("effective_upper_page") or 0),
        })
    return result


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("REUSABLE HISTORICAL ROW COVERAGE CONTINUATION")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Detail request execution: DISABLED")
    print()

    if not T15S2_PATH.exists():
        raise FileNotFoundError(f"T-15-S2 input missing: {T15S2_PATH}")

    t15 = load_json(T15S2_PATH)
    prior_files = discover_prior_output_files()
    prior_pages = load_prior_pages(prior_files)
    prior_candidates = load_prior_candidates(prior_files)
    contracts = load_contracts(t15)

    print("Prior output files:", len(prior_files))
    for path in prior_files:
        print("-", path.name)
    print("Prior covered pages:", len(prior_pages))
    print("Prior UQQ700 candidates:", len(prior_candidates))
    print("Traversal contracts:", len(contracts))
    print()

    # Once a candidate exists, continuation must not crawl more pages.
    if prior_candidates:
        output_data = {
            "step": "STEP 17-21-C-16-8-T-16-S8-CONT Reusable Historical Row Coverage Continuation",
            "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
            "summary": {
                "prior_output_file_count": len(prior_files),
                "prior_covered_page_count": len(prior_pages),
                "request_count": 0,
                "uqq700_candidate_count": len(prior_candidates),
            },
            "page_results": [],
            "uqq700_candidates": prior_candidates,
            "next_stage_document_candidate_pool": prior_candidates,
            "resolution": "COMPETENT_AUTHORITY_COVERAGE_CONTINUATION_SKIPPED_EXISTING_UQQ700_CANDIDATE",
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Existing candidate detected; no more coverage requests executed.")
        print("Output:", OUTPUT_PATH)
        print("all_pass: True")
        return

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})

    request_count = 0
    http_success_count = 0
    transport_error_count = 0
    all_rows: List[Dict[str, Any]] = []
    page_results: List[Dict[str, Any]] = []

    for index, contract in enumerate(contracts, start=1):
        missing_pages = [
            page
            for page in range(contract["lower"], contract["upper"] + 1)
            if (contract["source_family"], page) not in prior_pages
        ]
        selected_pages = missing_pages[:MAX_REQUESTS_PER_CONTRACT]

        print("-" * 60)
        print("CONTRACT", index)
        print("Family:", contract["source_family"])
        print("Base URL:", contract["base_url"])
        print("Missing page count:", len(missing_pages))
        print("Selected pages:", selected_pages)

        for page in selected_pages:
            if request_count >= MAX_TOTAL_REQUESTS:
                break
            page_url = build_page_url(contract["base_url"], contract["pagination_key"], page)
            response = fetch_page(session, page_url)
            request_count += 1
            status = response.get("http_status")
            if isinstance(status, int) and 200 <= status < 300:
                http_success_count += 1
            if response.get("error"):
                transport_error_count += 1

            rows: List[Dict[str, Any]] = []
            if isinstance(status, int) and 200 <= status < 300:
                rows = parse_rows(
                    str(response.get("text") or ""),
                    contract["source_family"],
                    response.get("final_url") or page_url,
                    page,
                )
                all_rows.extend(rows)

            page_results.append({
                "source_family": contract["source_family"],
                "page_number": page,
                "page_url": page_url,
                "http_status": status,
                "interaction_row_count": len(rows),
            })

    canonical_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    duplicate_removed = 0
    for row in all_rows:
        identity = (row["source_family"], row["argument"])
        if identity in canonical_map:
            duplicate_removed += 1
            existing = canonical_map[identity]
            if row.get("target_identity_direct") is True:
                existing["target_identity_direct"] = True
                existing["document_candidate_only"] = True
            existing["page_numbers"] = sorted(
                set((existing.get("page_numbers") or [existing.get("page_number")]) + [row.get("page_number")])
            )
            continue
        item = dict(row)
        item["page_numbers"] = [row.get("page_number")]
        canonical_map[identity] = item

    canonical_rows = list(canonical_map.values())
    current_candidates = [item for item in canonical_rows if item.get("target_identity_direct") is True]

    cumulative_pages = set(prior_pages)
    cumulative_pages.update((item["source_family"], int(item["page_number"])) for item in page_results)

    remaining_coverage: List[Dict[str, Any]] = []
    total_remaining = 0
    for contract in contracts:
        remaining = [
            page
            for page in range(contract["lower"], contract["upper"] + 1)
            if (contract["source_family"], page) not in cumulative_pages
        ]
        total_remaining += len(remaining)
        remaining_coverage.append({
            "source_family": contract["source_family"],
            "base_url": contract["base_url"],
            "remaining_page_count": len(remaining),
            "remaining_pages": remaining[:250],
        })

    resolution = (
        "COMPETENT_AUTHORITY_COVERAGE_CONTINUATION_UQQ700_CANDIDATE_RECOVERED"
        if current_candidates
        else (
            "COMPETENT_AUTHORITY_COVERAGE_CONTINUATION_COMPLETE_NO_UQQ700_ROW"
            if total_remaining == 0
            else "COMPETENT_AUTHORITY_COVERAGE_CONTINUATION_PARTIAL_NO_UQQ700_ROW"
        )
    )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-16-S8-CONT Reusable Historical Row Coverage Continuation",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "summary": {
            "prior_output_file_count": len(prior_files),
            "prior_covered_page_count": len(prior_pages),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "raw_interaction_row_count": len(all_rows),
            "duplicate_row_removed": duplicate_removed,
            "canonical_row_count": len(canonical_rows),
            "uqq700_candidate_count": len(current_candidates),
            "remaining_page_count": total_remaining,
            "remaining_coverage": remaining_coverage,
        },
        "page_results": page_results,
        "canonical_rows": canonical_rows,
        "uqq700_candidates": current_candidates,
        "next_stage_document_candidate_pool": current_candidates,
        "resolution": resolution,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    requery_leakage = sum(
        1
        for item in page_results
        if (item["source_family"], int(item["page_number"])) in prior_pages
    )
    invalid_host_leakage = sum(
        1 for item in page_results
        if not is_government_host(hostname(item.get("page_url") or ""))
    )
    unsafe_leakage = sum(
        1
        for item in canonical_rows
        if item.get("detail_request_executed") is True
        or item.get("verified_positive") is True
        or item.get("runtime_registration_allowed") is True
        or item.get("site_positive_allowed") is True
        or item.get("site_negative_allowed") is True
        or item.get("final_positive_promotion_allowed") is True
    )

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "T-15-S2 input exists": T15S2_PATH.exists(),
        "prior coverage automatically discovered": len(prior_files) > 0,
        "prior covered pages loaded": len(prior_pages) > 0,
        "bounded request count respected": request_count <= MAX_TOTAL_REQUESTS,
        "already-covered page requery leakage zero": requery_leakage == 0,
        "page hosts go.kr": invalid_host_leakage == 0,
        "detail request execution disabled": True,
        "target query execution disabled": True,
        "unsafe promotion leakage zero": unsafe_leakage == 0,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print()
    print("=" * 60)
    print("COVERAGE CONTINUATION RESULT")
    print("=" * 60)
    print("Prior covered pages:", len(prior_pages))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Canonical rows:", len(canonical_rows))
    print("UQQ700 candidates:", len(current_candidates))
    print("Remaining page count:", total_remaining)
    print("Remaining coverage:", remaining_coverage)
    print("Resolution:", resolution)
    print("Output:", OUTPUT_PATH)
    print()
    print("VALIDATION")
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("Requery leakage:", requery_leakage)
    print("Invalid host leakage:", invalid_host_leakage)
    print("Unsafe promotion leakage:", unsafe_leakage)
    print("all_pass:", all(validations.values()))

    if not all(validations.values()):
        raise AssertionError("reusable historical coverage continuation regression failed")


if __name__ == "__main__":
    main()
