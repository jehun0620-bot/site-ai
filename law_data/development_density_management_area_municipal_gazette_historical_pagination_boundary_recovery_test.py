# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-22
Development Density Management Area
Municipal Gazette Historical Pagination Boundary Recovery

Goal:
Recover the actual historical pagination boundary of the validated Seongnam municipal
gazette archive using bounded sparse probes only.

Safety:
- no UQQ700 target query
- no bulk detail execution
- no document candidate promotion
- no SITE TRUE/FALSE inference
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

T21_PATH = OUT_DIR / "development_density_management_area_municipal_gazette_bounded_detail_validation.json"
OUT_PATH = OUT_DIR / "development_density_management_area_municipal_gazette_historical_pagination_boundary_recovery.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

SOURCE_FAMILY = "CURRENT_MUNICIPAL_GAZETTE_ARCHIVE"
SOURCE_URL = "https://www.seongnam.go.kr/bbs010308"
PAGINATION_KEY = "curPage"

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_REQUESTS = 24
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

# Deliberately sparse and bounded. No unbounded crawling.
PROBE_PAGES = [1, 2, 5, 10, 20, 50, 100, 120, 140, 150, 155, 160, 161, 162, 163, 164, 165, 170, 180, 200, 250, 300]

TAG_RE = re.compile(r"<[^>]+>", re.S)
GAZETTE_RE = re.compile(r"성남시보\s*제\s*(\d+)\s*호", re.I)
ROW_DATE_RE = re.compile(r"((?:19|20)\d{2})년\s*(\d{1,2})월\s*(\d{1,2})일")
TOTAL_RE = re.compile(r"총\s*([0-9,]+)\s*건")


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def canonicalize_url(url: str) -> str:
    p = urlparse(norm(url))
    if not p.hostname:
        return ""
    params = sorted(parse_qsl(p.query, keep_blank_values=True), key=lambda x: (x[0].lower(), x[1]))
    return urlunparse(((p.scheme or "https").lower(), (p.hostname or "").lower(), p.path or "/", "", urlencode(params), ""))


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_government_host(host: str) -> bool:
    return bool(host) and (host == "go.kr" or host.endswith(".go.kr"))


def build_page_url(page: int) -> str:
    p = urlparse(SOURCE_URL)
    q = dict(parse_qsl(p.query, keep_blank_values=True))
    q[PAGINATION_KEY] = str(page)
    return canonicalize_url(urlunparse((p.scheme, p.netloc, p.path, "", urlencode(q), "")))


def fetch(session: requests.Session, url: str) -> Dict[str, Any]:
    out = {"http_status": None, "final_url": "", "text": "", "error": "", "response_bytes": 0}
    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
            out["http_status"] = response.status_code
            out["final_url"] = str(response.url)
            chunks: List[bytes] = []
            total = 0
            for chunk in response.iter_content(128 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise ValueError("response too large")
                chunks.append(chunk)
            raw = b"".join(chunks)
            out["response_bytes"] = len(raw)
            for enc in [response.encoding, "utf-8", "cp949", "euc-kr"]:
                if not enc:
                    continue
                try:
                    out["text"] = raw.decode(enc)
                    break
                except Exception:
                    continue
            if not out["text"]:
                out["text"] = raw.decode("utf-8", errors="replace")
    except Exception as exc:
        out["error"] = repr(exc)
    return out


def page_identity(raw_html: str) -> Dict[str, Any]:
    plain = norm(html.unescape(TAG_RE.sub(" ", raw_html or "")))
    gazette_numbers = [int(m.group(1)) for m in GAZETTE_RE.finditer(plain)]
    dates = [
        f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        for y, m, d in ROW_DATE_RE.findall(plain)
    ]
    total_match = TOTAL_RE.search(plain)
    total_count = int(total_match.group(1).replace(",", "")) if total_match else None
    # Hash only the semantic row identity, not page chrome or CSRF tokens.
    semantic = json.dumps({
        "gazette_numbers": gazette_numbers,
        "dates": dates,
    }, ensure_ascii=False, sort_keys=True)
    return {
        "gazette_numbers": gazette_numbers,
        "dates": dates,
        "total_count": total_count,
        "semantic_sha256": hashlib.sha256(semantic.encode("utf-8")).hexdigest(),
        "row_count": len(gazette_numbers),
    }


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE HISTORICAL PAGINATION BOUNDARY RECOVERY")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Target query execution: DISABLED")
    print("Bulk detail execution: DISABLED")
    print()

    if not T21_PATH.exists():
        raise FileNotFoundError(T21_PATH)
    t21 = json.loads(T21_PATH.read_text(encoding="utf-8"))
    t21_pool = t21.get("next_stage_contract_pool") or []
    if not t21_pool:
        raise AssertionError("T-21 validated gazette contract missing")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})

    records: List[Dict[str, Any]] = []
    request_count = 0
    http_success_count = 0
    transport_error_count = 0

    first_nonempty_sha: Optional[str] = None
    repeated_response_start: Optional[int] = None
    first_empty_page: Optional[int] = None

    for page in PROBE_PAGES:
        if request_count >= MAX_REQUESTS:
            break
        url = build_page_url(page)
        response = fetch(session, url)
        request_count += 1
        status = response.get("http_status")
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1
        if response.get("error"):
            transport_error_count += 1

        identity = page_identity(response.get("text") or "") if status == 200 else {
            "gazette_numbers": [], "dates": [], "total_count": None, "semantic_sha256": "", "row_count": 0
        }
        if identity["row_count"] == 0 and first_empty_page is None and status == 200:
            first_empty_page = page
        if identity["row_count"] > 0 and first_nonempty_sha is None:
            first_nonempty_sha = identity["semantic_sha256"]
        if (
            page > 1
            and identity["row_count"] > 0
            and first_nonempty_sha
            and identity["semantic_sha256"] == first_nonempty_sha
            and repeated_response_start is None
        ):
            repeated_response_start = page

        record = {
            "page": page,
            "url": url,
            "http_status": status,
            "final_url": response.get("final_url"),
            "response_bytes": response.get("response_bytes"),
            **identity,
        }
        records.append(record)

        print("-" * 60)
        print("PAGE:", page)
        print("HTTP:", status)
        print("Rows:", identity["row_count"])
        print("Gazette numbers:", identity["gazette_numbers"][:3], "...", identity["gazette_numbers"][-3:] if identity["gazette_numbers"] else [])
        print("Dates:", identity["dates"][:2], "...", identity["dates"][-2:] if identity["dates"] else [])
        print("Total count:", identity["total_count"])

    nonempty_pages = [r["page"] for r in records if r["row_count"] > 0]
    empty_pages = [r["page"] for r in records if r["http_status"] == 200 and r["row_count"] == 0]
    observed_totals = sorted({r["total_count"] for r in records if isinstance(r.get("total_count"), int)})

    # Boundary is evidence-derived only.
    effective_upper_page: Optional[int] = None
    boundary_reason = ""
    if first_empty_page is not None:
        previous_nonempty = [p for p in nonempty_pages if p < first_empty_page]
        if previous_nonempty:
            effective_upper_page = max(previous_nonempty)
            boundary_reason = f"FIRST_EMPTY_PAGE:{first_empty_page}"
    elif repeated_response_start is not None:
        previous_nonempty = [p for p in nonempty_pages if p < repeated_response_start]
        if previous_nonempty:
            effective_upper_page = max(previous_nonempty)
            boundary_reason = f"REPEATED_RESPONSE_START:{repeated_response_start}"

    # If total count is stable, use it only as supporting evidence, not as sole boundary evidence.
    stable_total_count = observed_totals[0] if len(observed_totals) == 1 else None

    qualified = effective_upper_page is not None
    next_pool = []
    if qualified:
        next_pool.append({
            "source_family": SOURCE_FAMILY,
            "base_url": SOURCE_URL,
            "pagination_key": PAGINATION_KEY,
            "effective_lower_page": 1,
            "effective_upper_page": effective_upper_page,
            "boundary_reason": boundary_reason,
            "stable_total_count": stable_total_count,
            "requires_bounded_historical_gazette_traversal": True,
            "target_query_executed": False,
            "bulk_detail_executed": False,
            "document_candidate_generated": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
        })

    resolution = (
        "MUNICIPAL_GAZETTE_HISTORICAL_PAGINATION_BOUNDARY_RECOVERED"
        if qualified
        else "MUNICIPAL_GAZETTE_HISTORICAL_PAGINATION_BOUNDARY_UNRESOLVED"
    )

    output = {
        "step": "STEP 17-21-C-16-8-T-22 Municipal Gazette Historical Pagination Boundary Recovery",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "method": {
            "bounded_sparse_probe_enabled": True,
            "unbounded_crawl_disabled": True,
            "target_query_execution_enabled": False,
            "bulk_detail_execution_enabled": False,
            "document_candidate_generation_enabled": False,
        },
        "summary": {
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "nonempty_probe_pages": nonempty_pages,
            "empty_probe_pages": empty_pages,
            "first_empty_page": first_empty_page,
            "repeated_response_start": repeated_response_start,
            "stable_total_count": stable_total_count,
            "effective_upper_page": effective_upper_page,
            "boundary_reason": boundary_reason,
        },
        "probe_records": records,
        "next_stage_boundary_pool": next_pool,
        "resolution": resolution,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    non_go_kr = sum(1 for r in records if r.get("final_url") and not is_government_host(hostname(r["final_url"])))
    unsafe = int(any([
        output["verified_positive"], output["runtime_registration_allowed"], output["site_positive_allowed"],
        output["site_negative_allowed"], output["final_positive_promotion_allowed"],
    ]))

    validations = {
        "T-21 input exists": T21_PATH.exists(),
        "validated detail contract loaded": bool(t21_pool),
        "bounded request count respected": request_count <= MAX_REQUESTS,
        "sparse boundary probing enabled": True,
        "unbounded crawling disabled": True,
        "target query execution disabled": True,
        "bulk detail execution disabled": True,
        "document candidate generation disabled": True,
        "official host leakage zero": non_go_kr == 0,
        "unsafe promotion leakage zero": unsafe == 0,
        "output written": OUT_PATH.exists() and OUT_PATH.stat().st_size > 0,
    }

    print()
    print("=" * 60)
    print("PAGINATION BOUNDARY RESULT")
    print("=" * 60)
    print("Request count:", request_count)
    print("Non-empty probe pages:", nonempty_pages)
    print("Empty probe pages:", empty_pages)
    print("First empty page:", first_empty_page)
    print("Repeated response start:", repeated_response_start)
    print("Stable total count:", stable_total_count)
    print("Effective upper page:", effective_upper_page)
    print("Boundary reason:", boundary_reason)
    print("Resolution:", resolution)
    print("Output:", OUT_PATH)
    print()
    print("VALIDATION")
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print("Non-go.kr leakage:", non_go_kr)
    print("Unsafe promotion leakage:", unsafe)
    print("all_pass:", all(validations.values()))

    if not all(validations.values()):
        raise AssertionError("municipal gazette historical pagination boundary recovery failed")


if __name__ == "__main__":
    main()
