# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-23
Development Density Management Area
Municipal Gazette Historical Row Registry Recovery

Traverse only the T-22 validated municipal gazette page range and recover canonical
row identities: gazette number, date, pstSn, page number, and row-local metadata.
No UQQ700 target identity evaluation, no detail execution, and no document promotion.
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
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)
T22_PATH = OUT_DIR / "development_density_management_area_municipal_gazette_historical_pagination_boundary_recovery.json"
OUT_PATH = OUT_DIR / "development_density_management_area_municipal_gazette_historical_row_registry_recovery.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False
SOURCE_FAMILY = "CURRENT_MUNICIPAL_GAZETTE_ARCHIVE"
FUNCTION_NAME = "fn_move_form"

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_REQUESTS = 162
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

TR_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>", re.S)
GAZETTE_RE = re.compile(r"성남시보\s*제\s*(\d+)\s*호", re.I)
DATE_RE = re.compile(r"((?:19|20)\d{2})년\s*(\d{1,2})월\s*(\d{1,2})일")
CALL_RE = re.compile(r"fn_move_form\s*\(\s*['\"]?(\d+)['\"]?\s*\)", re.I)


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


def gov(host: str) -> bool:
    return bool(host) and (host == "go.kr" or host.endswith(".go.kr"))


def build_page_url(base_url: str, key: str, page: int) -> str:
    p = urlparse(base_url)
    q = dict(parse_qsl(p.query, keep_blank_values=True))
    q[key] = str(page)
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


def parse_rows(raw_html: str, page: int, page_url: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for tr_index, match in enumerate(TR_RE.finditer(raw_html or ""), start=1):
        raw_row = match.group(1)
        text = norm(html.unescape(TAG_RE.sub(" ", raw_row)))
        gazette_match = GAZETTE_RE.search(text)
        if not gazette_match:
            continue
        pst_matches = list(CALL_RE.finditer(raw_row))
        if not pst_matches:
            continue
        dates = [
            f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
            for y, m, d in DATE_RE.findall(text)
        ]
        for pst_match in pst_matches:
            rows.append({
                "source_family": SOURCE_FAMILY,
                "page_number": page,
                "page_url": page_url,
                "tr_index": tr_index,
                "gazette_number": int(gazette_match.group(1)),
                "date": dates[0] if dates else "",
                "pstSn": pst_match.group(1),
                "function": FUNCTION_NAME,
                "row_text": text[:3000],
                "target_identity_evaluated": False,
                "detail_request_executed": False,
                "document_candidate_generated": False,
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
                "site_negative_allowed": False,
                "final_positive_promotion_allowed": False,
            })
    return rows


def unique_rows(rows: Iterable[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    out: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()
    duplicate_count = 0
    for row in rows:
        key = (norm(row.get("source_family")), norm(row.get("pstSn")))
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        out.append(row)
    out.sort(key=lambda x: (int(x.get("gazette_number") or 0), norm(x.get("pstSn"))), reverse=True)
    return out, duplicate_count


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE HISTORICAL ROW REGISTRY RECOVERY")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Target identity evaluation: DISABLED")
    print("Detail request execution: DISABLED")
    print()

    if not T22_PATH.exists():
        raise FileNotFoundError(T22_PATH)
    t22 = json.loads(T22_PATH.read_text(encoding="utf-8"))
    pool = t22.get("next_stage_boundary_pool") or []
    if len(pool) != 1:
        raise AssertionError("T-22 boundary contract cardinality must be exactly one")
    contract = pool[0]
    base_url = norm(contract.get("base_url"))
    pagination_key = norm(contract.get("pagination_key"))
    lower_page = int(contract.get("effective_lower_page") or 1)
    upper_page = int(contract.get("effective_upper_page") or 0)
    if lower_page != 1 or upper_page <= 0:
        raise AssertionError("invalid T-22 page range")

    pages = list(range(lower_page, upper_page + 1))
    if len(pages) > MAX_TOTAL_REQUESTS:
        raise AssertionError("validated range exceeds bounded request budget")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})

    request_count = 0
    http_success_count = 0
    transport_error_count = 0
    raw_rows: List[Dict[str, Any]] = []
    page_results: List[Dict[str, Any]] = []

    for page in pages:
        url = build_page_url(base_url, pagination_key, page)
        response = fetch(session, url)
        request_count += 1
        status = response.get("http_status")
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1
        if response.get("error"):
            transport_error_count += 1
        rows = parse_rows(response.get("text") or "", page, response.get("final_url") or url) if status == 200 else []
        raw_rows.extend(rows)
        page_results.append({
            "source_family": SOURCE_FAMILY,
            "page_number": page,
            "page_url": url,
            "http_status": status,
            "row_count": len(rows),
            "response_bytes": response.get("response_bytes"),
        })
        if page <= 3 or page % 20 == 0 or page >= upper_page - 2:
            print("-" * 60)
            print("PAGE:", page)
            print("HTTP:", status)
            print("Recovered rows:", len(rows))
            if rows:
                print("First gazette:", rows[0]["gazette_number"], rows[0]["date"], rows[0]["pstSn"])
                print("Last gazette:", rows[-1]["gazette_number"], rows[-1]["date"], rows[-1]["pstSn"])

    canonical_rows, duplicate_count = unique_rows(raw_rows)
    gazette_numbers = [int(r["gazette_number"]) for r in canonical_rows]
    dates = [r["date"] for r in canonical_rows if r.get("date")]
    page_gaps = [r["page_number"] for r in page_results if r.get("http_status") == 200 and int(r.get("row_count") or 0) == 0]

    next_pool = [
        {
            "source_family": row["source_family"],
            "gazette_number": row["gazette_number"],
            "date": row["date"],
            "pstSn": row["pstSn"],
            "page_number": row["page_number"],
            "row_text": row["row_text"],
            "requires_target_metadata_filter": True,
            "target_identity_evaluated": False,
            "detail_request_executed": False,
            "document_candidate_generated": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for row in canonical_rows
    ]

    output = {
        "step": "STEP 17-21-C-16-8-T-23 Municipal Gazette Historical Row Registry Recovery",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "inputs": {
            "t22_path": str(T22_PATH),
            "effective_lower_page": lower_page,
            "effective_upper_page": upper_page,
        },
        "method": {
            "validated_range_only": True,
            "target_identity_evaluation_enabled": False,
            "detail_request_execution_enabled": False,
            "document_candidate_generation_enabled": False,
            "canonical_identity_by_pstSn": True,
        },
        "summary": {
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "raw_row_count": len(raw_rows),
            "duplicate_row_removed": duplicate_count,
            "canonical_row_count": len(canonical_rows),
            "min_gazette_number": min(gazette_numbers) if gazette_numbers else None,
            "max_gazette_number": max(gazette_numbers) if gazette_numbers else None,
            "earliest_date": min(dates) if dates else None,
            "latest_date": max(dates) if dates else None,
            "empty_page_within_validated_range_count": len(page_gaps),
            "next_stage_row_pool_count": len(next_pool),
        },
        "page_results": page_results,
        "canonical_gazette_rows": canonical_rows,
        "next_stage_row_pool": next_pool,
        "resolution": "MUNICIPAL_GAZETTE_HISTORICAL_ROW_REGISTRY_RECOVERY_COMPLETED",
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    duplicate_pst = len(canonical_rows) - len({r["pstSn"] for r in canonical_rows})
    invalid_host = sum(1 for r in page_results if not gov(hostname(r["page_url"])))
    unsafe = sum(1 for r in canonical_rows if any([
        r.get("target_identity_evaluated"), r.get("detail_request_executed"), r.get("document_candidate_generated"),
        r.get("verified_positive"), r.get("runtime_registration_allowed"), r.get("site_positive_allowed"),
        r.get("site_negative_allowed"), r.get("final_positive_promotion_allowed"),
    ]))

    validations = {
        "T-22 input exists": T22_PATH.exists(),
        "single validated boundary loaded": len(pool) == 1,
        "bounded request count respected": request_count <= MAX_TOTAL_REQUESTS,
        "full validated range traversed": request_count == len(pages),
        "all validated-range requests HTTP 200": http_success_count == request_count,
        "canonical rows recovered": len(canonical_rows) > 0,
        "canonical pstSn unique": duplicate_pst == 0,
        "page hosts go.kr": invalid_host == 0,
        "target identity evaluation disabled": True,
        "detail request execution disabled": True,
        "document candidate generation disabled": True,
        "unsafe promotion leakage zero": unsafe == 0,
        "output written": OUT_PATH.exists() and OUT_PATH.stat().st_size > 0,
    }

    print()
    print("=" * 60)
    print("HISTORICAL ROW REGISTRY RESULT")
    print("=" * 60)
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Raw row count:", len(raw_rows))
    print("Duplicate row removed:", duplicate_count)
    print("Canonical row count:", len(canonical_rows))
    print("Gazette number range:", (min(gazette_numbers), max(gazette_numbers)) if gazette_numbers else None)
    print("Date range:", (min(dates), max(dates)) if dates else None)
    print("Empty pages inside range:", page_gaps)
    print("Next-stage row pool count:", len(next_pool))
    print("Output:", OUT_PATH)
    print()
    print("VALIDATION")
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print("Duplicate pstSn leakage:", duplicate_pst)
    print("Invalid host leakage:", invalid_host)
    print("Unsafe promotion leakage:", unsafe)
    print("all_pass:", all(validations.values()))

    if not all(validations.values()):
        raise AssertionError("municipal gazette historical row registry recovery failed")


if __name__ == "__main__":
    main()
