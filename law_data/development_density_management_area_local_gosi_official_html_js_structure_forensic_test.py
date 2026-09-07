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

S225 = OUT_DIR / "development_density_management_area_local_gosi_official_entry_contract_forensic.json"
OUT = OUT_DIR / "development_density_management_area_local_gosi_official_html_js_structure_forensic.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "LOCAL_GOSI_OFFICIAL"
ENTRY_URL = "https://local.gosi.go.kr/klid/main/main.do"

EXPECTED_S225_CLASSIFICATIONS = {
    "LOCAL_GOSI_OFFICIAL_ENTRY_QUALIFIED_SEARCH_CONTRACT_UNRESOLVED",
    "LOCAL_GOSI_OFFICIAL_ENTRY_QUALIFIED_SEARCH_CONTRACT_PARTIAL",
    "LOCAL_GOSI_OFFICIAL_ENTRY_AND_POSITIVE_CONTROL_SEARCH_CONTRACT_QUALIFIED",
}

KEYWORDS = (
    "search", "srch", "query", "keyword", "notice", "gosi", "gonggo", "list",
    "고시", "공고", "검색", "조회", "목록",
)
URL_TOKEN_RE = re.compile(
    r'''(?P<q>["'])(?P<url>(?:https?://|/|\.\.?/)[^"']+?\.(?:do|jsp)(?:\?[^"']*)?)(?P=q)''',
    flags=re.I,
)
FUNCTION_RE = re.compile(r'''(?im)(?:function\s+([A-Za-z_$][\w$]*)\s*\(|([A-Za-z_$][\w$]*)\s*=\s*function\s*\()''')
ACTION_SET_RE = re.compile(r'''(?is)(?:\.action\s*=|setAttribute\(\s*["']action["']\s*,)\s*["']([^"']+)["']''')
LOCATION_RE = re.compile(r'''(?is)(?:location(?:\.href)?|window\.location(?:\.href)?)\s*=\s*["']([^"']+)["']''')
OPEN_RE = re.compile(r'''(?is)window\.open\(\s*["']([^"']+)["']''')
SUBMIT_RE = re.compile(r'''(?is)([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)?)\.submit\s*\(''')
AJAX_URL_RE = re.compile(r'''(?is)(?:url\s*:\s*|fetch\s*\(\s*)["']([^"']+)["']''')


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def attrs(tag: str) -> dict[str, str]:
    pairs = re.findall(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', tag, flags=re.S)
    return {k: unescape(v) for k, _, v in pairs}


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def extract_forms(html: str, base_url: str) -> list[dict]:
    result = []
    for m in re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", html):
        form_tag = "<form" + m.group(1) + ">"
        body = m.group(2)
        a = attrs(form_tag)
        fields = []
        hidden_fields = []
        controls = []

        for im in re.finditer(r"(?is)<input\b([^>]*)>", body):
            ia = attrs("<input" + im.group(1) + ">")
            item = {
                "tag": "input",
                "type": (ia.get("type") or "text").lower(),
                "name": ia.get("name"),
                "id": ia.get("id"),
                "value": ia.get("value"),
            }
            controls.append(item)
            if item["name"]:
                fields.append(item["name"])
            if item["type"] == "hidden" and item["name"]:
                hidden_fields.append({"name": item["name"], "value": item["value"]})

        for sm in re.finditer(r"(?is)<select\b([^>]*)>", body):
            sa = attrs("<select" + sm.group(1) + ">")
            controls.append({"tag": "select", "name": sa.get("name"), "id": sa.get("id")})
            if sa.get("name"):
                fields.append(sa["name"])

        for tm in re.finditer(r"(?is)<textarea\b([^>]*)>", body):
            ta = attrs("<textarea" + tm.group(1) + ">")
            controls.append({"tag": "textarea", "name": ta.get("name"), "id": ta.get("id")})
            if ta.get("name"):
                fields.append(ta["name"])

        action_raw = a.get("action")
        action_abs = urljoin(base_url, action_raw) if action_raw else base_url
        result.append({
            "method": (a.get("method") or "GET").upper(),
            "action_raw": action_raw,
            "action_absolute": action_abs,
            "id": a.get("id"),
            "name": a.get("name"),
            "class": a.get("class"),
            "onsubmit": a.get("onsubmit"),
            "fields": sorted(set(fields)),
            "hidden_fields": hidden_fields,
            "controls": controls,
            "text": clean_html(body)[:1000],
        })
    return result


def extract_scripts(html: str, base_url: str) -> list[dict]:
    scripts = []
    for idx, m in enumerate(re.finditer(r"(?is)<script\b([^>]*)>(.*?)</script>", html), 1):
        a = attrs("<script" + m.group(1) + ">")
        src = a.get("src")
        scripts.append({
            "index": idx,
            "src_raw": src,
            "src_absolute": urljoin(base_url, src) if src else None,
            "inline": m.group(2) or "",
        })
    return scripts


def extract_inline_navigation(html: str, base_url: str) -> list[dict]:
    findings = []
    for m in re.finditer(r'''(?is)(?:href|onclick)\s*=\s*(["'])(.*?)\1''', html):
        raw = unescape(m.group(2))
        if not any(k in raw.lower() for k in KEYWORDS) and not any(k in raw for k in ("고시", "공고", "검색", "조회", "목록")):
            continue
        urls = []
        for um in URL_TOKEN_RE.finditer(raw):
            urls.append(urljoin(base_url, um.group("url")))
        findings.append({"attribute": raw[:1500], "urls": sorted(set(urls))})
    return findings


def analyze_js(js_text: str, base_url: str, source: str) -> dict:
    lowered = js_text.lower()
    keyword_hits = sorted({k for k in KEYWORDS if (k in lowered if k.isascii() else k in js_text)})
    urls = []
    for m in URL_TOKEN_RE.finditer(js_text):
        urls.append(urljoin(base_url, m.group("url")))
    for pat in (ACTION_SET_RE, LOCATION_RE, OPEN_RE, AJAX_URL_RE):
        for m in pat.finditer(js_text):
            value = m.group(1)
            if value:
                urls.append(urljoin(base_url, value))

    functions = []
    for m in FUNCTION_RE.finditer(js_text):
        name = m.group(1) or m.group(2)
        if name:
            functions.append(name)

    submit_targets = sorted(set(m.group(1) for m in SUBMIT_RE.finditer(js_text)))
    interesting_lines = []
    for line_no, line in enumerate(js_text.splitlines(), 1):
        low = line.lower()
        if any(k in low for k in KEYWORDS if k.isascii()) or any(k in line for k in ("고시", "공고", "검색", "조회", "목록")) or ".action" in line or ".submit(" in line or "window.open" in line or "location" in low:
            interesting_lines.append({"line": line_no, "text": line.strip()[:1000]})
        if len(interesting_lines) >= 120:
            break

    same_host_urls = sorted({u for u in urls if urlparse(u).netloc == "local.gosi.go.kr"})
    return {
        "source": source,
        "keyword_hits": keyword_hits,
        "function_names": sorted(set(functions)),
        "submit_targets": submit_targets,
        "endpoint_hints": sorted(set(urls)),
        "same_host_endpoint_hints": same_host_urls,
        "interesting_lines": interesting_lines,
    }


def main() -> None:
    print("=" * 78)
    print("LOCAL GOSI OFFICIAL HTML/JS STRUCTURE FORENSIC - S225A")
    print("=" * 78)
    print("Purpose: recover search-screen/endpoint hints from official entry HTML and linked JS")
    print("Search request: NOT EXECUTED")
    print("Positive-control search: NOT EXECUTED")
    print("UQQ700 target query: NOT EXECUTED")
    print("Search hit != legal fact")
    print("Search no-hit != legal absence")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s225 = load(S225)
    gate_225 = (
        s225.get("classification") in EXPECTED_S225_CLASSIFICATIONS
        and (s225.get("summary") or {}).get("entry_surface_qualified") is True
        and (s225.get("summary") or {}).get("target_query_executed") is False
        and (s225.get("summary") or {}).get("legal_absence_inference_allowed") is False
        and (s225.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    if not gate_225:
        raise AssertionError("S225A prerequisite S225 gate not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    try:
        entry = session.get(ENTRY_URL, timeout=60, allow_redirects=True)
        entry_error = None
    except requests.RequestException as ex:
        entry = None
        entry_error = f"{type(ex).__name__}: {ex}"

    html = entry.text if entry is not None else ""
    base_url = entry.url if entry is not None else ENTRY_URL
    entry_ok = bool(entry is not None and entry.status_code == 200 and urlparse(base_url).netloc == "local.gosi.go.kr")

    forms = extract_forms(html, base_url)
    scripts = extract_scripts(html, base_url)
    inline_nav = extract_inline_navigation(html, base_url)

    script_analysis = []
    external_fetches = []
    for s in scripts:
        if s.get("inline"):
            script_analysis.append(analyze_js(s["inline"], base_url, f"inline:{s['index']}"))
        src = s.get("src_absolute")
        if not src:
            continue
        if urlparse(src).netloc != "local.gosi.go.kr":
            external_fetches.append({"url": src, "skipped": True, "reason": "non-local.gosi.go.kr host"})
            continue
        try:
            r = session.get(src, timeout=60, allow_redirects=True, headers={"Referer": base_url})
            external_fetches.append({
                "url": src,
                "http": r.status_code,
                "final_url": r.url,
                "body_bytes": len(r.content),
                "error": None,
            })
            if r.status_code == 200:
                script_analysis.append(analyze_js(r.text, r.url, src))
        except requests.RequestException as ex:
            external_fetches.append({
                "url": src,
                "http": None,
                "final_url": None,
                "body_bytes": 0,
                "error": f"{type(ex).__name__}: {ex}",
            })

    endpoint_hints = sorted({
        u
        for block in script_analysis
        for u in block.get("same_host_endpoint_hints") or []
        if any(k in u.lower() for k in ("search", "srch", "list", "notice", "gosi", "gonggo", "bbs", "board", "main"))
    })

    keyword_function_hints = sorted({
        fn
        for block in script_analysis
        for fn in block.get("function_names") or []
        if any(k in fn.lower() for k in ("search", "srch", "list", "notice", "gosi", "gonggo", "bbs", "board", "menu", "move", "go"))
    })

    search_contract_recovered = bool(endpoint_hints or keyword_function_hints or inline_nav)

    if entry_ok and search_contract_recovered:
        classification = "LOCAL_GOSI_OFFICIAL_HTML_JS_SEARCH_NAVIGATION_HINTS_RECOVERED"
        semantic = "LOCAL_GOSI_OFFICIAL_SEARCH_SCREEN_OR_ENDPOINT_HINTS_RECOVERED_WITHOUT_SEARCH_EXECUTION"
        next_action = "BUILD_S225B_LOCAL_GOSI_MENU_NAVIGATION_AND_SEARCH_SCREEN_CONTRACT_REPLAY_WITH_POSITIVE_CONTROL_ONLY"
    elif entry_ok:
        classification = "LOCAL_GOSI_OFFICIAL_HTML_JS_STRUCTURE_SCANNED_SEARCH_NAVIGATION_UNRESOLVED"
        semantic = "LOCAL_GOSI_OFFICIAL_HTML_JS_STRUCTURE_SCANNED_BUT_SEARCH_NAVIGATION_NOT_RECOVERED"
        next_action = "HARDEN_LOCAL_GOSI_DYNAMIC_MENU_OR_FRAME_NAVIGATION_FORENSIC"
    else:
        classification = "LOCAL_GOSI_OFFICIAL_HTML_JS_ENTRY_ACCESS_UNRESOLVED"
        semantic = "LOCAL_GOSI_OFFICIAL_HTML_JS_ENTRY_ACCESS_TECHNICAL_UNKNOWN"
        next_action = "HARDEN_LOCAL_GOSI_ENTRY_ACCESS_BEFORE_SEARCH_CONTRACT_RECOVERY"

    out = {
        "step": "STEP 17-21-C-16-8-T-139-S225A",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "prerequisite_s225_gate": gate_225,
        "entry": {
            "url": ENTRY_URL,
            "http": entry.status_code if entry is not None else None,
            "final_url": entry.url if entry is not None else None,
            "body_bytes": len(entry.content) if entry is not None else 0,
            "error": entry_error,
            "entry_ok": entry_ok,
        },
        "forms": forms,
        "scripts": [
            {k: v for k, v in s.items() if k != "inline"}
            for s in scripts
        ],
        "external_script_fetches": external_fetches,
        "inline_navigation_hints": inline_nav,
        "script_analysis": script_analysis,
        "recovered": {
            "endpoint_hints": endpoint_hints,
            "keyword_function_hints": keyword_function_hints,
            "search_contract_recovered": search_contract_recovered,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "network_entry_get_executed": True,
            "external_js_get_executed": True,
            "search_request_executed": False,
            "positive_control_search_executed": False,
            "target_query_executed": False,
            "search_hit_equals_legal_fact": False,
            "search_hit_equals_designation_identity": False,
            "search_no_hit_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "official_designation_identity_verified": False,
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("S225 GATE:", gate_225)
    print("ENTRY HTTP:", out["entry"]["http"])
    print("ENTRY OK:", entry_ok)
    print("FORM COUNT:", len(forms))
    print("SCRIPT TAG COUNT:", len(scripts))
    print("EXTERNAL SCRIPT FETCH COUNT:", len(external_fetches))
    print("INLINE NAVIGATION HINT COUNT:", len(inline_nav))
    print("RECOVERED ENDPOINT HINT COUNT:", len(endpoint_hints))
    print("RECOVERED FUNCTION HINT COUNT:", len(keyword_function_hints))
    print("SEARCH CONTRACT RECOVERED:", search_contract_recovered)
    print("CLASSIFICATION:", classification)

    print("\nFORMS")
    print(json.dumps(forms, ensure_ascii=False, indent=2))

    print("\nEXTERNAL SCRIPT FETCHES")
    print(json.dumps(external_fetches, ensure_ascii=False, indent=2))

    print("\nINLINE NAVIGATION HINTS")
    print(json.dumps(inline_nav, ensure_ascii=False, indent=2))

    print("\nRECOVERED ENDPOINT HINTS")
    for u in endpoint_hints:
        print(u)

    print("\nRECOVERED FUNCTION HINTS")
    for fn in keyword_function_hints:
        print(fn)

    print("\nSCRIPT ANALYSIS")
    for i, block in enumerate(script_analysis, 1):
        print(f"--- SCRIPT ANALYSIS {i} ---")
        print(json.dumps(block, ensure_ascii=False, indent=2))

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("Search request executed: False")
    print("Positive-control search executed: False")
    print("Target query executed: False")
    print("Search no-hit equals legal absence: False")
    print("Negative evidence allowed: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S225 prerequisite gate": gate_225,
        "entry GET classified": entry is not None or entry_error is not None,
        "response classified": classification in {
            "LOCAL_GOSI_OFFICIAL_HTML_JS_SEARCH_NAVIGATION_HINTS_RECOVERED",
            "LOCAL_GOSI_OFFICIAL_HTML_JS_STRUCTURE_SCANNED_SEARCH_NAVIGATION_UNRESOLVED",
            "LOCAL_GOSI_OFFICIAL_HTML_JS_ENTRY_ACCESS_UNRESOLVED",
        },
        "search request not executed": out["summary"]["search_request_executed"] is False,
        "positive control search not executed": out["summary"]["positive_control_search_executed"] is False,
        "target query not executed": out["summary"]["target_query_executed"] is False,
        "search hit not legal fact": out["summary"]["search_hit_equals_legal_fact"] is False,
        "search hit not designation identity": out["summary"]["search_hit_equals_designation_identity"] is False,
        "search no-hit not legal absence": out["summary"]["search_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["official_designation_identity_verified"] is False,
        "current validity not promoted": out["current_validity_verified"] is False,
        "site inclusion not promoted": out["site_spatial_inclusion_verified"] is False,
        "SITE promotion blocked": not out["site_positive_allowed"] and not out["site_negative_allowed"],
        "runtime registration blocked": out["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nVALIDATION")
    for name, value in checks.items():
        print(f"{name}: {value}")
    print("all_pass:", all(checks.values()))

    if not all(checks.values()):
        raise AssertionError("S225A local.gosi.go.kr HTML/JS structure forensic failed")


if __name__ == "__main__":
    main()
