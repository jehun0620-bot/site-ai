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
S225A = OUT_DIR / "development_density_management_area_local_gosi_official_html_js_structure_forensic.json"
OUT = OUT_DIR / "development_density_management_area_local_gosi_official_nf_form_entry_gate_replay.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "LOCAL_GOSI_OFFICIAL"
ENTRY_URL = "https://local.gosi.go.kr/klid/main/main.do"

EXPECTED_S225A = "LOCAL_GOSI_OFFICIAL_HTML_JS_SEARCH_NAVIGATION_HINTS_RECOVERED"


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
    forms = []
    for m in re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", html):
        a = attrs("<form" + m.group(1) + ">")
        body = m.group(2)
        controls = []
        payload = {}
        for im in re.finditer(r"(?is)<input\b([^>]*)>", body):
            ia = attrs("<input" + im.group(1) + ">")
            item = {
                "type": (ia.get("type") or "text").lower(),
                "name": ia.get("name"),
                "id": ia.get("id"),
                "value": ia.get("value"),
            }
            controls.append(item)
            if item["name"] and item["type"] == "hidden":
                payload[item["name"]] = item["value"] or ""
        action_raw = a.get("action")
        forms.append({
            "id": a.get("id"),
            "name": a.get("name"),
            "method": (a.get("method") or "GET").upper(),
            "action_raw": action_raw,
            "action_absolute": urljoin(base_url, action_raw) if action_raw else base_url,
            "controls": controls,
            "hidden_payload": payload,
            "text": clean_html(body)[:1000],
        })
    return forms


def extract_scripts(html: str, base_url: str) -> list[str]:
    result = []
    for m in re.finditer(r"(?is)<script\b([^>]*)>", html):
        a = attrs("<script" + m.group(1) + ">")
        if a.get("src"):
            result.append(urljoin(base_url, a["src"]))
    return sorted(set(result))


def extract_navigation(html: str, base_url: str) -> list[dict]:
    result = []
    for m in re.finditer(r'''(?is)<a\b([^>]*)>(.*?)</a>''', html):
        a = attrs("<a" + m.group(1) + ">")
        href = a.get("href")
        onclick = a.get("onclick")
        text = clean_html(m.group(2))[:300]
        if not (href or onclick or text):
            continue
        result.append({
            "text": text,
            "href_raw": href,
            "href_absolute": urljoin(base_url, href) if href and not href.lower().startswith("javascript:") else None,
            "onclick": onclick,
        })
    return result[:500]


def page_signals(html: str, base_url: str) -> dict:
    text = clean_html(html)
    forms = extract_forms(html, base_url)
    scripts = extract_scripts(html, base_url)
    nav = extract_navigation(html, base_url)
    search_terms = [x for x in ("검색", "조회", "고시", "공고", "search", "keyword") if x.lower() in text.lower()]
    nf_forms = [f for f in forms if f.get("id") == "nfForm" or "nf_token" in (f.get("hidden_payload") or {})]
    non_nf_forms = [f for f in forms if f not in nf_forms]
    return {
        "text_length": len(text),
        "text_prefix": text[:1500],
        "form_count": len(forms),
        "nf_form_count": len(nf_forms),
        "non_nf_form_count": len(non_nf_forms),
        "forms": forms,
        "script_count": len(scripts),
        "scripts": scripts,
        "navigation_count": len(nav),
        "navigation_sample": nav[:100],
        "search_or_notice_terms": search_terms,
        "application_surface_signal": bool(non_nf_forms or nav or any(x in text for x in ("고시", "공고", "검색", "조회"))),
    }


def main() -> None:
    print("=" * 78)
    print("LOCAL GOSI OFFICIAL nfForm ENTRY-GATE REPLAY - S225B")
    print("=" * 78)
    print("Purpose: replay only the official nfForm gate in the same session and inspect post-gate surface")
    print("Search request: NOT EXECUTED")
    print("Positive-control search: NOT EXECUTED")
    print("UQQ700 target query: NOT EXECUTED")
    print("S225A generic-library function hints: DIAGNOSTIC ONLY")
    print("Search hit != legal fact")
    print("Search no-hit != legal absence")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s225 = load(S225)
    s225a = load(S225A)
    gate_225 = (
        (s225.get("summary") or {}).get("entry_surface_qualified") is True
        and (s225.get("summary") or {}).get("target_query_executed") is False
        and (s225.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    gate_225a = (
        s225a.get("classification") == EXPECTED_S225A
        and (s225a.get("summary") or {}).get("search_request_executed") is False
        and (s225a.get("summary") or {}).get("target_query_executed") is False
        and (s225a.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    if not (gate_225 and gate_225a):
        raise AssertionError("S225B prerequisite gate not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    entry = None
    entry_error = None
    try:
        entry = session.get(ENTRY_URL, timeout=60, allow_redirects=True)
    except requests.RequestException as ex:
        entry_error = f"{type(ex).__name__}: {ex}"

    entry_html = entry.text if entry is not None else ""
    entry_url = entry.url if entry is not None else ENTRY_URL
    entry_forms = extract_forms(entry_html, entry_url)
    nf_candidates = [
        f for f in entry_forms
        if f.get("id") == "nfForm" and "nf_token" in (f.get("hidden_payload") or {})
    ]

    replay_attempted = False
    replay = None
    replay_error = None
    selected_form = nf_candidates[0] if len(nf_candidates) == 1 else None

    if selected_form:
        action = selected_form["action_absolute"]
        official_action = urlparse(action).netloc == "local.gosi.go.kr"
        method_post = selected_form.get("method") == "POST"
        payload_keys = sorted((selected_form.get("hidden_payload") or {}).keys())
        exact_safe_payload = payload_keys == ["nf_token"]
        if official_action and method_post and exact_safe_payload:
            replay_attempted = True
            try:
                replay = session.post(
                    action,
                    data=selected_form["hidden_payload"],
                    timeout=60,
                    allow_redirects=True,
                    headers={"Referer": entry_url},
                )
            except requests.RequestException as ex:
                replay_error = f"{type(ex).__name__}: {ex}"

    post_html = replay.text if replay is not None else ""
    post_url = replay.url if replay is not None else None
    entry_signals = page_signals(entry_html, entry_url) if entry is not None else {}
    post_signals = page_signals(post_html, post_url or ENTRY_URL) if replay is not None else {}

    same_official_host = bool(post_url and urlparse(post_url).netloc == "local.gosi.go.kr")
    post_http_ok = bool(replay is not None and replay.status_code == 200 and same_official_host)
    escaped_gate = bool(
        post_http_ok
        and (
            (post_signals.get("nf_form_count") or 0) == 0
            or (post_signals.get("non_nf_form_count") or 0) > 0
            or (post_signals.get("navigation_count") or 0) > (entry_signals.get("navigation_count") or 0)
            or post_signals.get("application_surface_signal") is True
        )
    )

    if post_http_ok and escaped_gate:
        classification = "LOCAL_GOSI_OFFICIAL_NF_FORM_ENTRY_GATE_REPLAY_APPLICATION_SURFACE_RECOVERED"
        semantic = "LOCAL_GOSI_OFFICIAL_NF_FORM_GATE_REPLAY_RECOVERED_POST_GATE_APPLICATION_SURFACE"
        next_action = "BUILD_S225C_POST_GATE_MENU_AND_SEARCH_SCREEN_CONTRACT_FORENSIC_WITHOUT_UQQ700_QUERY"
    elif post_http_ok:
        classification = "LOCAL_GOSI_OFFICIAL_NF_FORM_ENTRY_GATE_REPLAY_STILL_GATED_OR_UNRESOLVED"
        semantic = "LOCAL_GOSI_OFFICIAL_NF_FORM_REPLAY_RETURNED_OFFICIAL_HTML_BUT_APPLICATION_SURFACE_NOT_VERIFIED"
        next_action = "FORENSICALLY_COMPARE_PRE_POST_GATE_HTML_SESSION_AND_NETFUNNEL_STATE"
    elif replay_attempted:
        classification = "LOCAL_GOSI_OFFICIAL_NF_FORM_ENTRY_GATE_REPLAY_TECHNICAL_UNKNOWN"
        semantic = "LOCAL_GOSI_OFFICIAL_NF_FORM_GATE_REPLAY_TECHNICAL_UNKNOWN"
        next_action = "HARDEN_NF_FORM_GATE_REPLAY_TRANSPORT_OR_SESSION_CONTRACT"
    else:
        classification = "LOCAL_GOSI_OFFICIAL_NF_FORM_ENTRY_GATE_CONTRACT_UNRESOLVED"
        semantic = "LOCAL_GOSI_OFFICIAL_NF_FORM_GATE_CONTRACT_NOT_SAFE_TO_REPLAY"
        next_action = "RECOVER_EXACT_SINGLE_NF_FORM_POST_CONTRACT_BEFORE_REPLAY"

    out = {
        "step": "STEP 17-21-C-16-8-T-140-S225B",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "prerequisite": {"s225": gate_225, "s225a": gate_225a},
        "s225a_search_contract_recovered_treatment": "DIAGNOSTIC_ONLY_GENERIC_LIBRARY_FALSE_POSITIVE_NOT_INHERITED_AS_SEARCH_CONTRACT",
        "entry": {
            "http": entry.status_code if entry is not None else None,
            "final_url": entry.url if entry is not None else None,
            "error": entry_error,
            "cookie_names": sorted(session.cookies.keys()),
            "nf_candidate_count": len(nf_candidates),
            "selected_nf_form": selected_form,
            "signals": entry_signals,
        },
        "replay": {
            "attempted": replay_attempted,
            "http": replay.status_code if replay is not None else None,
            "final_url": post_url,
            "body_bytes": len(replay.content) if replay is not None else 0,
            "error": replay_error,
            "same_official_host": same_official_host,
            "post_gate_application_surface_recovered": escaped_gate,
            "signals": post_signals,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "nf_form_gate_replay_executed": replay_attempted,
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
    print("S225A GATE:", gate_225a)
    print("ENTRY HTTP:", out["entry"]["http"])
    print("ENTRY FINAL URL:", out["entry"]["final_url"])
    print("COOKIE NAMES:", out["entry"]["cookie_names"])
    print("NF FORM CANDIDATE COUNT:", len(nf_candidates))
    print("NF FORM REPLAY ATTEMPTED:", replay_attempted)
    print("POST HTTP:", out["replay"]["http"])
    print("POST FINAL URL:", out["replay"]["final_url"])
    print("POST SAME OFFICIAL HOST:", same_official_host)
    print("POST-GATE APPLICATION SURFACE RECOVERED:", escaped_gate)
    print("CLASSIFICATION:", classification)

    print("\nSELECTED NF FORM")
    print(json.dumps(selected_form, ensure_ascii=False, indent=2))
    print("\nENTRY SIGNALS")
    print(json.dumps(entry_signals, ensure_ascii=False, indent=2))
    print("\nPOST SIGNALS")
    print(json.dumps(post_signals, ensure_ascii=False, indent=2))

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("S225A generic-library search-contract signal inherited: False")
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
        "S225 gate": gate_225,
        "S225A gate": gate_225a,
        "entry request classified": entry is not None or entry_error is not None,
        "nfForm candidate count bounded": len(nf_candidates) <= 1,
        "replay classification emitted": classification.startswith("LOCAL_GOSI_OFFICIAL_NF_FORM_"),
        "search request not executed": out["summary"]["search_request_executed"] is False,
        "positive control search not executed": out["summary"]["positive_control_search_executed"] is False,
        "target query not executed": out["summary"]["target_query_executed"] is False,
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
        raise AssertionError("S225B local.gosi.go.kr nfForm gate replay failed")


if __name__ == "__main__":
    main()
