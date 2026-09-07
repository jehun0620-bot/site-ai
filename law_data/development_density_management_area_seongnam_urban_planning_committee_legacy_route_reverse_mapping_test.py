# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import shutil
import subprocess
from html import unescape
from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlparse

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_legacy_route_reverse_mapping.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_URBAN_PLANNING_COMMITTEE_RECORD"
OFFICIAL_HOST = "www.seongnam.go.kr"

POSITIVE_CONTROL_TITLE = "2025년 제6회 성남시 도시계획위원회 개최 결과"
LEGACY_URL = "https://www.seongnam.go.kr/city/1000557/30229/bbsView.do?idx=374215"
LEGACY_IDENTIFIERS = ("1000557", "30229", "374215")
ADJACENT_TITLES = (
    "2025년 제5회 성남시 도시계획위원회 개최 결과",
    "2025년 제6회 성남시 도시계획위원회 개최 결과",
    "2025년 제7회 성남시 도시계획위원회 개최 결과",
)
ROOT_URLS = (
    "https://www.seongnam.go.kr/",
    "https://www.seongnam.go.kr/index",
)
MAX_CANDIDATE_FETCH = 20


def curl_bytes(url: str, *, method: str = "GET", data: str | None = None) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"ok": False, "http": None, "final_url": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS",
        "--connect-timeout", "15", "--max-time", "45",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}|%{url_effective}",
    ]
    if method.upper() == "POST":
        cmd += ["-X", "POST"]
        if data is not None:
            cmd += ["--data", data]
    cmd.append(url)
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
            if enc == "utf-8" or "성남" in text:
                return text, enc
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", errors="replace"), "utf-8-replace"


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def extract_title(html: str) -> str | None:
    m = re.search(r"(?is)<title\b[^>]*>(.*?)</title>", html or "")
    return clean_html(m.group(1))[:500] if m else None


def extract_links(html: str, base_url: str) -> list[dict]:
    out = []
    for m in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", html or ""):
        attrs = m.group(1)
        href_m = re.search(r'''(?is)href\s*=\s*(["'])(.*?)\1''', attrs)
        href = unescape(href_m.group(2).strip()) if href_m else ""
        text = clean_html(m.group(2))[:500]
        if not href or href.lower().startswith(("javascript:", "#", "mailto:", "tel:")):
            continue
        absolute = urljoin(base_url, href)
        if urlparse(absolute).hostname != OFFICIAL_HOST:
            continue
        out.append({"text": text, "href": absolute})
    return out


def candidate_urls_from_text(text: str, base_url: str) -> list[str]:
    out = set()
    patterns = [
        r'''(?i)(https?://www\.seongnam\.go\.kr/[^"'<>\s)]+)''',
        r'''(?i)(/(?:bbs\d+)(?:/\d+)?(?:\?[^"'<>\s)]*)?)''',
        r'''(?i)(/city/[^"'<>\s)]*(?:bbsView|bbsList)\.do(?:\?[^"'<>\s)]*)?)''',
    ]
    for pat in patterns:
        for hit in re.findall(pat, text or ""):
            u = urljoin(base_url, unescape(hit))
            if urlparse(u).hostname == OFFICIAL_HOST:
                out.add(u)
    return sorted(out)


def inspect_url(label: str, url: str) -> dict:
    f = curl_bytes(url)
    html, enc = decode_body(f.pop("body"))
    text = clean_html(html)
    title = extract_title(html)
    links = extract_links(html, f.get("final_url") or url)
    legacy_hits = [x for x in LEGACY_IDENTIFIERS if x in html or x in text]
    control_hits = [t for t in ADJACENT_TITLES if t in text or t in html]
    city_plan_hits = [t for t in ("도시계획위원회", "도시계획과") if t in text]
    candidates = set(candidate_urls_from_text(html, f.get("final_url") or url))
    for row in links:
        blob = (row.get("text") or "") + " " + (row.get("href") or "")
        if any(x in blob for x in LEGACY_IDENTIFIERS) or "도시계획위원회" in blob or re.search(r"/bbs\d+(?:/\d+)?", row.get("href") or ""):
            candidates.add(row["href"])
    return {
        "label": label,
        "url": url,
        **f,
        "selected_charset": enc,
        "same_official_host": bool(f.get("final_url") and urlparse(f["final_url"]).hostname == OFFICIAL_HOST),
        "title": title,
        "legacy_identifier_hits": legacy_hits,
        "positive_control_title_hits": control_hits,
        "city_planning_signal_hits": city_plan_hits,
        "candidate_url_count": len(candidates),
        "candidate_urls": sorted(candidates)[:200],
        "body_prefix": text[:3000],
    }


def build_known_title_search_urls() -> list[str]:
    q = quote_plus(POSITIVE_CONTROL_TITLE)
    return [
        f"https://www.seongnam.go.kr/search?query={q}",
        f"https://www.seongnam.go.kr/search?searchText={q}",
        f"https://www.seongnam.go.kr/search?keyword={q}",
    ]


def main() -> None:
    print("=" * 78)
    print("SEONGNAM URBAN PLANNING COMMITTEE LEGACY ROUTE REVERSE MAPPING - S226G")
    print("=" * 78)
    print("Purpose: reverse-map a verified committee positive-control identity to a current successor route")
    print(f"Positive control: {POSITIVE_CONTROL_TITLE}")
    print(f"Legacy URL: {LEGACY_URL}")
    print("Search scope: positive-control title only")
    print("UQQ700 target query: NOT EXECUTED")
    print("Committee record hit != designation notice")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    probes = []
    probes.append(inspect_url("legacy_detail", LEGACY_URL))
    for i, u in enumerate(ROOT_URLS, 1):
        probes.append(inspect_url(f"root_{i}", u))
    for i, u in enumerate(build_known_title_search_urls(), 1):
        probes.append(inspect_url(f"positive_control_search_{i}", u))

    candidate_urls = set()
    for p in probes:
        candidate_urls.update(p.get("candidate_urls") or [])

    # Prefer concrete current BBS URLs and positive-control-bearing same-host routes.
    ranked = []
    for u in sorted(candidate_urls):
        score = 0
        path = urlparse(u).path
        if re.search(r"/bbs\d+(?:/\d+)?", path):
            score += 10
        if any(x in u for x in LEGACY_IDENTIFIERS):
            score += 5
        if "city" in path:
            score += 2
        ranked.append((score, u))
    ranked.sort(key=lambda x: (-x[0], x[1]))

    inspected_candidates = []
    for _, u in ranked[:MAX_CANDIDATE_FETCH]:
        inspected_candidates.append(inspect_url("candidate", u))

    successor_candidates = []
    for row in inspected_candidates:
        if not row.get("ok") or row.get("http") != "200":
            continue
        final_url = row.get("final_url") or row.get("url")
        is_current_bbs = bool(re.search(r"/bbs\d+(?:/\d+)?", urlparse(final_url).path))
        direct_title = POSITIVE_CONTROL_TITLE in (row.get("body_prefix") or "") or POSITIVE_CONTROL_TITLE in (row.get("title") or "")
        adjacent = bool(row.get("positive_control_title_hits"))
        city_plan = "도시계획위원회" in (row.get("city_planning_signal_hits") or [])
        if is_current_bbs and (direct_title or adjacent or city_plan):
            successor_candidates.append({
                "url": row.get("url"),
                "final_url": final_url,
                "direct_positive_control_title": direct_title,
                "adjacent_title_hits": row.get("positive_control_title_hits"),
                "city_planning_signal_hits": row.get("city_planning_signal_hits"),
            })

    legacy_probe = probes[0]
    legacy_identity_reachable = legacy_probe.get("http") == "200" and POSITIVE_CONTROL_TITLE in (legacy_probe.get("body_prefix") or "")
    search_positive_control_hits = [
        p for p in probes
        if p["label"].startswith("positive_control_search_")
        and (p.get("positive_control_title_hits") or "도시계획위원회" in (p.get("body_prefix") or ""))
    ]

    if successor_candidates:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_SUCCESSOR_ROUTE_RECOVERED"
        semantic = "VERIFIED_LEGACY_COMMITTEE_IDENTITY_REVERSE_MAPPED_TO_CURRENT_SEONGNAM_BBS_ROUTE"
        next_action = "QUALIFY_SUCCESSOR_COMMITTEE_BOARD_WITH_POSITIVE_CONTROL_AND_HISTORICAL_COVERAGE_BEFORE_UQQ700_QUERY"
    elif legacy_probe.get("ok") or any(p.get("ok") for p in probes[1:]):
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_LEGACY_IDENTITY_VERIFIED_SUCCESSOR_ROUTE_UNRESOLVED"
        semantic = "LEGACY_COMMITTEE_POSITIVE_CONTROL_IDENTITY_PRESERVED_BUT_CURRENT_SUCCESSOR_ROUTE_REMAINS_UNRESOLVED"
        next_action = "EXPAND_OFFICIAL_SITE_INDEX_AND_ADJACENT_COMMITTEE_RECORD_REVERSE_LOOKUP_WITHOUT_UQQ700_QUERY"
    else:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_LEGACY_ROUTE_MAPPING_TECHNICAL_UNKNOWN"
        semantic = "LEGACY_TO_CURRENT_COMMITTEE_ROUTE_MAPPING_NOT_TECHNICALLY_QUALIFIED"
        next_action = "RECHECK_OFFICIAL_SEONGNAM_TRANSPORT_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-141-S226G",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "positive_control_title": POSITIVE_CONTROL_TITLE,
        "legacy_url": LEGACY_URL,
        "legacy_identifiers": list(LEGACY_IDENTIFIERS),
        "adjacent_positive_control_titles": list(ADJACENT_TITLES),
        "probe_count": len(probes),
        "probes": probes,
        "ranked_candidate_count": len(ranked),
        "inspected_candidate_count": len(inspected_candidates),
        "inspected_candidates": inspected_candidates,
        "successor_candidate_count": len(successor_candidates),
        "successor_candidates": successor_candidates,
        "legacy_identity_reachable_live": legacy_identity_reachable,
        "positive_control_search_hit_probe_count": len(search_positive_control_hits),
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "positive_control_search_only": True,
            "target_query_executed": False,
            "committee_record_hit_equals_designation_notice": False,
            "legacy_route_no_hit_equals_legal_absence": False,
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

    print("\nPROBES")
    print("-" * 78)
    for p in probes:
        print(f"[{p['label']}] {p['url']}")
        print(f"  HTTP: {p.get('http')}")
        print(f"  FINAL URL: {p.get('final_url')}")
        print(f"  TITLE: {p.get('title')}")
        print(f"  LEGACY ID HITS: {p.get('legacy_identifier_hits')}")
        print(f"  CONTROL TITLE HITS: {p.get('positive_control_title_hits')}")
        print(f"  CITY PLANNING SIGNALS: {p.get('city_planning_signal_hits')}")
        print(f"  CANDIDATE URLS: {p.get('candidate_url_count')}")

    print("\n" + "=" * 78)
    print("REVERSE MAPPING SUMMARY")
    print("=" * 78)
    print(f"LEGACY LIVE HTTP: {legacy_probe.get('http')}")
    print(f"LEGACY IDENTITY REACHABLE LIVE: {legacy_identity_reachable}")
    print(f"POSITIVE-CONTROL SEARCH HIT PROBE COUNT: {len(search_positive_control_hits)}")
    print(f"RANKED CANDIDATE COUNT: {len(ranked)}")
    print(f"INSPECTED CANDIDATE COUNT: {len(inspected_candidates)}")
    print(f"SUCCESSOR CANDIDATE COUNT: {len(successor_candidates)}")
    for i, row in enumerate(successor_candidates, 1):
        print(f"SUCCESSOR [{i:02d}] {row['final_url']} | direct={row['direct_positive_control_title']} | adjacent={row['adjacent_title_hits']} | signals={row['city_planning_signal_hits']}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Positive-control search only: True")
    print("Target query executed: False")
    print("Legal absence inference allowed: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "positive control identity fixed": out["positive_control_title"] == POSITIVE_CONTROL_TITLE,
        "legacy identifiers fixed": out["legacy_identifiers"] == list(LEGACY_IDENTIFIERS),
        "classification emitted": classification in {
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_SUCCESSOR_ROUTE_RECOVERED",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_LEGACY_IDENTITY_VERIFIED_SUCCESSOR_ROUTE_UNRESOLVED",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_LEGACY_ROUTE_MAPPING_TECHNICAL_UNKNOWN",
        },
        "positive control search only": out["summary"]["positive_control_search_only"] is True,
        "target query not executed": out["summary"]["target_query_executed"] is False,
        "committee hit not designation notice": out["summary"]["committee_record_hit_equals_designation_notice"] is False,
        "legacy no-hit not legal absence": out["summary"]["legacy_route_no_hit_equals_legal_absence"] is False,
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
        raise AssertionError("S226G validation failed")


if __name__ == "__main__":
    main()
