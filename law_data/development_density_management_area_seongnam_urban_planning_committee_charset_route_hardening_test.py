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
OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_charset_route_hardening.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_URBAN_PLANNING_COMMITTEE_RECORD"
OFFICIAL_HOST = "www.seongnam.go.kr"

START_URLS = [
    ("root", "https://www.seongnam.go.kr/"),
    ("index", "https://www.seongnam.go.kr/index"),
]

CHARSET_CANDIDATES = ("utf-8", "cp949", "euc-kr")
BOARD_TERMS = ("도시계획위원회", "도시계획과", "개최 결과", "심의 결과", "회의록")
ROUTE_TOKENS = ("bbsList.do", "bbsView.do")
PLACEHOLDER_HREFS = {"#", "#none", "", "javascript:void(0);", "javascript:;"}


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def extract_title(html: str) -> str | None:
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html or "")
    return clean_html(m.group(1)) if m else None


def detect_declared_charset(headers: str, raw: bytes) -> str | None:
    text = headers or ""
    m = re.search(r"(?i)content-type:[^\r\n]*charset\s*=\s*([\w-]+)", text)
    if m:
        return m.group(1).lower()
    head = raw[:8192].decode("ascii", errors="ignore")
    m = re.search(r"(?i)<meta[^>]+charset\s*=\s*[\"']?([\w-]+)", head)
    if m:
        return m.group(1).lower()
    m = re.search(r"(?i)content=[\"'][^\"']*charset\s*=\s*([\w-]+)", head)
    return m.group(1).lower() if m else None


def decode_best(raw: bytes, declared: str | None) -> tuple[str, str, dict[str, int]]:
    order = []
    if declared:
        order.append(declared)
    order.extend(CHARSET_CANDIDATES)
    seen = []
    candidates = []
    for enc in order:
        if enc.lower() not in [x.lower() for x in seen]:
            seen.append(enc)
            candidates.append(enc)

    scores: dict[str, int] = {}
    decoded: dict[str, str] = {}
    for enc in candidates:
        try:
            s = raw.decode(enc, errors="replace")
        except LookupError:
            continue
        replacement_count = s.count("�")
        korean_count = len(re.findall(r"[가-힣]", s))
        targetish_count = sum(s.count(t) for t in BOARD_TERMS)
        score = korean_count + (targetish_count * 1000) - (replacement_count * 50)
        scores[enc] = score
        decoded[enc] = s

    if not scores:
        return raw.decode("utf-8", errors="replace"), "utf-8-replace", {}
    best = max(scores, key=scores.get)
    return decoded[best], best, scores


def attrs(fragment: str) -> dict[str, str]:
    pairs = re.findall(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', fragment, flags=re.S)
    return {k.lower(): unescape(v) for k, _, v in pairs}


def valid_http_href(href: str | None, base_url: str) -> str | None:
    if href is None:
        return None
    raw = href.strip()
    if raw.lower() in PLACEHOLDER_HREFS:
        return None
    if raw.lower().startswith("javascript:"):
        return None
    absolute = urljoin(base_url, raw)
    p = urlparse(absolute)
    if p.scheme not in ("http", "https"):
        return None
    if p.hostname != OFFICIAL_HOST:
        return None
    if p.fragment and not p.path:
        return None
    return absolute


def extract_routes(html: str, base_url: str) -> dict:
    links = []
    for m in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", html or ""):
        a = attrs("<a" + m.group(1) + ">")
        href = valid_http_href(a.get("href"), base_url)
        text = clean_html(m.group(2))[:300]
        onclick = a.get("onclick") or ""
        links.append({"text": text, "href": href, "onclick": onclick})

    script_srcs = []
    for m in re.finditer(r"(?is)<script\b([^>]*)>", html or ""):
        a = attrs("<script" + m.group(1) + ">")
        src = valid_http_href(a.get("src"), base_url)
        if src:
            script_srcs.append(src)

    raw_routes = set()
    for pat in (
        r'''(?i)(?:https?://www\.seongnam\.go\.kr)?/[^"'<>\s]*(?:bbsList|bbsView)\.do(?:\?[^"'<>\s]*)?''',
        r'''(?i)["']([^"']*(?:bbsList|bbsView)\.do[^"']*)["']''',
    ):
        for x in re.findall(pat, html or ""):
            candidate = x if isinstance(x, str) else x[0]
            absu = valid_http_href(candidate, base_url)
            if absu:
                raw_routes.add(absu)

    board_links = []
    for row in links:
        blob = f"{row['text']} {row['href'] or ''} {row['onclick']}"
        if row["href"] and (any(t in blob for t in BOARD_TERMS) or any(tok.lower() in blob.lower() for tok in ROUTE_TOKENS)):
            board_links.append(row)

    return {
        "link_count": len(links),
        "script_src_count": len(script_srcs),
        "script_srcs": sorted(set(script_srcs))[:100],
        "raw_route_count": len(raw_routes),
        "raw_routes": sorted(raw_routes)[:200],
        "board_link_count": len(board_links),
        "board_links": board_links[:100],
    }


def curl_fetch_bytes(url: str) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"available": False, "ok": False, "http": None, "final_url": None, "headers": "", "body": b"", "stderr": "curl not found"}

    header_file = OUT_DIR / "_s226d_headers.tmp"
    body_file = OUT_DIR / "_s226d_body.tmp"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for p in (header_file, body_file):
        if p.exists():
            p.unlink()

    cmd = [
        exe, "-L", "-sS",
        "--connect-timeout", "15", "--max-time", "45",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-D", str(header_file),
        "-o", str(body_file),
        "-w", "%{http_code}|%{url_effective}",
        url,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    meta = (p.stdout or "").strip().split("|", 1)
    http = meta[0] if meta else None
    final_url = meta[1] if len(meta) > 1 else None
    headers = header_file.read_text(encoding="latin-1", errors="replace") if header_file.exists() else ""
    body = body_file.read_bytes() if body_file.exists() else b""
    for f in (header_file, body_file):
        if f.exists():
            f.unlink()
    return {
        "available": True,
        "ok": p.returncode == 0 and bool(http and http != "000"),
        "returncode": p.returncode,
        "http": http,
        "final_url": final_url,
        "headers": headers,
        "body": body,
        "stderr": (p.stderr or "").strip(),
    }


def analyze(label: str, url: str) -> dict:
    fetched = curl_fetch_bytes(url)
    body = fetched.pop("body")
    declared = detect_declared_charset(fetched.get("headers") or "", body)
    html, selected, scores = decode_best(body, declared)
    final_url = fetched.get("final_url") or url
    routes = extract_routes(html, final_url)
    text = clean_html(html)
    return {
        "label": label,
        "input_url": url,
        **fetched,
        "same_official_host": bool(fetched.get("final_url") and urlparse(fetched["final_url"]).hostname == OFFICIAL_HOST),
        "declared_charset": declared,
        "selected_charset": selected,
        "charset_scores": scores,
        "title": extract_title(html),
        "board_term_hits": [t for t in BOARD_TERMS if t in text],
        "mojibake_replacement_count": html.count("�"),
        **routes,
    }


def main() -> None:
    print("=" * 78)
    print("SEONGNAM URBAN PLANNING COMMITTEE CHARSET / ROUTE HARDENING - S226D")
    print("=" * 78)
    print("Purpose: harden curl HTML decoding and real route qualification after S226C false positive")
    print("S226C status: DIAGNOSTIC_ONLY | #none placeholder and overly broad /city/ candidate rule")
    print("Search request: NOT EXECUTED")
    print("UQQ700 target query: NOT EXECUTED")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    attempts = [analyze(label, url) for label, url in START_URLS]
    real_routes = sorted(set(
        route
        for a in attempts
        for route in (a.get("raw_routes") or [])
        if any(tok.lower() in route.lower() for tok in ROUTE_TOKENS)
    ))
    board_links = [row for a in attempts for row in (a.get("board_links") or []) if row.get("href")]
    root_ok = any(a.get("ok") and a.get("http") == "200" and a.get("same_official_host") for a in attempts)
    decoding_hardened = any((a.get("selected_charset") and a.get("mojibake_replacement_count", 0) == 0) for a in attempts if a.get("ok"))

    if root_ok and real_routes:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_REAL_BOARD_ROUTE_CANDIDATES_RECOVERED"
        semantic = "SEONGNAM_COMMITTEE_ROUTE_RECOVERED_AFTER_CHARSET_AND_PLACEHOLDER_HARDENING"
        next_action = "QUALIFY_REAL_BOARD_ROUTES_WITH_POSITIVE_CONTROL_ONLY_BEFORE_UQQ700_QUERY"
    elif root_ok and decoding_hardened:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_CHARSET_RECOVERED_ROUTE_STILL_UNRESOLVED"
        semantic = "SEONGNAM_OFFICIAL_HTML_DECODED_RELIABLY_BUT_REAL_COMMITTEE_ROUTE_NOT_YET_RECOVERED"
        next_action = "EXPAND_SCRIPT_AND_MENU_ROUTE_DISCOVERY_WITHOUT_UQQ700_QUERY"
    else:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_CHARSET_ROUTE_HARDENING_TECHNICAL_UNKNOWN"
        semantic = "SEONGNAM_CHARSET_ROUTE_HARDENING_REMAINS_TECHNICALLY_UNRESOLVED"
        next_action = "CONTINUE_OFFICIAL_SURFACE_FORENSICS_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-141-S226D",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "s226c_status": "DIAGNOSTIC_ONLY",
        "s226c_false_positive_reason": "#none placeholder plus overly broad /city/ candidate qualification",
        "attempts": attempts,
        "real_route_count": len(real_routes),
        "real_routes": real_routes,
        "board_link_count": len(board_links),
        "board_links": board_links[:100],
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "search_request_executed": False,
            "target_query_executed": False,
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
        print(f"DECLARED CHARSET: {a['declared_charset']}")
        print(f"SELECTED CHARSET: {a['selected_charset']}")
        print(f"CHARSET SCORES: {a['charset_scores']}")
        print(f"TITLE: {a['title']}")
        print(f"MOJIBAKE REPLACEMENT COUNT: {a['mojibake_replacement_count']}")
        print(f"BOARD TERM HITS: {a['board_term_hits']}")
        print(f"SCRIPT SRC COUNT: {a['script_src_count']}")
        print(f"RAW ROUTE COUNT: {a['raw_route_count']}")
        print(f"BOARD LINK COUNT: {a['board_link_count']}")
        print(f"STDERR: {a['stderr']}")

    print("\n" + "=" * 78)
    print("HARDENING SUMMARY")
    print("=" * 78)
    print("S226C: DIAGNOSTIC_ONLY")
    print("S226C FALSE POSITIVE: #none placeholder + overly broad /city/ candidate rule")
    print(f"REAL ROUTE COUNT: {len(real_routes)}")
    for i, route in enumerate(real_routes[:30], 1):
        print(f"[{i:02d}] {route}")
    print(f"BOARD LINK COUNT: {len(board_links)}")
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
        "S226C diagnostic only": out["s226c_status"] == "DIAGNOSTIC_ONLY",
        "classification emitted": classification in {
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_REAL_BOARD_ROUTE_CANDIDATES_RECOVERED",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_CHARSET_RECOVERED_ROUTE_STILL_UNRESOLVED",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_CHARSET_ROUTE_HARDENING_TECHNICAL_UNKNOWN",
        },
        "search request not executed": out["summary"]["search_request_executed"] is False,
        "target query not executed": out["summary"]["target_query_executed"] is False,
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
        raise AssertionError("S226D validation failed")


if __name__ == "__main__":
    main()
