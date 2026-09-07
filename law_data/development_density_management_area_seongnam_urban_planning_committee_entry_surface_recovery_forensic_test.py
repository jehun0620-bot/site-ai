# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_entry_surface_recovery_forensic.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_URBAN_PLANNING_COMMITTEE_RECORD"
OFFICIAL_HOST = "www.seongnam.go.kr"

# Candidate official surfaces. S226R is forensic recovery only: no target search.
CANDIDATES = [
    ("detail_known", "https://www.seongnam.go.kr/city/1000557/30229/bbsView.do?idx=374215"),
    ("board_list_guess", "https://www.seongnam.go.kr/city/1000557/30229/bbsList.do"),
    ("board_menu", "https://www.seongnam.go.kr/city/1000557/30229"),
    ("city_root", "https://www.seongnam.go.kr/city/"),
]

BOARD_TERMS = ("도시계획위원회", "개최 결과", "도시계획과", "심의결과", "회의록")
ATTACHMENT_TERMS = (".pdf", ".hwp", ".hwpx", "download", "filedown", "첨부", "파일")
ENDPOINT_PATTERNS = (
    r"/city/[^\"'<> ]*/bbs(?:List|View)\.do[^\"'<> ]*",
    r"bbs(?:List|View)\.do\?[^\"'<> ]+",
)


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def attrs(tag: str) -> dict[str, str]:
    pairs = re.findall(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', tag, flags=re.S)
    return {k.lower(): unescape(v) for k, _, v in pairs}


def extract_links(html: str, base_url: str) -> list[dict]:
    rows: list[dict] = []
    for m in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", html or ""):
        a = attrs("<a" + m.group(1) + ">")
        href = a.get("href")
        text = clean_html(m.group(2))[:240]
        absolute = None
        if href and not href.lower().startswith("javascript:"):
            absolute = urljoin(base_url, href)
        rows.append({"text": text, "href_raw": href, "href_absolute": absolute, "onclick": a.get("onclick")})
    return rows


def extract_title(html: str) -> str | None:
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html or "")
    return clean_html(m.group(1)) if m else None


def classify_error(ex: Exception) -> str:
    name = type(ex).__name__
    msg = str(ex)
    low = msg.lower()
    if "ssl" in low or "certificate" in low:
        return "SSL_ERROR"
    if "timed out" in low or "timeout" in low:
        return "TIMEOUT"
    if "connection reset" in low or "connection aborted" in low:
        return "CONNECTION_RESET"
    if "name or service not known" in low or "getaddrinfo" in low:
        return "DNS_ERROR"
    return name.upper()


def fetch(session: requests.Session, label: str, url: str) -> dict:
    try:
        resp = session.get(url, timeout=45, allow_redirects=True)
        html = resp.text or ""
        text = clean_html(html)
        links = extract_links(html, resp.url)
        endpoint_hints: list[str] = []
        for pat in ENDPOINT_PATTERNS:
            endpoint_hints.extend(re.findall(pat, html, flags=re.I))
        endpoint_hints = sorted(set(endpoint_hints))[:100]
        board_term_hits = [t for t in BOARD_TERMS if t in text]
        attachment_signal = any(t in html.lower() for t in [x.lower() for x in ATTACHMENT_TERMS])
        same_host = urlparse(resp.url).hostname == OFFICIAL_HOST
        relevant_links = [
            row for row in links
            if ((row.get("href_absolute") and urlparse(row["href_absolute"]).hostname == OFFICIAL_HOST)
                and any(k in ((row.get("href_raw") or "") + " " + (row.get("text") or "")).lower()
                        for k in ("bbs", "30229", "도시계획", "위원회")))
        ]
        access_guard_signal = resp.status_code in (401, 403, 429, 503) or any(
            token in text.lower() for token in ("접근이 제한", "비정상적인 접근", "captcha", "보안문자", "서비스 이용이 제한")
        )
        return {
            "label": label,
            "input_url": url,
            "request_ok": True,
            "http": resp.status_code,
            "final_url": resp.url,
            "same_official_host": same_host,
            "title": extract_title(html),
            "body_bytes": len(resp.content),
            "board_term_hits": board_term_hits,
            "attachment_signal": attachment_signal,
            "relevant_link_count": len(relevant_links),
            "relevant_links_sample": relevant_links[:30],
            "endpoint_hints": endpoint_hints,
            "access_guard_signal": access_guard_signal,
            "error_class": None,
            "error": None,
        }
    except requests.RequestException as ex:
        return {
            "label": label,
            "input_url": url,
            "request_ok": False,
            "http": None,
            "final_url": None,
            "same_official_host": False,
            "title": None,
            "body_bytes": 0,
            "board_term_hits": [],
            "attachment_signal": False,
            "relevant_link_count": 0,
            "relevant_links_sample": [],
            "endpoint_hints": [],
            "access_guard_signal": False,
            "error_class": classify_error(ex),
            "error": f"{type(ex).__name__}: {ex}",
        }


def main() -> None:
    print("=" * 78)
    print("SEONGNAM URBAN PLANNING COMMITTEE ENTRY SURFACE RECOVERY FORENSIC - S226R")
    print("=" * 78)
    print("Purpose: recover official list/detail entry surface and diagnose S226 technical failure")
    print("Positive-control search: NOT EXECUTED")
    print("UQQ700 target query: NOT EXECUTED")
    print("Search request: NOT EXECUTED")
    print("Technical failure != legal absence")
    print("Committee record hit != designation notice")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
    })

    attempts = [fetch(session, label, url) for label, url in CANDIDATES]

    recovered_candidates = [
        a for a in attempts
        if a["request_ok"]
        and a["http"] == 200
        and a["same_official_host"]
        and (a["board_term_hits"] or a["relevant_link_count"] > 0 or a["endpoint_hints"])
    ]
    guarded = [a for a in attempts if a["access_guard_signal"]]
    technical_errors = [a for a in attempts if not a["request_ok"]]

    recovered = bool(recovered_candidates)
    if recovered:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_ENTRY_SURFACE_RECOVERED"
        semantic = "SEONGNAM_URBAN_PLANNING_COMMITTEE_OFFICIAL_ENTRY_SURFACE_RECOVERED_WITHOUT_TARGET_QUERY"
        next_action = "QUALIFY_RECOVERED_LIST_DETAIL_CONTRACT_BEFORE_POSITIVE_CONTROL_OR_UQQ700_QUERY"
    elif guarded:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_ENTRY_SURFACE_ACCESS_GUARDED"
        semantic = "SEONGNAM_URBAN_PLANNING_COMMITTEE_OFFICIAL_ENTRY_SURFACE_ACCESS_GUARD_OBSERVED"
        next_action = "RECOVER_BROWSER_OR_ALTERNATE_OFFICIAL_ENTRY_CONTRACT_WITHOUT_NEGATIVE_INFERENCE"
    else:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_ENTRY_SURFACE_TECHNICAL_UNKNOWN"
        semantic = "SEONGNAM_URBAN_PLANNING_COMMITTEE_ENTRY_SURFACE_REMAINS_TECHNICALLY_UNRESOLVED"
        next_action = "EXPAND_OFFICIAL_ENTRY_DISCOVERY_WITHOUT_TARGET_QUERY_OR_LEGAL_ABSENCE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-141-S226R",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "attempts": attempts,
        "recovered_candidate_count": len(recovered_candidates),
        "guarded_attempt_count": len(guarded),
        "technical_error_count": len(technical_errors),
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "positive_control_search_executed": False,
            "search_request_executed": False,
            "target_query_executed": False,
            "technical_failure_equals_legal_absence": False,
            "committee_record_hit_equals_designation_notice": False,
            "search_no_hit_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "official_designation_identity_verified": False,
            "current_validity_verified": False,
            "site_spatial_inclusion_verified": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "runtime_registration_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    for a in attempts:
        print("\n" + "-" * 78)
        print(f"[{a['label']}] {a['input_url']}")
        print(f"REQUEST OK: {a['request_ok']}")
        print(f"HTTP: {a['http']}")
        print(f"FINAL URL: {a['final_url']}")
        print(f"SAME OFFICIAL HOST: {a['same_official_host']}")
        print(f"TITLE: {a['title']}")
        print(f"BOARD TERM HITS: {a['board_term_hits']}")
        print(f"RELEVANT LINK COUNT: {a['relevant_link_count']}")
        print(f"ENDPOINT HINT COUNT: {len(a['endpoint_hints'])}")
        print(f"ATTACHMENT SIGNAL: {a['attachment_signal']}")
        print(f"ACCESS GUARD SIGNAL: {a['access_guard_signal']}")
        print(f"ERROR CLASS: {a['error_class']}")
        print(f"ERROR: {a['error']}")

    print("\n" + "=" * 78)
    print("RECOVERY SUMMARY")
    print("=" * 78)
    print(f"RECOVERED CANDIDATE COUNT: {len(recovered_candidates)}")
    print(f"GUARDED ATTEMPT COUNT: {len(guarded)}")
    print(f"TECHNICAL ERROR COUNT: {len(technical_errors)}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Search request executed: False")
    print("Target query executed: False")
    print("Legal absence inference allowed: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "candidate attempts executed": len(attempts) == len(CANDIDATES),
        "classification emitted": classification in {
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_ENTRY_SURFACE_RECOVERED",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_ENTRY_SURFACE_ACCESS_GUARDED",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_ENTRY_SURFACE_TECHNICAL_UNKNOWN",
        },
        "positive control search not executed": out["summary"]["positive_control_search_executed"] is False,
        "search request not executed": out["summary"]["search_request_executed"] is False,
        "target query not executed": out["summary"]["target_query_executed"] is False,
        "technical failure not legal absence": out["summary"]["technical_failure_equals_legal_absence"] is False,
        "committee hit not designation notice": out["summary"]["committee_record_hit_equals_designation_notice"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "SITE promotion blocked": out["summary"]["site_positive_allowed"] is False and out["summary"]["site_negative_allowed"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for key, value in validation.items():
        print(f"{key}: {value}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT}")

    if not all(validation.values()):
        raise AssertionError("S226R validation failed")


if __name__ == "__main__":
    main()
