# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import shutil
import subprocess
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_script_menu_route_discovery.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_URBAN_PLANNING_COMMITTEE_RECORD"
OFFICIAL_HOST = "www.seongnam.go.kr"
ROOT_URL = "https://www.seongnam.go.kr/index"

BOARD_TERMS = ("도시계획위원회", "도시계획", "위원회", "개최 결과", "심의결과", "회의록")
ROUTE_TOKENS = ("bbsList.do", "bbsView.do", "menu", "city", "board", "bbs")
PLACEHOLDER_PREFIXES = ("#", "javascript:", "mailto:", "tel:")


def curl_bytes(url: str) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"ok": False, "http": None, "final_url": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS",
        "--connect-timeout", "15", "--max-time", "45",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}|%{url_effective}",
        url,
    ]
    p = subprocess.run(cmd, capture_output=True)
    raw = p.stdout or b""
    marker = b"\n__META__"
    if marker in raw:
        body, meta = raw.rsplit(marker, 1)
        parts = meta.decode("utf-8", errors="replace").strip().split("|", 1)
        http = parts[0] if parts else None
        final_url = parts[1] if len(parts) > 1 else None
    else:
        body, http, final_url = raw, None, None
    return {
        "ok": p.returncode == 0 and bool(http and http != "000"),
        "returncode": p.returncode,
        "http": http,
        "final_url": final_url,
        "body": body,
        "stderr": (p.stderr or b"").decode("utf-8", errors="replace").strip(),
    }


def decode_body(body: bytes) -> tuple[str, str]:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            text = body.decode(enc)
            if "성남" in text or enc == "utf-8":
                return text, enc
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", errors="replace"), "utf-8-replace"


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def attr_map(fragment: str) -> dict[str, str]:
    pairs = re.findall(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', fragment, flags=re.S)
    return {k.lower(): unescape(v) for k, _, v in pairs}


def extract_script_srcs(html: str, base_url: str) -> list[str]:
    out = []
    for m in re.finditer(r"(?is)<script\b([^>]*)>", html or ""):
        a = attr_map(m.group(1))
        src = a.get("src")
        if not src:
            continue
        u = urljoin(base_url, src)
        if urlparse(u).hostname == OFFICIAL_HOST:
            out.append(u)
    return sorted(set(out))


def extract_inline_scripts(html: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"(?is)<script\b[^>]*>(.*?)</script>", html or "") if m.group(1).strip()]


def extract_links(html: str, base_url: str) -> list[dict]:
    rows = []
    for m in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", html or ""):
        a = attr_map(m.group(1))
        href = (a.get("href") or "").strip()
        text = clean_html(m.group(2))[:300]
        low = href.lower()
        placeholder = (not href) or low.startswith(PLACEHOLDER_PREFIXES) or href in ("#none", "#")
        absolute = None if placeholder else urljoin(base_url, href)
        rows.append({
            "text": text,
            "href_raw": href,
            "href_absolute": absolute,
            "onclick": a.get("onclick"),
            "placeholder": placeholder,
        })
    return rows


def route_hints_from_text(text: str, base_url: str) -> list[str]:
    candidates = set()
    patterns = [
        r'''(?i)(https?://www\.seongnam\.go\.kr/[^"'<>\s)]+)''',
        r'''(?i)(/[^"'<>\s)]*(?:bbsList|bbsView)\.do(?:\?[^"'<>\s)]*)?)''',
        r'''(?i)(/city/[^"'<>\s)]+)''',
    ]
    for pat in patterns:
        for hit in re.findall(pat, text or ""):
            u = urljoin(base_url, hit)
            if urlparse(u).hostname != OFFICIAL_HOST:
                continue
            frag = urlparse(u).fragment.lower()
            if frag in ("none", ""):
                pass
            elif frag:
                u = u.split("#", 1)[0]
            if u.rstrip("/") in ("https://www.seongnam.go.kr", "https://www.seongnam.go.kr/city"):
                continue
            candidates.add(u)
    return sorted(candidates)


def page_summary(label: str, url: str) -> dict:
    f = curl_bytes(url)
    html, enc = decode_body(f.pop("body"))
    final_url = f.get("final_url") or url
    links = extract_links(html, final_url)
    valid_same_host_links = [
        r for r in links
        if not r["placeholder"] and r.get("href_absolute") and urlparse(r["href_absolute"]).hostname == OFFICIAL_HOST
    ]
    menu_links = [
        r for r in valid_same_host_links
        if any(term in ((r.get("text") or "") + " " + (r.get("href_raw") or "") + " " + (r.get("onclick") or "")) for term in BOARD_TERMS)
        or any(tok.lower() in ((r.get("href_raw") or "") + " " + (r.get("onclick") or "")).lower() for tok in ROUTE_TOKENS)
    ]
    script_srcs = extract_script_srcs(html, final_url)
    inline = extract_inline_scripts(html)
    route_hints = route_hints_from_text(html, final_url)
    return {
        "label": label,
        "input_url": url,
        **f,
        "selected_charset": enc,
        "same_official_host": bool(f.get("final_url") and urlparse(f["final_url"]).hostname == OFFICIAL_HOST),
        "board_term_hits": [t for t in BOARD_TERMS if t in clean_html(html)],
        "script_src_count": len(script_srcs),
        "script_srcs": script_srcs,
        "inline_script_count": len(inline),
        "inline_scripts": inline,
        "valid_same_host_link_count": len(valid_same_host_links),
        "menu_link_count": len(menu_links),
        "menu_links": menu_links[:80],
        "route_hint_count": len(route_hints),
        "route_hints": route_hints[:120],
    }


def fetch_scripts(urls: list[str]) -> list[dict]:
    rows = []
    for url in urls[:20]:
        f = curl_bytes(url)
        body = f.pop("body")
        text, enc = decode_body(body)
        hints = route_hints_from_text(text, url)
        rows.append({
            "url": url,
            **f,
            "selected_charset": enc,
            "board_term_hits": [t for t in BOARD_TERMS if t in text],
            "route_hint_count": len(hints),
            "route_hints": hints[:120],
        })
    return rows


def main() -> None:
    print("=" * 78)
    print("SEONGNAM URBAN PLANNING COMMITTEE SCRIPT / MENU ROUTE DISCOVERY - S226E")
    print("=" * 78)
    print("Purpose: recover committee board route from official scripts/menu navigation")
    print("Search request: NOT EXECUTED")
    print("UQQ700 target query: NOT EXECUTED")
    print("Committee record hit != designation notice")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    root = page_summary("root_index", ROOT_URL)
    scripts = fetch_scripts(root.get("script_srcs") or [])

    discovered = set(root.get("route_hints") or [])
    for row in scripts:
        discovered.update(row.get("route_hints") or [])
    for inline in root.get("inline_scripts") or []:
        discovered.update(route_hints_from_text(inline, ROOT_URL))
    for row in root.get("menu_links") or []:
        u = row.get("href_absolute")
        if u:
            discovered.add(u)

    bounded_urls = []
    for u in sorted(discovered):
        if urlparse(u).hostname != OFFICIAL_HOST:
            continue
        low = u.lower()
        if any(token in low for token in ("bbs", "/city/", "menu")):
            bounded_urls.append(u)
        if len(bounded_urls) >= 12:
            break

    bounded_pages = [page_summary(f"bounded_{i:02d}", u) for i, u in enumerate(bounded_urls, 1)]

    all_candidates = set(discovered)
    for p in bounded_pages:
        all_candidates.update(p.get("route_hints") or [])
        for row in p.get("menu_links") or []:
            u = row.get("href_absolute")
            if u:
                all_candidates.add(u)

    real_route_candidates = sorted({
        u for u in all_candidates
        if urlparse(u).hostname == OFFICIAL_HOST
        and not urlparse(u).fragment
        and any(tok in u.lower() for tok in ("bbslist.do", "bbsview.do", "/city/"))
        and u.rstrip("/") not in ("https://www.seongnam.go.kr/city",)
    })

    committee_signal_candidates = []
    for p in [root] + bounded_pages:
        if p.get("board_term_hits"):
            committee_signal_candidates.extend(p.get("route_hints") or [])
            committee_signal_candidates.extend([r.get("href_absolute") for r in p.get("menu_links") or [] if r.get("href_absolute")])
    for s in scripts:
        if s.get("board_term_hits"):
            committee_signal_candidates.extend(s.get("route_hints") or [])
    committee_signal_candidates = sorted(set(committee_signal_candidates))

    if real_route_candidates and committee_signal_candidates:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_SCRIPT_MENU_ROUTE_RECOVERED"
        semantic = "SEONGNAM_URBAN_PLANNING_COMMITTEE_REAL_ROUTE_RECOVERED_FROM_OFFICIAL_SCRIPT_OR_MENU_SURFACE"
        next_action = "QUALIFY_RECOVERED_ROUTE_WITH_POSITIVE_CONTROL_ONLY_BEFORE_UQQ700_QUERY"
    elif root.get("ok") and (root.get("script_src_count", 0) > 0 or root.get("valid_same_host_link_count", 0) > 0):
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_MENU_SURFACE_RECOVERED_ROUTE_UNRESOLVED"
        semantic = "SEONGNAM_OFFICIAL_MENU_AND_SCRIPT_SURFACE_QUALIFIED_BUT_COMMITTEE_ROUTE_REMAINS_UNRESOLVED"
        next_action = "EXPAND_BOUNDED_MENU_DISCOVERY_OR_RECOVER_MENU_API_WITHOUT_UQQ700_QUERY"
    else:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_SCRIPT_MENU_DISCOVERY_TECHNICAL_UNKNOWN"
        semantic = "SEONGNAM_SCRIPT_MENU_DISCOVERY_NOT_TECHNICALLY_QUALIFIED"
        next_action = "RECHECK_OFFICIAL_MENU_TRANSPORT_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-141-S226E",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "root": {k: v for k, v in root.items() if k != "inline_scripts"},
        "script_results": scripts,
        "bounded_navigation_count": len(bounded_pages),
        "bounded_pages": [{k: v for k, v in p.items() if k != "inline_scripts"} for p in bounded_pages],
        "real_route_candidate_count": len(real_route_candidates),
        "real_route_candidates": real_route_candidates[:200],
        "committee_signal_candidate_count": len(committee_signal_candidates),
        "committee_signal_candidates": committee_signal_candidates[:200],
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

    print(f"ROOT HTTP: {root.get('http')}")
    print(f"ROOT FINAL URL: {root.get('final_url')}")
    print(f"ROOT CHARSET: {root.get('selected_charset')}")
    print(f"ROOT SCRIPT SRC COUNT: {root.get('script_src_count')}")
    print(f"ROOT INLINE SCRIPT COUNT: {root.get('inline_script_count')}")
    print(f"ROOT VALID SAME-HOST LINK COUNT: {root.get('valid_same_host_link_count')}")
    print(f"ROOT MENU LINK COUNT: {root.get('menu_link_count')}")
    print(f"ROOT ROUTE HINT COUNT: {root.get('route_hint_count')}")
    print(f"SCRIPT FETCH COUNT: {len(scripts)}")
    print(f"BOUNDED NAVIGATION COUNT: {len(bounded_pages)}")
    for s in scripts:
        print(f"SCRIPT {s['url']} | HTTP={s.get('http')} | BOARD TERMS={s.get('board_term_hits')} | ROUTES={s.get('route_hint_count')}")

    print("\n" + "=" * 78)
    print("DISCOVERY SUMMARY")
    print("=" * 78)
    print(f"REAL ROUTE CANDIDATE COUNT: {len(real_route_candidates)}")
    for i, u in enumerate(real_route_candidates[:40], 1):
        print(f"REAL ROUTE [{i:02d}] {u}")
    print(f"COMMITTEE SIGNAL CANDIDATE COUNT: {len(committee_signal_candidates)}")
    for i, u in enumerate(committee_signal_candidates[:40], 1):
        print(f"COMMITTEE SIGNAL [{i:02d}] {u}")
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
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_SCRIPT_MENU_ROUTE_RECOVERED",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_MENU_SURFACE_RECOVERED_ROUTE_UNRESOLVED",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_SCRIPT_MENU_DISCOVERY_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S226E validation failed")


if __name__ == "__main__":
    main()
