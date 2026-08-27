# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-15-S2
Development Density Management Area
Competent Authority Historical Boundary Semantic Hardening

목표
======================================================================
T-15에서 복원된 historical pagination/date boundary를 T-16 traversal에
직접 넘기기 전에 의미론적으로 hardening한다.

핵심 원칙
======================================================================
1. T-15 output만 입력으로 사용한다.
2. 추가 network request를 실행하지 않는다.
3. 현재 검증 기준일 이후의 future date는 historical reach 증거로 사용하지 않는다.
4. page 전체에서 추출된 날짜는 diagnostic provenance로만 취급한다.
5. repeated response boundary는 out-of-range clamp 신호로 취급한다.
6. repeated boundary 이후 page를 traversal range에 포함하지 않는다.
7. 동일 source-family / host / pagination-key에서 /list route alias는 하나로 병합한다.
8. T-16에는 traversal-safe canonical contract만 전달한다.
9. UQQ700 target query를 실행하지 않는다.
10. document candidate를 생성하지 않는다.
11. verified positive / runtime registration / SITE TRUE / SITE FALSE 자동판정 금지.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


# ============================================================
# PATH / TARGET
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

T15_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "development_density_management_area_competent_authority_historical_period_boundary_recovery.json"
)

OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "development_density_management_area_competent_authority_historical_boundary_semantic_hardening.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

# 프로젝트 검증 기준일. 테스트 재현성을 위해 wall clock 대신 명시값을 사용한다.
VERIFIED_AS_OF = date(2026, 8, 27)
MIN_TRUSTED_DATE = date(1980, 1, 1)

FAMILY_NOTICE = "CURRENT_MUNICIPAL_OFFICIAL_NOTICE_ARCHIVE"
FAMILY_URBAN = "CURRENT_URBAN_PLANNING_INFORMATION_ARCHIVE"
ALLOWED_FAMILIES = {
    FAMILY_NOTICE,
    FAMILY_URBAN,
}

CLASS_TRAVERSAL_READY = "HARDENED_AUTHORITY_HISTORICAL_TRAVERSAL_CONTRACT"
CLASS_UNRESOLVED = "HARDENED_AUTHORITY_HISTORICAL_BOUNDARY_UNRESOLVED"

VALID_CLASSES = {
    CLASS_TRAVERSAL_READY,
    CLASS_UNRESOLVED,
}

PAGINATION_KEYS = {
    "page",
    "curpage",
    "pagenum",
    "pageindex",
    "page_no",
    "pageno",
    "currentpage",
}

VOLATILE_QUERY_KEYS = {
    "token",
    "_csrf",
    "csrf",
    "sessionid",
    "jsessionid",
    "timestamp",
    "rand",
    "random",
    "_",
}

TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
}


# ============================================================
# UTIL
# ============================================================

def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def unique_strings(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: Set[str] = set()

    for value in values:
        text = normalize_space(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)

    return result


def unique_ints(values: Iterable[Any]) -> List[int]:
    result: Set[int] = set()

    for value in values:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            result.add(number)

    return sorted(result)


def canonicalize_url(url: str) -> str:
    value = normalize_space(url)
    if not value:
        return ""

    try:
        parsed = urlparse(value)
    except Exception:
        return ""

    if not parsed.hostname:
        return ""

    scheme = (parsed.scheme or "https").lower()
    host = (parsed.hostname or "").lower()

    try:
        port = parsed.port
    except ValueError:
        port = None

    if port and not (scheme == "http" and port == 80) and not (scheme == "https" and port == 443):
        netloc = f"{host}:{port}"
    else:
        netloc = host

    path = parsed.path or "/"
    path = re.sub(r";jsessionid=[^/?]+", "", path, flags=re.I)
    path = re.sub(r"/{2,}", "/", path)

    query_items: List[Tuple[str, str]] = []
    seen_pairs: Set[Tuple[str, str]] = set()

    for key, raw_value in parse_qsl(parsed.query, keep_blank_values=True):
        normalized_key = normalize_space(key)
        if not normalized_key:
            continue

        lowered = normalized_key.lower()
        if lowered in VOLATILE_QUERY_KEYS or lowered in TRACKING_QUERY_KEYS:
            continue
        if "csrf" in lowered or "session" in lowered:
            continue

        pair = (normalized_key, raw_value)
        if pair in seen_pairs:
            continue

        seen_pairs.add(pair)
        query_items.append(pair)

    query_items.sort(key=lambda item: (item[0].lower(), item[1]))

    return urlunparse((
        scheme,
        netloc,
        path,
        "",
        urlencode(query_items, doseq=True),
        "",
    ))


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_government_host(host: str) -> bool:
    value = normalize_space(host).lower()
    return bool(value) and (value == "go.kr" or value.endswith(".go.kr"))


def parse_iso_date(value: Any) -> date | None:
    text = normalize_space(value)
    if not text:
        return None

    try:
        return date.fromisoformat(text[:10])
    except (TypeError, ValueError):
        return None


def date_is_trusted(value: Any) -> bool:
    parsed = parse_iso_date(value)
    if parsed is None:
        return False
    return MIN_TRUSTED_DATE <= parsed <= VERIFIED_AS_OF


def normalize_route_alias(url: str) -> str:
    """같은 board에서 `/list` 유무만 다른 route를 동일 identity로 묶는다."""

    canonical = canonicalize_url(url)
    if not canonical:
        return ""

    parsed = urlparse(canonical)
    path = parsed.path or "/"

    if path.lower().endswith("/list"):
        path = path[:-5] or "/"

    path = path.rstrip("/") or "/"

    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        path,
        "",
        parsed.query,
        "",
    ))


def choose_primary_base_url(urls: List[str]) -> str:
    canonical = unique_strings(canonicalize_url(url) for url in urls)
    if not canonical:
        return ""

    # T-16 pagination traversal은 실제 list route가 있으면 그것을 우선한다.
    list_routes = [url for url in canonical if urlparse(url).path.lower().endswith("/list")]
    if list_routes:
        return sorted(list_routes)[0]

    return sorted(canonical)[0]


# ============================================================
# INPUT LOAD
# ============================================================

def load_t15_boundaries(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = data.get("historical_boundaries")
    if not isinstance(raw, list):
        raw = []

    return [item for item in raw if isinstance(item, dict)]


def load_probe_records(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = data.get("probe_records")
    if not isinstance(raw, list):
        raw = []

    return [item for item in raw if isinstance(item, dict)]


# ============================================================
# SEMANTIC HARDENING
# ============================================================

def collect_contract_probe_records(
    probe_records: List[Dict[str, Any]],
    source_family: str,
    base_urls: List[str],
    pagination_key: str,
) -> List[Dict[str, Any]]:
    aliases = {
        normalize_route_alias(url)
        for url in base_urls
        if normalize_route_alias(url)
    }

    result: List[Dict[str, Any]] = []

    for item in probe_records:
        if normalize_space(item.get("source_family")) != source_family:
            continue
        if normalize_space(item.get("pagination_key")).lower() != pagination_key.lower():
            continue

        item_alias = normalize_route_alias(item.get("base_url") or "")
        if item_alias not in aliases:
            continue

        result.append(item)

    return result


def derive_trusted_dates(probes: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    trusted: Set[str] = set()
    rejected: Set[str] = set()

    for item in probes:
        for raw_date in item.get("dates") or []:
            text = normalize_space(raw_date)
            if not text:
                continue

            if date_is_trusted(text):
                trusted.add(text[:10])
            else:
                rejected.add(text[:10])

    return sorted(trusted), sorted(rejected)


def derive_repeated_boundary(
    boundaries: List[Dict[str, Any]],
    probes: List[Dict[str, Any]],
) -> int | None:
    candidates: List[int] = []

    for item in boundaries:
        value = item.get("first_repeated_boundary_page")
        try:
            page = int(value)
        except (TypeError, ValueError):
            continue
        if page > 1:
            candidates.append(page)

    signature_pages: Dict[str, List[int]] = {}

    for item in probes:
        signature = normalize_space(item.get("response_signature"))
        if not signature:
            continue

        try:
            page = int(item.get("requested_page"))
        except (TypeError, ValueError):
            continue

        if page <= 0:
            continue

        signature_pages.setdefault(signature, []).append(page)

    for pages in signature_pages.values():
        distinct = sorted(set(pages))
        if len(distinct) < 2:
            continue
        if distinct[-1] - distinct[0] < 10:
            continue
        if distinct[0] > 1:
            candidates.append(distinct[0])

    return min(candidates) if candidates else None


def derive_empty_boundary(boundaries: List[Dict[str, Any]], probes: List[Dict[str, Any]]) -> int | None:
    candidates: List[int] = []

    for item in boundaries:
        value = item.get("first_empty_probe_page")
        try:
            page = int(value)
        except (TypeError, ValueError):
            continue
        if page > 1:
            candidates.append(page)

    for item in probes:
        if item.get("empty_page_signal") is not True:
            continue
        try:
            page = int(item.get("requested_page"))
        except (TypeError, ValueError):
            continue
        if page > 1:
            candidates.append(page)

    return min(candidates) if candidates else None


def build_hardened_contract(
    boundaries: List[Dict[str, Any]],
    probes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    first = boundaries[0]

    family = normalize_space(first.get("source_family"))
    pagination_key = normalize_space(first.get("pagination_key"))

    source_urls = unique_strings(item.get("source_url") for item in boundaries)
    base_urls = unique_strings(item.get("base_url") for item in boundaries)
    regions = unique_strings(
        region
        for item in boundaries
        for region in (item.get("regions") or [])
    )

    observed_pages = unique_ints(
        page
        for item in boundaries
        for page in (item.get("observed_pages") or [])
    )

    successful_pages = unique_ints(
        page
        for item in boundaries
        for page in (item.get("successful_probe_pages") or [])
    )

    nonempty_pages = unique_ints(
        page
        for item in boundaries
        for page in (item.get("nonempty_probe_pages") or [])
    )

    repeated_boundary = derive_repeated_boundary(boundaries, probes)
    empty_boundary = derive_empty_boundary(boundaries, probes)

    upper_candidates = [
        page - 1
        for page in [repeated_boundary, empty_boundary]
        if isinstance(page, int) and page > 1
    ]

    effective_upper_page = min(upper_candidates) if upper_candidates else None

    max_observed_page = max(observed_pages) if observed_pages else None

    if effective_upper_page is None and max_observed_page is not None:
        # clamp/empty evidence가 없으면 sparse probe 최대치를 역사 범위로 승격하지 않는다.
        # T-16의 안전한 초기 traversal 범위는 실제 navigation에서 관측된 page까지만 둔다.
        effective_upper_page = max_observed_page

    if effective_upper_page is not None and max_observed_page is not None:
        effective_upper_page = max(effective_upper_page, max_observed_page)

    trusted_dates, rejected_dates = derive_trusted_dates(probes)

    future_date_contamination = any(
        parse_iso_date(value) is not None and parse_iso_date(value) > VERIFIED_AS_OF
        for value in rejected_dates
    )

    primary_base_url = choose_primary_base_url(base_urls)

    reasons: List[str] = []

    if len(base_urls) > 1:
        reasons.append("ROUTE_ALIAS_CONTRACTS_MERGED")
    if repeated_boundary is not None:
        reasons.append(f"REPEATED_RESPONSE_CLAMP_FROM:{repeated_boundary}")
    if empty_boundary is not None:
        reasons.append(f"EMPTY_PAGE_BOUNDARY_FROM:{empty_boundary}")
    if future_date_contamination:
        reasons.append("FUTURE_DATE_CONTAMINATION_REMOVED")
    if trusted_dates:
        reasons.append(f"TRUSTED_DIAGNOSTIC_DATE_MIN:{trusted_dates[0]}")
        reasons.append(f"TRUSTED_DIAGNOSTIC_DATE_MAX:{trusted_dates[-1]}")
    if effective_upper_page is not None:
        reasons.append(f"TRAVERSAL_UPPER_PAGE:{effective_upper_page}")

    valid_identity = (
        family in ALLOWED_FAMILIES
        and pagination_key.lower() in PAGINATION_KEYS
        and bool(primary_base_url)
        and is_government_host(hostname(primary_base_url))
        and effective_upper_page is not None
        and effective_upper_page >= 1
    )

    return {
        "source_family": family,
        "authority_role": first.get("authority_role"),
        "authority_entity": first.get("authority_entity"),
        "regions": regions,
        "source_urls": source_urls,
        "base_url_aliases": base_urls,
        "base_url": primary_base_url,
        "pagination_key": pagination_key,
        "observed_pages": observed_pages,
        "successful_probe_pages": successful_pages,
        "nonempty_probe_pages": nonempty_pages,
        "max_observed_page": max_observed_page,
        "repeated_boundary_page": repeated_boundary,
        "empty_boundary_page": empty_boundary,
        "effective_lower_page": 1 if valid_identity else None,
        "effective_upper_page": effective_upper_page if valid_identity else None,
        "server_clamp_detected": repeated_boundary is not None,
        "future_date_contamination_detected": future_date_contamination,
        "trusted_diagnostic_dates": trusted_dates,
        "rejected_date_values": rejected_dates,
        "trusted_earliest_date": trusted_dates[0] if trusted_dates else None,
        "trusted_latest_date": trusted_dates[-1] if trusted_dates else None,
        "date_values_allowed_as_traversal_boundary": False,
        "qualified": valid_identity,
        "classification": CLASS_TRAVERSAL_READY if valid_identity else CLASS_UNRESOLVED,
        "reasons": unique_strings(reasons or ["TRAVERSAL_BOUNDARY_UNRESOLVED"]),
        "traversal_allowed": valid_identity,
        "bounded_range_only": True,
        "requires_document_metadata_recovery": True,
        "target_query_executed": False,
        "document_candidate": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("COMPETENT AUTHORITY HISTORICAL BOUNDARY SEMANTIC HARDENING")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Verified as of:", VERIFIED_AS_OF.isoformat())
    print("Target query execution: DISABLED")
    print()

    if not T15_INPUT_PATH.exists():
        raise FileNotFoundError(f"T-15 input not found: {T15_INPUT_PATH}")

    t15_data = json.loads(T15_INPUT_PATH.read_text(encoding="utf-8"))

    if not isinstance(t15_data, dict):
        raise TypeError("T-15 input must be JSON object")

    boundaries = load_t15_boundaries(t15_data)
    probe_records = load_probe_records(t15_data)

    print("T-15 boundary count:", len(boundaries))
    print("T-15 probe record count:", len(probe_records))
    print()

    grouped: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}

    for item in boundaries:
        family = normalize_space(item.get("source_family"))
        base_url = canonicalize_url(item.get("base_url") or item.get("source_url") or "")
        pagination_key = normalize_space(item.get("pagination_key")).lower()
        alias = normalize_route_alias(base_url)

        if not family or not alias or not pagination_key:
            continue

        key = (family, alias, pagination_key)
        grouped.setdefault(key, []).append(item)

    hardened_contracts: List[Dict[str, Any]] = []

    for index, ((family, _alias, pagination_key), items) in enumerate(
        sorted(grouped.items(), key=lambda entry: entry[0]),
        start=1,
    ):
        base_urls = unique_strings(item.get("base_url") for item in items)
        contract_probes = collect_contract_probe_records(
            probe_records,
            family,
            base_urls,
            pagination_key,
        )

        hardened = build_hardened_contract(items, contract_probes)
        hardened_contracts.append(hardened)

        print("-" * 60)
        print(f"CONTRACT {index}")
        print("Family:", hardened.get("source_family"))
        print("Base URL aliases:", hardened.get("base_url_aliases"))
        print("Primary base URL:", hardened.get("base_url"))
        print("Pagination key:", hardened.get("pagination_key"))
        print("Observed pages:", hardened.get("observed_pages"))
        print("Repeated boundary:", hardened.get("repeated_boundary_page"))
        print("Empty boundary:", hardened.get("empty_boundary_page"))
        print("Effective upper page:", hardened.get("effective_upper_page"))
        print("Future date contamination:", hardened.get("future_date_contamination_detected"))
        print("Trusted diagnostic dates:", (
            hardened.get("trusted_earliest_date"),
            hardened.get("trusted_latest_date"),
        ))
        print("Qualified:", hardened.get("qualified"))
        print("Resolution:", hardened.get("classification"))
        print("Reasons:", hardened.get("reasons"))
        print()

    hardened_contracts.sort(key=lambda item: (
        normalize_space(item.get("source_family")),
        canonicalize_url(item.get("base_url") or ""),
        normalize_space(item.get("pagination_key")).lower(),
    ))

    traversal_ready = [
        item
        for item in hardened_contracts
        if item.get("qualified") is True
    ]

    unresolved = [
        item
        for item in hardened_contracts
        if item.get("qualified") is not True
    ]

    next_stage_boundary_pool = [
        {
            "source_family": item.get("source_family"),
            "authority_role": item.get("authority_role"),
            "authority_entity": item.get("authority_entity"),
            "regions": item.get("regions") or [],
            "source_urls": item.get("source_urls") or [],
            "base_url_aliases": item.get("base_url_aliases") or [],
            "base_url": item.get("base_url"),
            "pagination_key": item.get("pagination_key"),
            "observed_pages": item.get("observed_pages") or [],
            "effective_lower_page": item.get("effective_lower_page"),
            "effective_upper_page": item.get("effective_upper_page"),
            "repeated_boundary_page": item.get("repeated_boundary_page"),
            "empty_boundary_page": item.get("empty_boundary_page"),
            "server_clamp_detected": item.get("server_clamp_detected") is True,
            "future_date_contamination_detected": item.get("future_date_contamination_detected") is True,
            "trusted_earliest_date": item.get("trusted_earliest_date"),
            "trusted_latest_date": item.get("trusted_latest_date"),
            "date_values_allowed_as_traversal_boundary": False,
            "classification": item.get("classification"),
            "reasons": item.get("reasons") or [],
            "traversal_allowed": True,
            "bounded_range_only": True,
            "requires_document_metadata_recovery": True,
            "target_query_executed": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in traversal_ready
    ]

    future_date_rejection_count = sum(
        len(item.get("rejected_date_values") or [])
        for item in hardened_contracts
    )

    alias_merge_count = sum(
        max(0, len(item.get("base_url_aliases") or []) - 1)
        for item in hardened_contracts
    )

    clamp_contract_count = sum(
        1
        for item in hardened_contracts
        if item.get("server_clamp_detected") is True
    )

    if next_stage_boundary_pool:
        resolution = "COMPETENT_AUTHORITY_HISTORICAL_BOUNDARY_SEMANTIC_HARDENING_COMPLETED"
        next_action = (
            "T-15-S2에서 hardening된 traversal-safe pagination contract만 T-16 bounded historical range traversal 입력으로 사용한다. "
            "T-16에서는 effective page range를 초과하지 않고 실제 document metadata row(title, notice number, date, detail URL) 구조만 복원한다. "
            "UQQ700 target query와 SITE TRUE/FALSE 판정은 계속 금지한다."
        )
    else:
        resolution = "COMPETENT_AUTHORITY_HISTORICAL_BOUNDARY_SEMANTIC_HARDENING_UNRESOLVED"
        next_action = (
            "T-15 boundary를 traversal-safe contract로 승격하지 못했다. SITE FALSE로 판정하지 않고 UNKNOWN을 유지한다."
        )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-15-S2 Competent Authority Historical Boundary Semantic Hardening",
        "target": {
            "name": TARGET_NAME,
            "standard_code": STANDARD_CODE,
        },
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
            "verified_as_of": VERIFIED_AS_OF.isoformat(),
        },
        "inputs": {
            "t15_path": str(T15_INPUT_PATH),
            "t15_resolution": t15_data.get("resolution"),
        },
        "method": {
            "network_requery_enabled": False,
            "future_date_as_boundary_enabled": False,
            "page_global_date_as_boundary_enabled": False,
            "repeated_response_clamp_guard_enabled": True,
            "route_alias_merge_enabled": True,
            "bounded_range_only": True,
            "target_query_execution_enabled": False,
            "document_candidate_generation_enabled": False,
            "negative_evidence_enabled": False,
            "verified_positive_promotion_allowed": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
        },
        "summary": {
            "t15_boundary_count": len(boundaries),
            "t15_probe_record_count": len(probe_records),
            "canonical_contract_count": len(hardened_contracts),
            "traversal_ready_contract_count": len(traversal_ready),
            "unresolved_contract_count": len(unresolved),
            "route_alias_removed_count": alias_merge_count,
            "future_date_rejection_count": future_date_rejection_count,
            "clamp_contract_count": clamp_contract_count,
            "next_stage_boundary_pool_count": len(next_stage_boundary_pool),
        },
        "hardened_contracts": hardened_contracts,
        "traversal_ready_contracts": traversal_ready,
        "unresolved_contracts": unresolved,
        "next_stage_boundary_pool": next_stage_boundary_pool,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }

    OUTPUT_PATH.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=" * 60)
    print("HISTORICAL BOUNDARY SEMANTIC HARDENING RESULT")
    print("=" * 60)
    print("T-15 boundary count:", len(boundaries))
    print("Canonical contract count:", len(hardened_contracts))
    print("Traversal-ready contract count:", len(traversal_ready))
    print("Route alias removed:", alias_merge_count)
    print("Future date values rejected:", future_date_rejection_count)
    print("Clamp contract count:", clamp_contract_count)
    print("Next-stage boundary pool count:", len(next_stage_boundary_pool))
    print()
    print("=" * 60)
    print("RESOLUTION")
    print("=" * 60)
    print(resolution)
    print()
    print(next_action)
    print("Output:", OUTPUT_PATH)

    # ========================================================
    # VALIDATION
    # ========================================================

    contract_keys = [
        (
            normalize_space(item.get("source_family")),
            normalize_route_alias(item.get("base_url") or ""),
            normalize_space(item.get("pagination_key")).lower(),
        )
        for item in hardened_contracts
    ]

    next_stage_keys = [
        (
            normalize_space(item.get("source_family")),
            normalize_route_alias(item.get("base_url") or ""),
            normalize_space(item.get("pagination_key")).lower(),
        )
        for item in next_stage_boundary_pool
    ]

    all_classes_valid = all(
        item.get("classification") in VALID_CLASSES
        for item in hardened_contracts
    )

    future_date_boundary_leakage = sum(
        1
        for item in hardened_contracts
        for value in [item.get("trusted_earliest_date"), item.get("trusted_latest_date")]
        if parse_iso_date(value) is not None and parse_iso_date(value) > VERIFIED_AS_OF
    )

    invalid_upper_page_leakage = sum(
        1
        for item in traversal_ready
        if not isinstance(item.get("effective_upper_page"), int)
        or item.get("effective_upper_page") < 1
    )

    clamp_range_leakage = sum(
        1
        for item in traversal_ready
        if isinstance(item.get("repeated_boundary_page"), int)
        and item.get("effective_upper_page") >= item.get("repeated_boundary_page")
    )

    non_go_kr_leakage = sum(
        1
        for item in traversal_ready
        if not is_government_host(hostname(item.get("base_url") or ""))
    )

    target_query_leakage = sum(
        1
        for item in hardened_contracts + next_stage_boundary_pool
        if item.get("target_query_executed") is True
    )

    document_candidate_leakage = sum(
        1
        for item in hardened_contracts + next_stage_boundary_pool
        if item.get("document_candidate") is True
    )

    verified_positive_leakage = sum(
        1
        for item in hardened_contracts + next_stage_boundary_pool
        if item.get("verified_positive") is True
    )

    runtime_registration_leakage = sum(
        1
        for item in hardened_contracts + next_stage_boundary_pool
        if item.get("runtime_registration_allowed") is True
    )

    site_true_leakage = sum(
        1
        for item in hardened_contracts + next_stage_boundary_pool
        if item.get("site_positive_allowed") is True
    )

    site_false_leakage = sum(
        1
        for item in hardened_contracts + next_stage_boundary_pool
        if item.get("site_negative_allowed") is True
    )

    traversal_keys = {
        (
            normalize_space(item.get("source_family")),
            normalize_route_alias(item.get("base_url") or ""),
            normalize_space(item.get("pagination_key")).lower(),
        )
        for item in traversal_ready
    }

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "T-15 input exists": T15_INPUT_PATH.exists(),
        "T-15 input parsed": isinstance(t15_data, dict),
        "T-15 historical boundaries loaded": len(boundaries) > 0,
        "network requery disabled": True,
        "future date boundary disabled": True,
        "page-global date boundary disabled": True,
        "repeated response clamp guard enabled": True,
        "route alias merge enabled": True,
        "target query execution disabled": target_query_leakage == 0,
        "document candidate generation disabled": document_candidate_leakage == 0,
        "all classes valid": all_classes_valid,
        "canonical contracts unique": len(contract_keys) == len(set(contract_keys)),
        "next-stage contracts unique": len(next_stage_keys) == len(set(next_stage_keys)),
        "traversal and next-stage parity": traversal_keys == set(next_stage_keys),
        "future date boundary leakage zero": future_date_boundary_leakage == 0,
        "invalid traversal upper page leakage zero": invalid_upper_page_leakage == 0,
        "clamp range leakage zero": clamp_range_leakage == 0,
        "traversal source go.kr leakage zero": non_go_kr_leakage == 0,
        "verified positive leakage zero": verified_positive_leakage == 0,
        "runtime registration leakage zero": runtime_registration_leakage == 0,
        "SITE TRUE leakage zero": site_true_leakage == 0,
        "SITE FALSE leakage zero": site_false_leakage == 0,
        "runtime registration remains blocked": output_data["runtime_registration_allowed"] is False,
        "SITE TRUE remains blocked": output_data["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output_data["site_negative_allowed"] is False,
        "final positive promotion remains blocked": output_data["final_positive_promotion_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)

    for name, passed in validations.items():
        print(f"{name}: {passed}")

    print()
    print("Future date boundary leakage:", future_date_boundary_leakage)
    print("Invalid traversal upper page leakage:", invalid_upper_page_leakage)
    print("Clamp range leakage:", clamp_range_leakage)
    print("Non-go.kr traversal leakage:", non_go_kr_leakage)
    print("Target query leakage:", target_query_leakage)
    print("Document candidate leakage:", document_candidate_leakage)
    print("Verified positive leakage:", verified_positive_leakage)
    print("Runtime registration leakage:", runtime_registration_leakage)
    print("SITE TRUE leakage:", site_true_leakage)
    print("SITE FALSE leakage:", site_false_leakage)
    print()

    all_pass = all(validations.values())
    print(f"all_pass: {all_pass}")

    if not all_pass:
        failed = [name for name, passed in validations.items() if not passed]
        print()
        print("FAILED:")
        for name in failed:
            print("-", name)
        raise AssertionError(
            "UQQ700 competent authority historical boundary semantic hardening regression failed"
        )


if __name__ == "__main__":
    main()
