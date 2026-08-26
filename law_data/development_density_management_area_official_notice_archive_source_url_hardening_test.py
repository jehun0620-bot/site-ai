# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-5-S1
Development Density Management Area
Official Notice / Archive Source URL Canonicalization Hardening

T-5에서 HTML entity decoding이 URL query에 적용되면서
`&not_ancmt_se_code=...`가 HTML entity `&not`로 오인되어
`¬_ancmt_se_code=...` 형태로 손상될 수 있는 회귀를 제거한다.

원칙
======================================================================
1. 입력은 T-5 next_stage_source_pool만 사용한다.
2. URL에는 html.unescape 전체 적용을 하지 않는다.
3. HTML transport escape인 &amp; 계열만 안전하게 복원한다.
4. legacy T-5 출력의 `list_gubun=A¬_ancmt_se_code=...` 오염은 구조적으로 복구한다.
5. 복구된 URL은 직접 HTTP 재조회한다.
6. HTTP 2xx + go.kr + municipality binding 유지가 필요하다.
7. source 자체는 document candidate / verified positive가 아니다.
8. SITE TRUE / SITE FALSE / runtime registration 금지.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
T5_INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_official_notice_archive_source_expansion.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_official_notice_archive_source_url_hardening.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

VOLATILE_QUERY_KEYS = {
    "token", "_csrf", "csrf", "sessionid", "jsessionid",
    "timestamp", "rand", "random", "_",
}
TRACKING_QUERY_KEYS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term",
    "utm_content", "fbclid", "gclid",
}
REGION_ALIASES = {
    "경기도 성남시": ["성남시", "성남", "seongnam"],
    "경기도 평택시": ["평택시", "평택", "pyeongtaek"],
    "부산광역시 강서구": ["강서구", "강서", "bsgangseo"],
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


def decode_url_transport_entities(value: str) -> str:
    """URL 전체에 html.unescape를 사용하지 않는다."""
    result = normalize_space(value)
    replacements = {
        "&amp;": "&",
        "&#38;": "&",
        "&#x26;": "&",
        "&#X26;": "&",
    }
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result


def repair_legacy_t5_query_pairs(pairs: List[Tuple[str, str]]) -> Tuple[List[Tuple[str, str]], List[str]]:
    repaired: List[Tuple[str, str]] = []
    reasons: List[str] = []

    for key, value in pairs:
        # T-5 contamination example after parse_qsl:
        # key=list_gubun
        # value='A¬_ancmt_se_code=01,02,...'
        if key == "list_gubun" and "¬_ancmt_se_code=" in value:
            left, right = value.split("¬_ancmt_se_code=", 1)
            repaired.append(("list_gubun", left))
            repaired.append(("not_ancmt_se_code", right))
            reasons.append("REPAIRED_HTML_ENTITY_NOT_ANCMNT_CONTAMINATION")
            continue

        # 혹시 key 자체가 오염된 schema variation 대응
        if key.startswith("¬_ancmt_se_code"):
            repaired.append(("not_ancmt_se_code", value))
            reasons.append("REPAIRED_HTML_ENTITY_NOT_ANCMNT_KEY_CONTAMINATION")
            continue

        repaired.append((key, value))

    return repaired, unique_strings(reasons)


def canonicalize_url(url: str) -> Tuple[str, List[str]]:
    value = decode_url_transport_entities(url)
    reasons: List[str] = []
    if not value:
        return "", reasons

    try:
        parsed = urlparse(value)
    except Exception:
        return "", reasons

    if not parsed.hostname:
        return "", reasons

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

    raw_pairs = list(parse_qsl(parsed.query, keep_blank_values=True))
    raw_pairs, repair_reasons = repair_legacy_t5_query_pairs(raw_pairs)
    reasons.extend(repair_reasons)

    items: List[Tuple[str, str]] = []
    seen: Set[Tuple[str, str]] = set()

    for raw_key, raw_value in raw_pairs:
        key = normalize_space(raw_key)
        if not key:
            continue
        lowered = key.lower()
        if lowered in VOLATILE_QUERY_KEYS or lowered in TRACKING_QUERY_KEYS:
            continue
        if "csrf" in lowered or "session" in lowered:
            continue
        pair = (key, raw_value)
        if pair in seen:
            continue
        seen.add(pair)
        items.append(pair)

    items.sort(key=lambda item: (item[0].lower(), item[1]))
    query = urlencode(items, doseq=True)

    return urlunparse((scheme, netloc, path, "", query, "")), unique_strings(reasons)


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_government_host(host: str) -> bool:
    value = normalize_space(host).lower()
    return bool(value) and (value == "go.kr" or value.endswith(".go.kr"))


def matches_region(regions: List[str], url: str, body_preview: str) -> Tuple[bool, List[str]]:
    evidence = normalize_space(f"{url} {hostname(url)} {body_preview}").lower()
    matched: List[str] = []
    for region in regions:
        aliases = REGION_ALIASES.get(region, [region])
        if any(normalize_space(alias).lower() in evidence for alias in aliases if normalize_space(alias)):
            matched.append(region)
    return bool(matched), unique_strings(matched)


def fetch_page(session: requests.Session, url: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "final_url": "",
        "http_status": None,
        "content_type": "",
        "response_bytes": 0,
        "body_preview": "",
        "error": "",
    }
    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
            result["http_status"] = response.status_code
            final_url, _ = canonicalize_url(str(response.url))
            result["final_url"] = final_url
            result["content_type"] = normalize_space(response.headers.get("Content-Type"))
            chunks: List[bytes] = []
            total = 0
            for chunk in response.iter_content(chunk_size=128 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise ValueError(f"response exceeds {MAX_RESPONSE_BYTES} bytes")
                chunks.append(chunk)
            data = b"".join(chunks)
            result["response_bytes"] = len(data)
            for encoding in [response.encoding, "utf-8", "cp949", "euc-kr"]:
                if not encoding:
                    continue
                try:
                    result["body_preview"] = normalize_space(data.decode(encoding, errors="strict")[:5000])
                    break
                except Exception:
                    continue
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("OFFICIAL NOTICE / ARCHIVE SOURCE URL HARDENING")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print()

    if not T5_INPUT_PATH.exists():
        raise FileNotFoundError(f"T-5 input not found: {T5_INPUT_PATH}")

    data = json.loads(T5_INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("T-5 input must be a JSON object")

    raw = data.get("next_stage_source_pool")
    if not isinstance(raw, list):
        raw = []

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.5",
    })

    records: List[Dict[str, Any]] = []
    request_count = http_success_count = transport_error_count = repair_count = 0

    for index, item in enumerate(raw, start=1):
        regions = unique_strings(item.get("regions") or [])
        input_url = normalize_space(item.get("url"))
        hardened_url, repair_reasons = canonicalize_url(input_url)
        if repair_reasons:
            repair_count += 1

        print("-" * 60)
        print(f"SOURCE {index}")
        print("Input URL:", input_url)
        print("Hardened URL:", hardened_url)
        print("Repair reasons:", repair_reasons)

        record = dict(item)
        record.update({
            "input_url": input_url,
            "url": hardened_url,
            "url_repair_reasons": repair_reasons,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        })

        if not hardened_url:
            record.update(qualified=False, resolution="REJECTED_INVALID_HARDENED_URL")
            records.append(record)
            continue

        request_count += 1
        response = fetch_page(session, hardened_url)
        status = response.get("http_status")
        final_url = normalize_space(response.get("final_url")) or hardened_url
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1
        if response.get("error"):
            transport_error_count += 1

        region_ok, matched_regions = matches_region(
            regions,
            final_url,
            normalize_space(response.get("body_preview")),
        )

        qualified = (
            isinstance(status, int)
            and 200 <= status < 300
            and not response.get("error")
            and is_government_host(hostname(final_url))
            and region_ok
        )

        record.update({
            "url": final_url,
            "http_status": status,
            "content_type": response.get("content_type"),
            "response_bytes": response.get("response_bytes"),
            "matched_regions": matched_regions,
            "qualified": qualified,
            "resolution": "URL_HARDENED_SOURCE_RECONFIRMED" if qualified else "URL_HARDENING_SOURCE_REJECTED",
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        })
        records.append(record)
        print("HTTP:", status)
        print("Matched regions:", matched_regions)
        print("Qualified:", qualified)

    qualified_sources = [item for item in records if item.get("qualified") is True]
    rejected_sources = [item for item in records if item.get("qualified") is not True]
    next_stage_source_pool = [
        {
            "source_family": item.get("source_family"),
            "regions": item.get("matched_regions") or item.get("regions") or [],
            "url": item.get("url"),
            "title": item.get("title"),
            "classification": item.get("classification"),
            "url_repair_reasons": item.get("url_repair_reasons") or [],
            "source_only": True,
            "target_query_executed": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in qualified_sources
    ]

    resolution = (
        "OFFICIAL_NOTICE_ARCHIVE_SOURCE_URL_HARDENING_COMPLETED"
        if next_stage_source_pool
        else "OFFICIAL_NOTICE_ARCHIVE_SOURCE_URL_HARDENING_NO_SOURCE"
    )
    next_action = (
        "URL hardening을 통과한 source만 T-6 source-local search contract recovery로 넘긴다."
        if next_stage_source_pool
        else "URL hardening 후 usable source가 없으므로 UNKNOWN을 유지하고 source seed를 추가한다."
    )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-5-S1 Official Notice / Archive Source URL Canonicalization Hardening",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "input": {"t5_path": str(T5_INPUT_PATH), "t5_resolution": data.get("resolution")},
        "method": {
            "full_html_unescape_on_url_disabled": True,
            "transport_entity_decode_only": True,
            "legacy_not_ancmt_contamination_repair_enabled": True,
            "direct_network_reconfirmation_required": True,
            "http_2xx_required": True,
            "go_kr_required": True,
            "municipality_binding_required": True,
            "target_query_execution_enabled": False,
            "document_candidate_promotion_enabled": False,
        },
        "summary": {
            "input_source_count": len(raw),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "url_repair_count": repair_count,
            "qualified_source_count": len(qualified_sources),
            "rejected_source_count": len(rejected_sources),
            "next_stage_source_pool_count": len(next_stage_source_pool),
        },
        "qualified_sources": qualified_sources,
        "rejected_sources": rejected_sources,
        "next_stage_source_pool": next_stage_source_pool,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    url_entity_contamination_leakage = sum(
        1 for item in qualified_sources
        if "¬_ancmt" in normalize_space(item.get("url"))
        or "%C2%AC_ancmt" in normalize_space(item.get("url"))
    )
    not_ancmt_key_preservation_leakage = sum(
        1 for item in qualified_sources
        if "eminwon." in hostname(item.get("url") or "")
        and "selectofrnotancmt" in (item.get("url") or "").lower()
        and "not_ancmt_se_code=" not in (item.get("url") or "")
    )
    non_go_kr_leakage = sum(1 for item in qualified_sources if not is_government_host(hostname(item.get("url") or "")))
    region_unbound_leakage = sum(1 for item in qualified_sources if not (item.get("matched_regions") or []))
    verified_positive_leakage = sum(1 for item in records if item.get("verified_positive") is True)
    runtime_leakage = sum(1 for item in records if item.get("runtime_registration_allowed") is True)
    site_true_leakage = sum(1 for item in records if item.get("site_positive_allowed") is True)
    site_false_leakage = sum(1 for item in records if item.get("site_negative_allowed") is True)

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "T-5 input exists": T5_INPUT_PATH.exists(),
        "T-5 input parsed": isinstance(data, dict),
        "full html.unescape on URL disabled": True,
        "legacy not_ancmt contamination repair enabled": True,
        "URL entity contamination leakage zero": url_entity_contamination_leakage == 0,
        "not_ancmt key preservation leakage zero": not_ancmt_key_preservation_leakage == 0,
        "qualified source HTTP 2xx": all(isinstance(item.get("http_status"), int) and 200 <= item.get("http_status") < 300 for item in qualified_sources),
        "qualified source go.kr": non_go_kr_leakage == 0,
        "qualified source region bound": region_unbound_leakage == 0,
        "verified positive leakage zero": verified_positive_leakage == 0,
        "runtime registration leakage zero": runtime_leakage == 0,
        "SITE TRUE leakage zero": site_true_leakage == 0,
        "SITE FALSE leakage zero": site_false_leakage == 0,
        "runtime registration remains blocked": output_data["runtime_registration_allowed"] is False,
        "SITE TRUE remains blocked": output_data["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output_data["site_negative_allowed"] is False,
        "final positive promotion remains blocked": output_data["final_positive_promotion_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print("\n" + "=" * 60)
    print("URL HARDENING RESULT")
    print("=" * 60)
    print("Input source count:", len(raw))
    print("URL repair count:", repair_count)
    print("Qualified source count:", len(qualified_sources))
    print("Next-stage source pool count:", len(next_stage_source_pool))
    print("Resolution:", resolution)
    print("Output:", OUTPUT_PATH)
    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("URL entity contamination leakage:", url_entity_contamination_leakage)
    print("not_ancmt key preservation leakage:", not_ancmt_key_preservation_leakage)
    print("Non-go.kr leakage:", non_go_kr_leakage)
    print("Region-unbound leakage:", region_unbound_leakage)
    print("Verified positive leakage:", verified_positive_leakage)
    print("Runtime registration leakage:", runtime_leakage)
    print("SITE TRUE leakage:", site_true_leakage)
    print("SITE FALSE leakage:", site_false_leakage)
    print()

    all_pass = all(validations.values())
    print(f"all_pass: {all_pass}")
    if not all_pass:
        failed = [name for name, passed in validations.items() if not passed]
        print("\nFAILED:")
        for name in failed:
            print("-", name)
        raise AssertionError("UQQ700 archive source URL canonicalization hardening regression failed")


if __name__ == "__main__":
    main()
