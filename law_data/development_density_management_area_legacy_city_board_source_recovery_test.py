# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-17
Development Density Management Area
Legacy Seongnam City-Board Source Recovery

Goal:
Revalidate previously rejected legacy Seongnam city/.../bbsList.do board sources using live HTTP.
Do not execute UQQ700 target queries and do not promote documents. Recover only source identity.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_legacy_city_board_source_recovery.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

SEEDS = [
    {
        "source_family": "LEGACY_SEONGNAM_URBAN_PLANNING_NOTICE_BOARD",
        "regions": ["경기도 성남시"],
        "authority": "성남시장",
        "url": "https://www.seongnam.go.kr/city/1000818/30278/bbsList.do",
        "role": "URBAN_PLANNING_NOTICE_BOARD",
    },
    {
        "source_family": "LEGACY_SEONGNAM_MUNICIPAL_GAZETTE_BOARD",
        "regions": ["경기도 성남시"],
        "authority": "성남시장",
        "url": "https://www.seongnam.go.kr/city/1000063/30009/bbsList.do",
        "role": "MUNICIPAL_GAZETTE_BOARD",
    },
]

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>", re.S)

URBAN_MARKERS = [
    "지구단위계획",
    "도시관리계획",
    "도시계획",
    "고시/공고",
    "고시 공고",
]
GAZETTE_MARKERS = [
    "성남시보",
    "시보",
    "고 시",
    "고시",
    "공 고",
    "공고",
]
REGION_MARKERS = ["성남시", "성남"]


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def strip_html(value: str) -> str:
    return normalize_space(TAG_RE.sub(" ", value or ""))


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_government_host(host: str) -> bool:
    return bool(host) and (host == "go.kr" or host.endswith(".go.kr"))


def fetch(session: requests.Session, url: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "http_status": None,
        "final_url": "",
        "text": "",
        "error": "",
        "response_bytes": 0,
    }
    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
            result["http_status"] = response.status_code
            result["final_url"] = str(response.url)
            chunks: List[bytes] = []
            total = 0
            for chunk in response.iter_content(128 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise ValueError("response exceeds maximum size")
                chunks.append(chunk)
            raw = b"".join(chunks)
            result["response_bytes"] = len(raw)
            encodings = [response.encoding, "utf-8", "cp949", "euc-kr"]
            for encoding in encodings:
                if not encoding:
                    continue
                try:
                    result["text"] = raw.decode(encoding)
                    break
                except Exception:
                    continue
            if not result["text"]:
                result["text"] = raw.decode("utf-8", errors="replace")
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def classify(seed: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
    status = response.get("http_status")
    final_url = normalize_space(response.get("final_url")) or seed["url"]
    text = normalize_space(response.get("text"))
    title_match = TITLE_RE.search(response.get("text") or "")
    title = strip_html(title_match.group(1)) if title_match else ""
    evidence = normalize_space(f"{title} {text[:120000]} {final_url}")
    reasons: List[str] = []

    if not (isinstance(status, int) and 200 <= status < 300):
        return {
            "qualified": False,
            "classification": "REJECTED_LEGACY_CITY_BOARD_HTTP_FAILURE",
            "title": title,
            "final_url": final_url,
            "reasons": ["HTTP_NON_2XX"],
        }

    if not is_government_host(hostname(final_url)):
        return {
            "qualified": False,
            "classification": "REJECTED_LEGACY_CITY_BOARD_NON_OFFICIAL",
            "title": title,
            "final_url": final_url,
            "reasons": ["FINAL_HOST_NOT_GO_KR"],
        }

    if not any(marker in evidence for marker in REGION_MARKERS):
        return {
            "qualified": False,
            "classification": "REJECTED_LEGACY_CITY_BOARD_REGION_UNBOUND",
            "title": title,
            "final_url": final_url,
            "reasons": ["SEONGNAM_REGION_IDENTITY_MISSING"],
        }
    reasons.append("REGION_BOUND:경기도 성남시")

    role = seed["role"]
    if role == "URBAN_PLANNING_NOTICE_BOARD":
        matches = [marker for marker in URBAN_MARKERS if marker in evidence]
        if not matches:
            return {
                "qualified": False,
                "classification": "REJECTED_LEGACY_CITY_BOARD_ROLE_WEAK",
                "title": title,
                "final_url": final_url,
                "reasons": ["URBAN_BOARD_ROLE_EVIDENCE_MISSING"],
            }
        reasons.extend(f"URBAN_BOARD_MARKER:{marker}" for marker in matches[:6])
        classification = "QUALIFIED_LEGACY_SEONGNAM_URBAN_PLANNING_NOTICE_BOARD"
    else:
        matches = [marker for marker in GAZETTE_MARKERS if marker in evidence]
        if not matches:
            return {
                "qualified": False,
                "classification": "REJECTED_LEGACY_CITY_BOARD_ROLE_WEAK",
                "title": title,
                "final_url": final_url,
                "reasons": ["GAZETTE_BOARD_ROLE_EVIDENCE_MISSING"],
            }
        reasons.extend(f"GAZETTE_BOARD_MARKER:{marker}" for marker in matches[:6])
        classification = "QUALIFIED_LEGACY_SEONGNAM_MUNICIPAL_GAZETTE_BOARD"

    return {
        "qualified": True,
        "classification": classification,
        "title": title,
        "final_url": final_url,
        "reasons": reasons,
    }


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("LEGACY SEONGNAM CITY-BOARD SOURCE RECOVERY")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Target query execution: DISABLED")
    print("Document candidate promotion: DISABLED")
    print()

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept-Language": "ko-KR,ko;q=0.9",
    })

    records: List[Dict[str, Any]] = []
    request_count = 0
    http_success_count = 0
    transport_error_count = 0

    for index, seed in enumerate(SEEDS, start=1):
        print("-" * 60)
        print("SOURCE", index)
        print("Family:", seed["source_family"])
        print("URL:", seed["url"])

        response = fetch(session, seed["url"])
        request_count += 1
        status = response.get("http_status")
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1
        if response.get("error"):
            transport_error_count += 1

        result = classify(seed, response)
        record = {
            **seed,
            "http_status": status,
            "final_url": result["final_url"],
            "title": result["title"],
            "response_bytes": response.get("response_bytes"),
            "qualified": result["qualified"],
            "classification": result["classification"],
            "reasons": result["reasons"],
            "target_query_executed": False,
            "document_candidate_generated": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        records.append(record)

        print("HTTP:", status)
        print("Final URL:", record["final_url"])
        print("Title:", record["title"])
        print("Qualified:", record["qualified"])
        print("Resolution:", record["classification"])
        print("Reasons:", record["reasons"])

    qualified = [item for item in records if item.get("qualified") is True]
    next_stage = [
        {
            "source_family": item["source_family"],
            "regions": item["regions"],
            "authority": item["authority"],
            "url": item["final_url"],
            "title": item["title"],
            "role": item["role"],
            "classification": item["classification"],
            "reasons": item["reasons"],
            "requires_search_contract_recovery": True,
            "target_query_executed": False,
            "document_candidate_generated": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in qualified
    ]

    resolution = (
        "LEGACY_SEONGNAM_CITY_BOARD_SOURCE_RECOVERY_COMPLETED"
        if qualified
        else "LEGACY_SEONGNAM_CITY_BOARD_SOURCE_RECOVERY_NO_SOURCE"
    )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-17 Legacy Seongnam City-Board Source Recovery",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "method": {
            "previous_404_cache_ignored": True,
            "live_http_revalidation_enabled": True,
            "target_query_execution_enabled": False,
            "document_candidate_generation_enabled": False,
            "competent_authority_scope_preserved": True,
        },
        "summary": {
            "seed_count": len(SEEDS),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "qualified_source_count": len(qualified),
            "next_stage_source_pool_count": len(next_stage),
        },
        "source_records": records,
        "qualified_sources": qualified,
        "next_stage_source_pool": next_stage,
        "resolution": resolution,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    duplicate_urls = len(next_stage) - len({item["url"] for item in next_stage})
    non_go_kr = sum(1 for item in qualified if not is_government_host(hostname(item["final_url"])))
    unsafe = sum(
        1 for item in records
        if item.get("verified_positive") is True
        or item.get("runtime_registration_allowed") is True
        or item.get("site_positive_allowed") is True
        or item.get("site_negative_allowed") is True
        or item.get("final_positive_promotion_allowed") is True
        or item.get("target_query_executed") is True
        or item.get("document_candidate_generated") is True
    )

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "legacy city-board seeds present": len(SEEDS) == 2,
        "live HTTP revalidation enabled": request_count == len(SEEDS),
        "target query execution disabled": all(item["target_query_executed"] is False for item in records),
        "document candidate generation disabled": all(item["document_candidate_generated"] is False for item in records),
        "qualified URLs unique": duplicate_urls == 0,
        "qualified go.kr leakage zero": non_go_kr == 0,
        "unsafe promotion leakage zero": unsafe == 0,
        "runtime registration remains blocked": output_data["runtime_registration_allowed"] is False,
        "SITE TRUE remains blocked": output_data["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output_data["site_negative_allowed"] is False,
        "final positive promotion remains blocked": output_data["final_positive_promotion_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print()
    print("=" * 60)
    print("LEGACY CITY-BOARD SOURCE RECOVERY RESULT")
    print("=" * 60)
    print("Seed count:", len(SEEDS))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Transport error count:", transport_error_count)
    print("Qualified source count:", len(qualified))
    print("Next-stage source pool count:", len(next_stage))
    print("Resolution:", resolution)
    print("Output:", OUTPUT_PATH)
    print()
    print("VALIDATION")
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print("Duplicate qualified URL leakage:", duplicate_urls)
    print("Non-go.kr leakage:", non_go_kr)
    print("Unsafe promotion leakage:", unsafe)
    print("all_pass:", all(validations.values()))

    if not all(validations.values()):
        raise AssertionError("UQQ700 legacy Seongnam city-board source recovery regression failed")


if __name__ == "__main__":
    main()
