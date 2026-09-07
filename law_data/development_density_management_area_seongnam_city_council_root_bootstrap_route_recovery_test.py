# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urljoin, urlparse

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_council_root_bootstrap_route_recovery.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_COUNCIL_OFFICIAL_RECORD"
ROOT = "https://www.sncouncil.go.kr/"

FAMILY_KEYWORDS = {
    "MINUTES": ["회의록", "회의", "본회의", "상임위원회", "minutes"],
    "AGENDA": ["의안", "안건", "의안정보", "agenda", "bill"],
    "ORDINANCE": ["조례", "규칙", "자치법규", "ordinance"],
    "SEARCH": ["통합검색", "검색", "자료검색", "search"],
}

URL_PATTERNS = [
    ("iframe", re.compile(r'(?is)<iframe\b[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']')),
    ("frame", re.compile(r'(?is)<frame\b[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']')),
    ("meta_refresh", re.compile(r'(?is)<meta\b[^>]*http-equiv\s*=\s*["\']?refresh["\']?[^>]*content\s*=\s*["\'][^"\']*?url\s*=\s*([^"\';>]+)')),
    ("meta_refresh_reverse", re.compile(r'(?is)<meta\b[^>]*content\s*=\s*["\'][^"\']*?url\s*=\s*([^"\';>]+)["\'][^>]*http-equiv\s*=\s*["\']?refresh["\']?')),
    ("js_location", re.compile(r'(?is)(?:window\.|document\.)?location(?:\.href)?\s*=\s*["\']([^"\']+)["\']')),
    ("js_location_replace", re.compile(r'(?is)(?:window\.|document\.)?location\.replace\s*\(\s*["\']([^"\']+)["\']\s*\)')),
    ("window_open", re.compile(r'(?is)window\.open\s*\(\s*["\']([^"\']+)["\']')),
    ("base_href", re.compile(r'(?is)<base\b[^>]*\bhref\s*=\s*["\']([^"\']+)["\']')),
    ("form_action", re.compile(r'(?is)<form\b[^>]*\baction\s*=\s*["\']([^"\']+)["\']')),
    ("anchor", re.compile(r'(?is)<a\b[^>]*\bhref\s*=\s*["\']([^"\']+)["\']')),
]


def curl(url: str, referer: str | None = None) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"http": None, "final_url": None, "content_type": None, "redirects": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "120",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    ]
    if referer:
        cmd += ["-e", referer]
    cmd += ["-w", "\n__META__%{http_code}|%{url_effective}|%{content_type}|%{num_redirects}", url]
    p = subprocess.run(cmd, capture_output=True)
    raw = p.stdout or b""
    marker = b"\n__META__"
    if marker in raw:
        body, meta = raw.rsplit(marker, 1)
        parts = meta.decode("utf-8", errors="replace").strip().split("|", 3)
        http = parts[0] if parts else None
        final_url = parts[1] if len(parts) > 1 else None
        content_type = parts[2] if len(parts) > 2 else None
        redirects = parts[3] if len(parts) > 3 else None
    else:
        body, http, final_url, content_type, redirects = raw, None, None, None, None
    return {
        "http": http,
        "final_url": final_url,
        "content_type": content_type,
        "redirects": redirects,
        "body": body,
        "stderr": (p.stderr or b"").decode("utf-8", errors="replace").strip(),
    }


def decode(body: bytes) -> str:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            return body.decode(enc)
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", errors="replace")


def strip_tags(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s)
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def same_host(url: str, root_host: str) -> bool:
    try:
        h = urlparse(url).hostname or ""
        return h == root_host or h.endswith("." + root_host) or root_host.endswith("." + h)
    except Exception:
        return False


def normalize_candidate(base_url: str, raw: str) -> str | None:
    raw = html.unescape(raw).strip().strip('"\' ')
    if not raw or raw.startswith(("javascript:", "mailto:", "tel:", "#")):
        return None
    if raw.lower().startswith("url="):
        raw = raw[4:].strip()
    return urljoin(base_url, raw)


def extract_bootstrap_routes(base_url: str, text: str, root_host: str) -> list[dict]:
    rows = []
    seen = set()
    for source, pat in URL_PATTERNS:
        for raw in pat.findall(text):
            url = normalize_candidate(base_url, raw)
            if not url or not same_host(url, root_host):
                continue
            key = (source, url)
            if key in seen:
                continue
            seen.add(key)
            rows.append({"source": source, "raw": raw, "url": url})

    # Also inspect quoted path-like literals in tiny bootstrap scripts, but only official-host resolved paths.
    for raw in re.findall(r'(?is)["\']((?:/|\.\.?/)[^"\']{1,300})["\']', text):
        url = normalize_candidate(base_url, raw)
        if not url or not same_host(url, root_host):
            continue
        key = ("quoted_path_literal", url)
        if key not in seen:
            seen.add(key)
            rows.append({"source": "quoted_path_literal", "raw": raw, "url": url})
    return rows


def classify_record_routes(base_url: str, text: str, root_host: str) -> list[dict]:
    rows = []
    seen = set()
    pat = re.compile(r'(?is)<a\b([^>]*)href\s*=\s*["\']([^"\']+)["\']([^>]*)>(.*?)</a>')
    for a1, href, a2, label_html in pat.findall(text):
        url = normalize_candidate(base_url, href)
        if not url or not same_host(url, root_host):
            continue
        label = strip_tags(label_html)
        attrs = f"{a1} {a2}"
        context = f"{label} {attrs} {url}".lower()
        families = [name for name, kws in FAMILY_KEYWORDS.items() if any(k.lower() in context for k in kws)]
        if not families:
            continue
        key = url
        if key in seen:
            continue
        seen.add(key)
        rows.append({"url": url, "label": label, "families": families})
    return rows


def page_title(text: str) -> str | None:
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", text)
    return strip_tags(m.group(1)) if m else None


def landing_score(row: dict) -> int:
    score = 0
    if row.get("http") == "200":
        score += 5
    if row.get("official_signal"):
        score += 4
    if row.get("body_size", 0) > 5000:
        score += 3
    score += min(row.get("record_family_route_count", 0), 6)
    if row.get("url") != ROOT:
        score += 1
    return score


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY COUNCIL ROOT BOOTSTRAP / ROUTE RECOVERY - S228B")
    print("=" * 78)
    print("Purpose: recover actual council landing page and record-family routes from the tiny official root bootstrap")
    print("UQQ700 target search: DISABLED")
    print("Only official-host bootstrap/frame/meta-refresh/JS/form routes are followed")
    print("Council route failure != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    rr = curl(ROOT)
    root_text = decode(rr.get("body") or b"")
    root_host = urlparse(rr.get("final_url") or ROOT).hostname or "www.sncouncil.go.kr"
    root_plain = strip_tags(root_text)
    root_official = "성남시의회" in root_plain or "성남시 의회" in root_plain or "성남시의회" in root_text

    bootstrap = extract_bootstrap_routes(rr.get("final_url") or ROOT, root_text, root_host)
    # Do not waste calls on the root itself or duplicate normalized URLs. Keep bounded.
    probe_urls = []
    seen = set()
    for row in bootstrap:
        u = row["url"]
        if u.rstrip("/") == (rr.get("final_url") or ROOT).rstrip("/"):
            continue
        if u not in seen:
            seen.add(u)
            probe_urls.append(u)
    probe_urls = probe_urls[:20]

    probed_pages = []
    all_record_routes = []
    route_seen = set()
    for url in probe_urls:
        pr = curl(url, referer=rr.get("final_url") or ROOT)
        text = decode(pr.get("body") or b"")
        plain = strip_tags(text)
        record_routes = classify_record_routes(pr.get("final_url") or url, text, root_host) if pr.get("http") == "200" else []
        official_signal = any(k in (plain + " " + text) for k in ["성남시의회", "성남시 의회"])
        page = {
            "url": url,
            "http": pr.get("http"),
            "final_url": pr.get("final_url"),
            "content_type": pr.get("content_type"),
            "redirects": pr.get("redirects"),
            "body_size": len(pr.get("body") or b""),
            "title": page_title(text),
            "official_signal": official_signal,
            "record_family_route_count": len(record_routes),
            "record_family_routes": record_routes,
        }
        page["score"] = landing_score(page)
        probed_pages.append(page)
        for r in record_routes:
            if r["url"] not in route_seen:
                route_seen.add(r["url"])
                all_record_routes.append(r)

    # If no bootstrap child was usable, root itself remains a technical bootstrap page, not a landing qualification.
    selected = None
    usable = [p for p in probed_pages if p.get("http") == "200" and p.get("official_signal") and p.get("body_size", 0) > len(rr.get("body") or b"")]
    if usable:
        selected = sorted(usable, key=lambda x: (x.get("score", 0), x.get("body_size", 0)), reverse=True)[0]

    families = sorted({f for r in all_record_routes for f in r.get("families", [])})
    family_map = {name: [] for name in FAMILY_KEYWORDS}
    for r in all_record_routes:
        for fam in r.get("families", []):
            family_map.setdefault(fam, []).append(r)

    bootstrap_route_found = len(bootstrap) > 0
    landing_qualified = selected is not None
    record_family_route_found = len(all_record_routes) > 0

    if landing_qualified and record_family_route_found:
        classification = "SEONGNAM_CITY_COUNCIL_ROOT_BOOTSTRAP_ROUTE_QUALIFIED"
        semantic = "OFFICIAL_ROOT_BOOTSTRAP_WAS_RESOLVED_TO_A_USABLE_COUNCIL_LANDING_PAGE_WITH_RECORD_FAMILY_ROUTES"
        next_action = "QUALIFY_POSITIVE_CONTROL_SEARCH_CONTRACTS_ON_RECOVERED_COUNCIL_RECORD_FAMILY_ROUTES_BEFORE_UQQ700_TARGET_SEARCH"
    elif bootstrap_route_found:
        classification = "SEONGNAM_CITY_COUNCIL_ROOT_BOOTSTRAP_ROUTE_PARTIALLY_RECOVERED_TECHNICAL_UNKNOWN"
        semantic = "ONE_OR_MORE_OFFICIAL_BOOTSTRAP_ROUTES_WERE_RECOVERED_BUT_A_USABLE_RECORD_FAMILY_LANDING_SURFACE_WAS_NOT_YET_QUALIFIED"
        next_action = "HARDEN_ONLY_RECOVERED_BOOTSTRAP_CHILD_ROUTES_OR_CLIENT_SIDE_NAVIGATION_WITHOUT_UQQ700_NEGATIVE_INFERENCE"
    else:
        classification = "SEONGNAM_CITY_COUNCIL_ROOT_BOOTSTRAP_ROUTE_TECHNICAL_UNKNOWN"
        semantic = "THE_OFFICIAL_ROOT_REMAINED_A_TINY_BOOTSTRAP_PAGE_WITHOUT_A_RECOVERED_OFFICIAL_CHILD_ROUTE"
        next_action = "FORENSICALLY_INSPECT_ROOT_BOOTSTRAP_HTML_HEADERS_AND_SCRIPT_LITERALS_WITHOUT_TARGET_SEARCH_OR_LEGAL_ABSENCE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-158-S228B",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "root": {
            "url": ROOT,
            "http": rr.get("http"),
            "final_url": rr.get("final_url"),
            "content_type": rr.get("content_type"),
            "redirects": rr.get("redirects"),
            "body_size": len(rr.get("body") or b""),
            "official_signal": root_official,
            "title": page_title(root_text),
            "html_sample": root_text[:3000],
        },
        "bootstrap_routes": bootstrap,
        "probed_pages": probed_pages,
        "selected_landing_page": selected,
        "record_family_routes": all_record_routes,
        "record_family_types_observed": families,
        "record_family_route_map": family_map,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "bootstrap_route_found": bootstrap_route_found,
            "landing_page_qualified": landing_qualified,
            "record_family_route_found": record_family_route_found,
            "target_search_executed": False,
            "council_record_hit_equals_designation_notice": False,
            "council_record_hit_equals_current_validity": False,
            "council_record_hit_equals_site_inclusion": False,
            "council_route_failure_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "official_designation_identity_verified": False,
            "current_validity_verified": False,
            "site_spatial_inclusion_verified": False,
            "runtime_registration_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nROOT BOOTSTRAP")
    print("-" * 78)
    print(f"ROOT HTTP: {rr.get('http')}")
    print(f"ROOT FINAL URL: {rr.get('final_url')}")
    print(f"ROOT BODY SIZE: {len(rr.get('body') or b'')}")
    print(f"ROOT OFFICIAL SIGNAL: {root_official}")
    print(f"ROOT TITLE: {page_title(root_text)}")

    print("\nBOOTSTRAP ROUTES")
    print("-" * 78)
    for r in bootstrap:
        print(json.dumps(r, ensure_ascii=False))

    print("\nPROBED LANDING CANDIDATES")
    print("-" * 78)
    for p in probed_pages:
        print(json.dumps({k: p.get(k) for k in ["url", "http", "final_url", "body_size", "title", "official_signal", "record_family_route_count", "score"]}, ensure_ascii=False))

    print("\nRECORD FAMILY ROUTES")
    print("-" * 78)
    for fam in ["MINUTES", "AGENDA", "ORDINANCE", "SEARCH"]:
        print(f"{fam}:")
        for r in family_map.get(fam, []):
            print("  " + json.dumps(r, ensure_ascii=False))

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"SELECTED LANDING PAGE: {selected.get('final_url') if selected else None}")
    print(f"LANDING HTTP: {selected.get('http') if selected else None}")
    print(f"LANDING BODY SIZE: {selected.get('body_size') if selected else None}")
    print(f"RECORD FAMILY TYPES OBSERVED: {families}")
    print(f"RECORD FAMILY ROUTE COUNT: {len(all_record_routes)}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Target UQQ700 search executed: False")
    print("Council route failure == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "root fetched": rr.get("http") == "200",
        "root official signal": root_official,
        "bootstrap probe bounded": len(probe_urls) <= 20,
        "target search not executed": out["summary"]["target_search_executed"] is False,
        "council hit not designation": out["summary"]["council_record_hit_equals_designation_notice"] is False,
        "council hit not validity": out["summary"]["council_record_hit_equals_current_validity"] is False,
        "council hit not site inclusion": out["summary"]["council_record_hit_equals_site_inclusion"] is False,
        "route failure not legal absence": out["summary"]["council_route_failure_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "SEONGNAM_CITY_COUNCIL_ROOT_BOOTSTRAP_ROUTE_QUALIFIED",
            "SEONGNAM_CITY_COUNCIL_ROOT_BOOTSTRAP_ROUTE_PARTIALLY_RECOVERED_TECHNICAL_UNKNOWN",
            "SEONGNAM_CITY_COUNCIL_ROOT_BOOTSTRAP_ROUTE_TECHNICAL_UNKNOWN",
        },
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for k, v in validation.items():
        print(f"{k}: {v}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT}")

    if not all(validation.values()):
        raise AssertionError("S228B validation failed")


if __name__ == "__main__":
    main()
