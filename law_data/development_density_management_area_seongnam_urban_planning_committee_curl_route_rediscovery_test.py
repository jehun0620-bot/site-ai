# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_curl_route_rediscovery.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_URBAN_PLANNING_COMMITTEE_RECORD"
OFFICIAL_HOST = "www.seongnam.go.kr"

START_URLS = [
    ("root", "https://www.seongnam.go.kr/"),
    ("city_root", "https://www.seongnam.go.kr/city/"),
]

MENU_TERMS = ("도시계획위원회", "도시계획", "위원회", "고시/공고", "고시·공고")
ROUTE_HINT_TERMS = ("bbsList.do", "bbsView.do", "/city/", "1000557", "30229")


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def attrs(tag: str) -> dict[str, str]:
    pairs = re.findall(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', tag, flags=re.S)
    return {k.lower(): unescape(v) for k, _, v in pairs}


def extract_title(html: str) -> str | None:
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html or "")
    return clean_html(m.group(1)) if m else None


def extract_links(html: str, base_url: str) -> list[dict]:
    out: list[dict] = []
    for m in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", html or ""):
        a = attrs("<a" + m.group(1) + ">")
        href = a.get("href")
        text = clean_html(m.group(2))[:300]
        absolute = None
        if href and not href.lower().startswith("javascript:"):
            absolute = urljoin(base_url, href)
        out.append({
            "text": text,
            "href_raw": href,
            "href_absolute": absolute,
            "onclick": a.get("onclick"),
        })
    return out


def curl_fetch(url: str) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {
            "available": False,
            "ok": False,
            "http": None,
            "final_url": None,
            "html": "",
            "stderr": "curl not found",
        }

    cmd = [
        exe,
        "-L",
        "-sS",
        "--connect-timeout", "15",
        "--max-time", "45",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}|%{url_effective}",
        url,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    raw = p.stdout or ""
    marker = "\n__META__"
    if marker in raw:
        html, meta = raw.rsplit(marker, 1)
        parts = meta.strip().split("|", 1)
        http = parts[0] if parts else None
        final_url = parts[1] if len(parts) > 1 else None
    else:
        html, http, final_url = raw, None, None
    return {
        "available": True,
        "ok": p.returncode == 0 and bool(http and http != "000"),
        "returncode": p.returncode,
        "http": http,
        "final_url": final_url,
        "html": html,
        "stderr": (p.stderr or "").strip(),
    }


def analyze(label: str, url: str) -> dict:
    fetched = curl_fetch(url)
    html = fetched.pop("html")
    final_url = fetched.get("final_url") or url
    links = extract_links(html, final_url)
    text = clean_html(html)

    menu_hits = [t for t in MENU_TERMS if t in text]
    relevant_links = []
    for row in links:
        blob = " ".join(str(row.get(k) or "") for k in ("text", "href_raw", "href_absolute", "onclick"))
        if any(term.lower() in blob.lower() for term in MENU_TERMS + ROUTE_HINT_TERMS):
            relevant_links.append(row)

    endpoint_hints = sorted(set(re.findall(
        r'''(?i)(?:https?://www\.seongnam\.go\.kr)?/city/[^"'<>\s]*(?:bbsList|bbsView)\.do(?:\?[^"'<>\s]*)?''',
        html,
    )))

    same_host = bool(fetched.get("final_url") and urlparse(fetched["final_url"]).hostname == OFFICIAL_HOST)
    return {
        "label": label,
        "input_url": url,
        **fetched,
        "same_official_host": same_host,
        "title": extract_title(html),
        "body_bytes": len(html.encode("utf-8", errors="ignore")),
        "menu_term_hits": menu_hits,
        "link_count": len(links),
        "relevant_link_count": len(relevant_links),
        "relevant_links_sample": relevant_links[:80],
        "endpoint_hint_count": len(endpoint_hints),
        "endpoint_hints": endpoint_hints[:120],
    }


def main() -> None:
    print("=" * 78)
    print("SEONGNAM URBAN PLANNING COMMITTEE CURL ROUTE REDISCOVERY - S226C")
    print("=" * 78)
    print("Purpose: rediscover current official committee board routes using curl transport")
    print("Search request: NOT EXECUTED")
    print("UQQ700 target query: NOT EXECUTED")
    print("Committee record hit != designation notice")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    attempts = [analyze(label, url) for label, url in START_URLS]

    route_candidates: list[str] = []
    for a in attempts:
        route_candidates.extend(a.get("endpoint_hints") or [])
        for row in a.get("relevant_links_sample") or []:
            absolute = row.get("href_absolute")
            if absolute and urlparse(absolute).hostname == OFFICIAL_HOST:
                route_candidates.append(absolute)
    route_candidates = sorted(set(route_candidates))

    committee_candidates = [
        u for u in route_candidates
        if any(x in u.lower() for x in ("bbslist.do", "bbsview.do", "/city/"))
    ]

    root_ok = any(a.get("ok") and a.get("http") == "200" and a.get("same_official_host") for a in attempts)
    route_recovered = bool(root_ok and committee_candidates)

    if route_recovered:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_CURRENT_BOARD_ROUTE_CANDIDATES_RECOVERED"
        semantic = "SEONGNAM_URBAN_PLANNING_COMMITTEE_CURRENT_OFFICIAL_ROUTE_CANDIDATES_RECOVERED_WITHOUT_TARGET_QUERY"
        next_action = "QUALIFY_RECOVERED_BOARD_ROUTE_CANDIDATES_WITH_POSITIVE_CONTROL_ONLY_BEFORE_UQQ700_QUERY"
    elif root_ok:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_ROOT_RECOVERED_BOARD_ROUTE_UNRESOLVED"
        semantic = "SEONGNAM_OFFICIAL_CURL_TRANSPORT_WORKS_BUT_COMMITTEE_BOARD_ROUTE_NOT_YET_RECOVERED"
        next_action = "FORENSICALLY_EXPAND_MENU_AND_SCRIPT_ROUTE_DISCOVERY_WITHOUT_UQQ700_QUERY"
    else:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_CURL_ROUTE_REDISCOVERY_TECHNICAL_UNKNOWN"
        semantic = "SEONGNAM_OFFICIAL_CURL_ROUTE_REDISCOVERY_NOT_TECHNICALLY_QUALIFIED"
        next_action = "RECHECK_CURL_TRANSPORT_AND_OFFICIAL_ENTRY_SURFACE_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-141-S226C",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "attempts": attempts,
        "route_candidate_count": len(route_candidates),
        "route_candidates": route_candidates[:200],
        "committee_candidate_count": len(committee_candidates),
        "committee_candidates": committee_candidates[:200],
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "search_request_executed": False,
            "target_query_executed": False,
            "committee_record_hit_equals_designation_notice": False,
            "route_no_hit_equals_legal_absence": False,
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
        print(f"OK: {a['ok']}")
        print(f"HTTP: {a['http']}")
        print(f"FINAL URL: {a['final_url']}")
        print(f"SAME OFFICIAL HOST: {a['same_official_host']}")
        print(f"TITLE: {a['title']}")
        print(f"MENU TERM HITS: {a['menu_term_hits']}")
        print(f"LINK COUNT: {a['link_count']}")
        print(f"RELEVANT LINK COUNT: {a['relevant_link_count']}")
        print(f"ENDPOINT HINT COUNT: {a['endpoint_hint_count']}")
        print(f"STDERR: {a['stderr']}")

    print("\n" + "=" * 78)
    print("ROUTE REDISCOVERY SUMMARY")
    print("=" * 78)
    print(f"ROUTE CANDIDATE COUNT: {len(route_candidates)}")
    print(f"COMMITTEE CANDIDATE COUNT: {len(committee_candidates)}")
    for i, u in enumerate(committee_candidates[:30], 1):
        print(f"[{i:02d}] {u}")
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
        "classification emitted": classification in {
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_CURRENT_BOARD_ROUTE_CANDIDATES_RECOVERED",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_ROOT_RECOVERED_BOARD_ROUTE_UNRESOLVED",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_CURL_ROUTE_REDISCOVERY_TECHNICAL_UNKNOWN",
        },
        "search request not executed": out["summary"]["search_request_executed"] is False,
        "target query not executed": out["summary"]["target_query_executed"] is False,
        "committee hit not designation notice": out["summary"]["committee_record_hit_equals_designation_notice"] is False,
        "route no-hit not legal absence": out["summary"]["route_no_hit_equals_legal_absence"] is False,
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
        raise AssertionError("S226C validation failed")


if __name__ == "__main__":
    main()
