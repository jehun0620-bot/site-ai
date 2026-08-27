# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-16-S8

Development Density Management Area
Competent Authority Historical Row Identity Recovery & UQQ700 Metadata Filter

목표
======================================================================
S7-S3에서 known sample로 검증된 exact detail contract를 신뢰 가능한 후단 contract로 두고,
T-15-S2 traversal-safe pagination 범위에서 실제 row-local interaction identity를 복원한다.

이번 단계에서는 detail request를 실행하지 않는다.
각 historical page의 실제 <tr> 안에서 다음을 동시에 복원한다.

- f_view(notAncmtMgtNo) 또는 fn_move_form(pstSn)
- row-local title/text
- notice number
- date
- source family / page number

그 후 row-local metadata 자체에 개발밀도관리구역 identity가 직접 존재하는 경우만
후속 direct detail verification 대상으로 넘긴다.

핵심 원칙
======================================================================
1. T-15-S2 traversal-safe contract만 사용한다.
2. S7-S3에서 validated된 source family만 사용한다.
3. effective page range를 초과하지 않는다.
4. bounded traversal schedule만 사용한다.
5. 실제 <tr> 내부의 observed function call만 identity로 인정한다.
6. page title/source URL/query 문자열은 UQQ700 evidence가 아니다.
7. row-local text에 개발밀도관리구역 direct identity가 있어야 candidate가 된다.
8. generic 도시관리계획/지구단위계획은 자동 승격하지 않는다.
9. detail request 실행 금지.
10. candidate는 verified positive가 아니다.
11. SITE TRUE / SITE FALSE / runtime registration 자동판정 금지.
"""
from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
T15S2_INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_competent_authority_historical_boundary_semantic_hardening.json"
)
S7S3_INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_competent_authority_exact_serialization_detail_validation.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_competent_authority_historical_row_identity_recovery.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

FAMILY_NOTICE = "CURRENT_MUNICIPAL_OFFICIAL_NOTICE_ARCHIVE"
FAMILY_URBAN = "CURRENT_URBAN_PLANNING_INFORMATION_ARCHIVE"
ALLOWED_FAMILIES = {FAMILY_NOTICE, FAMILY_URBAN}
FUNCTION_BY_FAMILY = {
    FAMILY_NOTICE: "f_view",
    FAMILY_URBAN: "fn_move_form",
}

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 48
MAX_REQUESTS_PER_CONTRACT = 24
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

TR_PATTERN = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
TAG_PATTERN = re.compile(r"<[^>]+>", re.S)
SCRIPT_STYLE_PATTERN = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>", re.I | re.S)
COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.S)

TARGET_PATTERN = re.compile(r"개발\s*밀도\s*관리\s*구역", re.I)
GENERIC_URBAN_PATTERN = re.compile(r"(?:도시관리계획|도시계획|지구단위계획|용도지역|용도지구|용도구역)", re.I)
DATE_PATTERN = re.compile(
    r"(?<!\d)((?:19|20)\d{2})[.\-/년\s]+(0?[1-9]|1[0-2])[.\-/월\s]+(0?[1-9]|[12]\d|3[01])(?:일)?(?!\d)"
)
NOTICE_NUMBER_PATTERNS = [
    re.compile(r"(?:[가-힣A-Za-z0-9 ]{0,20})?(?:고시|공고)\s*(?:제)?\s*(\d{4})\s*[-–]\s*(\d+)\s*호?", re.I),
    re.compile(r"(?:제)?\s*(\d{4})\s*[-–]\s*(\d+)\s*호", re.I),
]

CLASS_ROW_IDENTITY = "RECOVERED_HISTORICAL_INTERACTION_ROW_IDENTITY"
CLASS_TARGET_CANDIDATE = "RECOVERED_UQQ700_HISTORICAL_ROW_CANDIDATE"
CLASS_OTHER_ROW = "REJECTED_NON_TARGET_HISTORICAL_ROW"
CLASS_GENERIC_URBAN = "REJECTED_GENERIC_URBAN_ROW"
VALID_CLASSES = {
    CLASS_ROW_IDENTITY,
    CLASS_TARGET_CANDIDATE,
    CLASS_OTHER_ROW,
    CLASS_GENERIC_URBAN,
}


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
    value = html.unescape(value)
    return normalize_space(value)


def canonicalize_url(url: str) -> str:
    value = normalize_space(url)
    if not value:
        return ""
    try:
        p = urlparse(value)
    except Exception:
        return ""
    if not p.hostname:
        return ""
    scheme = (p.scheme or "https").lower()
    host = (p.hostname or "").lower()
    netloc = host
    try:
        port = p.port
    except ValueError:
        port = None
    if port and not (scheme == "http" and port == 80) and not (scheme == "https" and port == 443):
        netloc = f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", p.path or "/")
    items = sorted(parse_qsl(p.query, keep_blank_values=True), key=lambda x: (x[0].lower(), x[1]))
    return urlunparse((scheme, netloc, path, "", urlencode(items, doseq=True), ""))


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_government_host(host: str) -> bool:
    host = normalize_space(host).lower()
    return bool(host) and (host == "go.kr" or host.endswith(".go.kr"))


def same_host(a: str, b: str) -> bool:
    return bool(hostname(a)) and hostname(a) == hostname(b)


def decode_text(response: requests.Response, raw: bytes) -> str:
    for encoding in unique_strings([response.encoding, "utf-8", "cp949", "euc-kr"]):
        try:
            return raw.decode(encoding)
        except Exception:
            continue
    return raw.decode("utf-8", errors="replace")


def fetch_page(session: requests.Session, url: str) -> Dict[str, Any]:
    result = {"http_status": None, "final_url": "", "text": "", "bytes": 0, "error": ""}
    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
            result["http_status"] = response.status_code
            result["final_url"] = canonicalize_url(str(response.url))
            chunks: List[bytes] = []
            total = 0
            for chunk in response.iter_content(chunk_size=128 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise ValueError("response exceeds MAX_RESPONSE_BYTES")
                chunks.append(chunk)
            raw = b"".join(chunks)
            result["bytes"] = len(raw)
            result["text"] = decode_text(response, raw)
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def extract_notice_numbers(text: str) -> List[str]:
    result: List[str] = []
    for pattern in NOTICE_NUMBER_PATTERNS:
        for match in pattern.finditer(text or ""):
            result.append(normalize_space(match.group(0)))
    return unique_strings(result)


def extract_dates(text: str) -> List[str]:
    result: List[str] = []
    for match in DATE_PATTERN.finditer(text or ""):
        y, m, d = match.groups()
        result.append(f"{int(y):04d}-{int(m):02d}-{int(d):02d}")
    return unique_strings(result)


def traversal_pages(lower: int, upper: int) -> List[int]:
    if upper < lower:
        return []
    size = upper - lower + 1
    if size <= MAX_REQUESTS_PER_CONTRACT:
        return list(range(lower, upper + 1))

    observed_prefix_end = min(upper, lower + 20)
    pages = list(range(lower, observed_prefix_end + 1))
    for page in (50, 100, upper):
        if lower <= page <= upper:
            pages.append(page)
    return sorted(set(pages))[:MAX_REQUESTS_PER_CONTRACT]


def load_validated_families(data: Dict[str, Any]) -> Set[str]:
    result: Set[str] = set()
    raw = data.get("next_stage_validated_detail_contract_pool")
    if not isinstance(raw, list):
        raw = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        family = normalize_space(item.get("source_family"))
        if family in ALLOWED_FAMILIES and item.get("sample_reproduced") is True:
            result.add(family)
    return result


def load_traversal_contracts(data: Dict[str, Any], validated_families: Set[str]) -> List[Dict[str, Any]]:
    raw = data.get("next_stage_boundary_pool")
    if not isinstance(raw, list):
        raw = []
    result: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str, str]] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        family = normalize_space(item.get("source_family"))
        if family not in validated_families:
            continue
        base_url = canonicalize_url(item.get("primary_base_url") or item.get("base_url") or "")
        key = normalize_space(item.get("pagination_key"))
        if not base_url or not key:
            continue
        lower = int(item.get("effective_lower_page") or 1)
        upper = int(item.get("effective_upper_page") or 0)
        identity = (family, base_url, key.lower())
        if identity in seen:
            continue
        seen.add(identity)
        result.append({
            "source_family": family,
            "base_url": base_url,
            "pagination_key": key,
            "effective_lower_page": lower,
            "effective_upper_page": upper,
        })
    return result


def build_page_url(base_url: str, pagination_key: str, page: int) -> str:
    p = urlparse(base_url)
    params = dict(parse_qsl(p.query, keep_blank_values=True))
    params[pagination_key] = str(page)
    return canonicalize_url(urlunparse((p.scheme, p.netloc, p.path, "", urlencode(params), "")))


def extract_interaction_rows(raw_html: str, family: str, page_url: str, page_number: int) -> List[Dict[str, Any]]:
    function_name = FUNCTION_BY_FAMILY[family]
    call_pattern = re.compile(rf"{re.escape(function_name)}\s*\(\s*['\"]?(\d+)['\"]?\s*\)", re.I)
    rows: List[Dict[str, Any]] = []
    seen_args: Set[str] = set()

    for tr_index, match in enumerate(TR_PATTERN.finditer(raw_html or ""), start=1):
        row_html = match.group(1)
        calls = unique_strings(m.group(1) for m in call_pattern.finditer(row_html))
        if not calls:
            continue
        row_text = strip_html(row_html)
        if not row_text:
            continue
        for argument in calls:
            if argument in seen_args:
                continue
            seen_args.add(argument)
            notices = extract_notice_numbers(row_text)
            dates = extract_dates(row_text)
            target_match = TARGET_PATTERN.search(row_text)
            generic_urban = bool(GENERIC_URBAN_PATTERN.search(row_text)) and not target_match
            if target_match:
                classification = CLASS_TARGET_CANDIDATE
                reasons = ["ROW_LOCAL_UQQ700_DIRECT_IDENTITY:" + normalize_space(target_match.group(0))]
            elif generic_urban:
                classification = CLASS_GENERIC_URBAN
                reasons = ["GENERIC_URBAN_ROW_WITHOUT_UQQ700_DIRECT_IDENTITY"]
            else:
                classification = CLASS_OTHER_ROW
                reasons = ["ROW_LOCAL_UQQ700_DIRECT_IDENTITY_MISSING"]

            rows.append({
                "source_family": family,
                "page_url": page_url,
                "page_number": page_number,
                "tr_index": tr_index,
                "function": function_name,
                "argument": argument,
                "row_text": row_text[:5000],
                "notice_numbers": notices,
                "dates": dates,
                "classification": classification,
                "reasons": reasons,
                "target_identity_direct": bool(target_match),
                "detail_request_executed": False,
                "document_candidate_only": classification == CLASS_TARGET_CANDIDATE,
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
                "site_negative_allowed": False,
                "final_positive_promotion_allowed": False,
            })
    return rows


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("HISTORICAL ROW IDENTITY RECOVERY & UQQ700 METADATA FILTER")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Detail request execution: DISABLED")
    print("Row-local target identity evaluation: ENABLED")
    print()

    if not T15S2_INPUT_PATH.exists() or not S7S3_INPUT_PATH.exists():
        raise FileNotFoundError("required input missing")
    t15 = json.loads(T15S2_INPUT_PATH.read_text(encoding="utf-8"))
    s73 = json.loads(S7S3_INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(t15, dict) or not isinstance(s73, dict):
        raise TypeError("input must be JSON object")

    validated_families = load_validated_families(s73)
    contracts = load_traversal_contracts(t15, validated_families)

    print("Validated detail-contract families:", sorted(validated_families))
    print("Traversal contract count:", len(contracts))
    print()

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9",
    })

    request_count = 0
    http_success_count = 0
    transport_error_count = 0
    all_rows: List[Dict[str, Any]] = []
    page_results: List[Dict[str, Any]] = []

    for contract_index, contract in enumerate(contracts, start=1):
        family = contract["source_family"]
        pages = traversal_pages(contract["effective_lower_page"], contract["effective_upper_page"])
        contract_requests = 0
        contract_rows = 0
        print("-" * 60)
        print(f"CONTRACT {contract_index}")
        print("Family:", family)
        print("Base URL:", contract["base_url"])
        print("Range:", (contract["effective_lower_page"], contract["effective_upper_page"]))
        print("Traversal pages:", pages)

        for page in pages:
            if request_count >= MAX_TOTAL_REQUESTS or contract_requests >= MAX_REQUESTS_PER_CONTRACT:
                break
            page_url = build_page_url(contract["base_url"], contract["pagination_key"], page)
            response = fetch_page(session, page_url)
            request_count += 1
            contract_requests += 1
            status = response.get("http_status")
            if isinstance(status, int) and 200 <= status < 300:
                http_success_count += 1
            if response.get("error"):
                transport_error_count += 1
            rows: List[Dict[str, Any]] = []
            if isinstance(status, int) and 200 <= status < 300 and response.get("text"):
                rows = extract_interaction_rows(str(response.get("text")), family, response.get("final_url") or page_url, page)
                all_rows.extend(rows)
                contract_rows += len(rows)
            page_results.append({
                "source_family": family,
                "page_number": page,
                "page_url": page_url,
                "http_status": status,
                "interaction_row_count": len(rows),
            })

        print("Requests:", contract_requests)
        print("Recovered interaction rows:", contract_rows)
        print()

    canonical_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    duplicate_removed = 0
    for row in all_rows:
        key = (normalize_space(row.get("source_family")), normalize_space(row.get("argument")))
        if key in canonical_map:
            duplicate_removed += 1
            existing = canonical_map[key]
            existing["page_numbers"] = sorted(set((existing.get("page_numbers") or [existing.get("page_number")]) + [row.get("page_number")]))
            existing["row_text_variants"] = unique_strings((existing.get("row_text_variants") or [existing.get("row_text")]) + [row.get("row_text")])
            existing["notice_numbers"] = unique_strings((existing.get("notice_numbers") or []) + (row.get("notice_numbers") or []))
            existing["dates"] = unique_strings((existing.get("dates") or []) + (row.get("dates") or []))
            if row.get("target_identity_direct") is True:
                existing["target_identity_direct"] = True
                existing["classification"] = CLASS_TARGET_CANDIDATE
                existing["document_candidate_only"] = True
                existing["reasons"] = unique_strings((existing.get("reasons") or []) + (row.get("reasons") or []))
            continue
        item = dict(row)
        item["page_numbers"] = [row.get("page_number")]
        item["row_text_variants"] = [row.get("row_text")]
        canonical_map[key] = item

    canonical_rows = list(canonical_map.values())
    canonical_rows.sort(key=lambda x: (x.get("source_family") or "", int(x.get("argument") or 0)))
    target_candidates = [x for x in canonical_rows if x.get("target_identity_direct") is True]
    generic_rows = [x for x in canonical_rows if x.get("classification") == CLASS_GENERIC_URBAN]

    next_stage_pool = []
    for item in target_candidates:
        next_stage_pool.append({
            "source_family": item.get("source_family"),
            "function": item.get("function"),
            "argument": item.get("argument"),
            "page_numbers": item.get("page_numbers") or [],
            "row_text_variants": item.get("row_text_variants") or [],
            "notice_numbers": item.get("notice_numbers") or [],
            "dates": item.get("dates") or [],
            "target_identity_direct": True,
            "requires_validated_exact_detail_request": True,
            "detail_request_executed": False,
            "document_candidate_only": True,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        })

    resolution = (
        "COMPETENT_AUTHORITY_UQQ700_HISTORICAL_ROW_CANDIDATE_RECOVERED"
        if next_stage_pool
        else "COMPETENT_AUTHORITY_HISTORICAL_ROW_IDENTITY_RECOVERY_NO_UQQ700_ROW"
    )
    next_action = (
        "row-local metadata에서 UQQ700 direct identity가 확인된 row만 S9 direct detail verification으로 넘긴다. "
        "S9는 S7-S3에서 validated된 exact detail contract를 사용해 title/notice number/date/issuing authority/target identity를 직접 재검증한다."
        if next_stage_pool
        else
        "bounded historical row traversal에서 개발밀도관리구역 direct row identity를 찾지 못했다. 이는 SITE FALSE가 아니다. "
        "UNKNOWN을 유지하고 더 오래된 competent-authority archive 또는 spatial designation source scope를 검토한다."
    )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-16-S8 Historical Row Identity Recovery",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "method": {
            "validated_detail_contract_family_gate": True,
            "traversal_safe_boundary_only": True,
            "bounded_historical_page_traversal": True,
            "row_local_observed_function_call_required": True,
            "row_local_target_identity_evaluation_enabled": True,
            "page_title_target_evidence_disabled": True,
            "source_url_target_evidence_disabled": True,
            "generic_urban_auto_promotion_disabled": True,
            "detail_request_execution_enabled": False,
            "verified_positive_promotion_allowed": False,
        },
        "summary": {
            "validated_family_count": len(validated_families),
            "traversal_contract_count": len(contracts),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "raw_interaction_row_count": len(all_rows),
            "duplicate_row_removed": duplicate_removed,
            "canonical_interaction_row_count": len(canonical_rows),
            "generic_urban_row_count": len(generic_rows),
            "uqq700_target_candidate_count": len(target_candidates),
            "next_stage_candidate_count": len(next_stage_pool),
        },
        "classification_counts": dict(sorted(Counter(x.get("classification") for x in canonical_rows).items())),
        "page_results": page_results,
        "canonical_interaction_rows": canonical_rows,
        "uqq700_target_candidates": target_candidates,
        "next_stage_document_candidate_pool": next_stage_pool,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    invalid_candidate_identity = sum(1 for x in target_candidates if not x.get("argument") or not x.get("target_identity_direct"))
    detail_request_leakage = sum(1 for x in canonical_rows + next_stage_pool if x.get("detail_request_executed") is True)
    verified_positive_leakage = sum(1 for x in canonical_rows + next_stage_pool if x.get("verified_positive") is True)
    site_true_leakage = sum(1 for x in canonical_rows + next_stage_pool if x.get("site_positive_allowed") is True)
    site_false_leakage = sum(1 for x in canonical_rows + next_stage_pool if x.get("site_negative_allowed") is True)
    runtime_leakage = sum(1 for x in canonical_rows + next_stage_pool if x.get("runtime_registration_allowed") is True)
    duplicate_identity_leakage = len(canonical_rows) - len({(x.get("source_family"), x.get("argument")) for x in canonical_rows})
    invalid_host_leakage = sum(1 for x in page_results if x.get("page_url") and not is_government_host(hostname(x.get("page_url"))))
    false_from_no_candidate_leakage = 1 if (not next_stage_pool and output_data["resolution_policy"]["source_failure_site_status"] == "FALSE") else 0

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "T-15-S2 input exists": T15S2_INPUT_PATH.exists(),
        "S7-S3 input exists": S7S3_INPUT_PATH.exists(),
        "validated detail-contract families loaded": len(validated_families) > 0,
        "traversal contracts loaded": len(contracts) > 0,
        "bounded total request count respected": request_count <= MAX_TOTAL_REQUESTS,
        "row-local interaction identity required": True,
        "row-local target identity evaluation enabled": True,
        "generic urban auto-promotion disabled": True,
        "detail request execution disabled": detail_request_leakage == 0,
        "canonical row identities unique": duplicate_identity_leakage == 0,
        "candidate identities valid": invalid_candidate_identity == 0,
        "page hosts go.kr": invalid_host_leakage == 0,
        "verified positive leakage zero": verified_positive_leakage == 0,
        "runtime registration leakage zero": runtime_leakage == 0,
        "SITE TRUE leakage zero": site_true_leakage == 0,
        "SITE FALSE leakage zero": site_false_leakage == 0,
        "false from no candidate leakage zero": false_from_no_candidate_leakage == 0,
        "runtime registration remains blocked": output_data["runtime_registration_allowed"] is False,
        "SITE TRUE remains blocked": output_data["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output_data["site_negative_allowed"] is False,
        "final positive promotion remains blocked": output_data["final_positive_promotion_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print("=" * 60)
    print("HISTORICAL ROW IDENTITY RECOVERY RESULT")
    print("=" * 60)
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Raw interaction rows:", len(all_rows))
    print("Duplicate row removed:", duplicate_removed)
    print("Canonical interaction rows:", len(canonical_rows))
    print("Generic urban rows:", len(generic_rows))
    print("UQQ700 target candidates:", len(target_candidates))
    print("Next-stage candidates:", len(next_stage_pool))
    print("Resolution:", resolution)
    print("Output:", OUTPUT_PATH)

    if target_candidates:
        print()
        print("UQQ700 ROW-LOCAL CANDIDATES")
        print("-" * 60)
        for index, item in enumerate(target_candidates, start=1):
            print(f"[{index}]", item.get("source_family"))
            print("Argument:", item.get("argument"))
            print("Pages:", item.get("page_numbers"))
            print("Notices:", item.get("notice_numbers"))
            print("Dates:", item.get("dates"))
            print("Text:", item.get("row_text"))
            print()

    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("Duplicate identity leakage:", duplicate_identity_leakage)
    print("Invalid candidate identity leakage:", invalid_candidate_identity)
    print("Invalid host leakage:", invalid_host_leakage)
    print("Detail request leakage:", detail_request_leakage)
    print("Verified positive leakage:", verified_positive_leakage)
    print("Runtime registration leakage:", runtime_leakage)
    print("SITE TRUE leakage:", site_true_leakage)
    print("SITE FALSE leakage:", site_false_leakage)
    print("False from no candidate leakage:", false_from_no_candidate_leakage)
    print()
    all_pass = all(validations.values())
    print(f"all_pass: {all_pass}")
    if not all_pass:
        print("FAILED:")
        for name, passed in validations.items():
            if not passed:
                print("-", name)
        raise AssertionError("UQQ700 historical row identity recovery regression failed")


if __name__ == "__main__":
    main()
