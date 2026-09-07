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

S224C = OUT_DIR / "development_density_management_area_gyeonggi_official_record_source_family_terminal_reconciliation.json"
OUT = OUT_DIR / "development_density_management_area_local_gosi_official_entry_contract_forensic.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "LOCAL_GOSI_OFFICIAL"

ENTRY_URL = "https://local.gosi.go.kr/klid/main/main.do"
POSITIVE_CONTROL = "성남시"

EXPECTED_S224C_CLASSIFICATION = (
    "GYEONGGI_OFFICIAL_RECORD_SOURCE_FAMILY_OPERATIONALLY_CLOSED_WITHOUT_LEGAL_ABSENCE_INFERENCE"
)


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def attrs(tag: str) -> dict[str, str]:
    pairs = re.findall(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', tag, flags=re.S)
    return {k: unescape(v) for k, _, v in pairs}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_action(base_url: str, action: str | None) -> str | None:
    if action is None:
        return base_url
    action = action.strip()
    if not action or action.lower().startswith("javascript:"):
        return None
    return urljoin(base_url, action)


def extract_forms(html: str, base_url: str) -> list[dict]:
    forms: list[dict] = []
    for m in re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", html):
        tag = "<form" + m.group(1) + ">"
        body = m.group(2)
        a = attrs(tag)
        fields = []
        for im in re.finditer(r"(?is)<(?:input|select|textarea)\b([^>]*)>", body):
            ia = attrs("<input" + im.group(1) + ">")
            name = ia.get("name")
            if name:
                fields.append(name)
        forms.append(
            {
                "method": (a.get("method") or "GET").upper(),
                "action_raw": a.get("action"),
                "action_absolute": normalize_action(base_url, a.get("action")),
                "id": a.get("id"),
                "name": a.get("name"),
                "fields": sorted(set(fields)),
                "text": clean_html(body)[:500],
            }
        )
    return forms


def extract_scripts(html: str, base_url: str) -> list[dict]:
    scripts = []
    for m in re.finditer(r"(?is)<script\b([^>]*)>(.*?)</script>", html):
        a = attrs("<script" + m.group(1) + ">")
        src = a.get("src")
        scripts.append(
            {
                "src": urljoin(base_url, src) if src else None,
                "inline": (m.group(2) or "")[:4000],
            }
        )
    return scripts


def extract_links(html: str, base_url: str) -> list[str]:
    links: list[str] = []
    for m in re.finditer(r"(?is)<a\b([^>]*)>", html):
        a = attrs("<a" + m.group(1) + ">")
        href = a.get("href")
        if not href or href.lower().startswith("javascript:"):
            continue
        links.append(urljoin(base_url, href))
    return sorted(set(links))


def discover_search_contract(forms: list[dict], scripts: list[dict], links: list[str]) -> dict:
    form_candidates = []
    for f in forms:
        blob = " ".join([
            f.get("action_raw") or "",
            f.get("id") or "",
            f.get("name") or "",
            " ".join(f.get("fields") or []),
            f.get("text") or "",
        ]).lower()
        if any(k in blob for k in ("search", "srch", "query", "keyword", "검색", "고시", "공고")):
            form_candidates.append(f)

    script_hits = []
    patterns = [
        r'''["']([^"']*(?:search|srch|list|notice|gosi|gonggo)[^"']*\.do(?:\?[^"']*)?)["']''',
        r'''["']([^"']*(?:search|srch|list|notice|gosi|gonggo)[^"']*\.jsp(?:\?[^"']*)?)["']''',
    ]
    for s in scripts:
        inline = s.get("inline") or ""
        for pat in patterns:
            for m in re.finditer(pat, inline, flags=re.I):
                script_hits.append(m.group(1))

    link_hits = [
        x for x in links
        if any(k in x.lower() for k in ("search", "srch", "list", "notice", "gosi", "gonggo"))
    ]

    return {
        "form_candidates": form_candidates,
        "script_endpoint_hints": sorted(set(script_hits)),
        "link_endpoint_hints": sorted(set(link_hits))[:100],
    }


def bounded_positive_control_attempt(session: requests.Session, base_url: str, contract: dict) -> dict:
    attempts = []
    candidate_forms = contract.get("form_candidates") or []

    keyword_field_names = {
        "keyword", "kwd", "query", "searchword", "search_word", "searchkeyword",
        "search_keyword", "srchword", "srch_word", "srchkeyword", "searchtext", "search_text",
    }

    for f in candidate_forms[:6]:
        action = f.get("action_absolute")
        if not action or urlparse(action).netloc not in {"local.gosi.go.kr"}:
            continue
        fields = f.get("fields") or []
        field = next((x for x in fields if x.lower() in keyword_field_names), None)
        if not field:
            field = next((x for x in fields if any(k in x.lower() for k in ("keyword", "kwd", "query", "search", "srch"))), None)
        if not field:
            continue

        data = {field: POSITIVE_CONTROL}
        try:
            if (f.get("method") or "GET").upper() == "POST":
                r = session.post(action, data=data, timeout=60, allow_redirects=True, headers={"Referer": base_url})
            else:
                r = session.get(action, params=data, timeout=60, allow_redirects=True, headers={"Referer": base_url})
            attempts.append(
                {
                    "method": (f.get("method") or "GET").upper(),
                    "action": action,
                    "field": field,
                    "http": r.status_code,
                    "final_url": r.url,
                    "body_bytes": len(r.content),
                    "positive_term_visible": POSITIVE_CONTROL in clean_html(r.text),
                    "same_official_host": urlparse(r.url).netloc == "local.gosi.go.kr",
                    "error": None,
                }
            )
        except requests.RequestException as ex:
            attempts.append(
                {
                    "method": (f.get("method") or "GET").upper(),
                    "action": action,
                    "field": field,
                    "http": None,
                    "final_url": None,
                    "body_bytes": 0,
                    "positive_term_visible": False,
                    "same_official_host": False,
                    "error": f"{type(ex).__name__}: {ex}",
                }
            )

    qualified = any(
        x.get("http") == 200
        and x.get("same_official_host") is True
        and x.get("positive_term_visible") is True
        for x in attempts
    )
    return {"attempts": attempts, "qualified": qualified}


def main() -> None:
    print("=" * 78)
    print("LOCAL GOSI OFFICIAL ENTRY CONTRACT FORENSIC - S225")
    print("=" * 78)
    print("Purpose: qualify official local.gosi.go.kr entry/search contract before any UQQ700 replay")
    print("Positive control only; UQQ700 target query is NOT executed")
    print("Search hit != legal fact")
    print("Search no-hit != legal absence")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s224c = load(S224C)
    gate_224c = (
        s224c.get("classification") == EXPECTED_S224C_CLASSIFICATION
        and (s224c.get("summary") or {}).get("operational_source_family_closure") is True
        and (s224c.get("summary") or {}).get("legal_absence_inference_allowed") is False
        and (s224c.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    if not gate_224c:
        raise AssertionError("S225 prerequisite S224C gate not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    try:
        r = session.get(ENTRY_URL, timeout=60, allow_redirects=True)
        entry_error = None
    except requests.RequestException as ex:
        r = None
        entry_error = f"{type(ex).__name__}: {ex}"

    html = r.text if r is not None else ""
    final_url = r.url if r is not None else None
    official_host = bool(final_url and urlparse(final_url).netloc == "local.gosi.go.kr")
    entry_http_ok = bool(r is not None and r.status_code == 200)

    forms = extract_forms(html, final_url or ENTRY_URL)
    scripts = extract_scripts(html, final_url or ENTRY_URL)
    links = extract_links(html, final_url or ENTRY_URL)
    contract = discover_search_contract(forms, scripts, links)
    positive = bounded_positive_control_attempt(session, final_url or ENTRY_URL, contract) if entry_http_ok and official_host else {"attempts": [], "qualified": False}

    has_contract_signal = bool(
        contract.get("form_candidates")
        or contract.get("script_endpoint_hints")
        or contract.get("link_endpoint_hints")
    )

    if entry_http_ok and official_host and positive.get("qualified"):
        classification = "LOCAL_GOSI_OFFICIAL_ENTRY_AND_POSITIVE_CONTROL_SEARCH_CONTRACT_QUALIFIED"
        semantic = "LOCAL_GOSI_OFFICIAL_ENTRY_AND_POSITIVE_CONTROL_SURFACE_QUALIFIED"
        next_action = "BUILD_S226_LOCAL_GOSI_RESULT_IDENTITY_AND_DETAIL_NAVIGATION_FORENSIC_BEFORE_UQQ700_TARGET_REPLAY"
    elif entry_http_ok and official_host and has_contract_signal:
        classification = "LOCAL_GOSI_OFFICIAL_ENTRY_QUALIFIED_SEARCH_CONTRACT_PARTIAL"
        semantic = "LOCAL_GOSI_OFFICIAL_ENTRY_SURFACE_QUALIFIED_SEARCH_REPLAY_PARTIAL"
        next_action = "HARDEN_LOCAL_GOSI_SEARCH_PARAMETER_OR_JAVASCRIPT_CONTRACT_BEFORE_UQQ700_TARGET_REPLAY"
    elif entry_http_ok and official_host:
        classification = "LOCAL_GOSI_OFFICIAL_ENTRY_QUALIFIED_SEARCH_CONTRACT_UNRESOLVED"
        semantic = "LOCAL_GOSI_OFFICIAL_ENTRY_SURFACE_QUALIFIED_SEARCH_CONTRACT_UNRESOLVED"
        next_action = "FORENSICALLY_RECOVER_LOCAL_GOSI_SEARCH_FORM_ACTION_AND_PARAMETER_CONTRACT"
    else:
        classification = "LOCAL_GOSI_OFFICIAL_ENTRY_SURFACE_UNRESOLVED"
        semantic = "LOCAL_GOSI_OFFICIAL_ENTRY_SURFACE_TECHNICAL_UNKNOWN"
        next_action = "HARDEN_LOCAL_GOSI_ENTRY_ACCESS_BEFORE_ANY_TARGET_REPLAY"

    out = {
        "step": "STEP 17-21-C-16-8-T-138-S225",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "prerequisite_s224c_gate": gate_224c,
        "entry": {
            "url": ENTRY_URL,
            "http": r.status_code if r is not None else None,
            "final_url": final_url,
            "body_bytes": len(r.content) if r is not None else 0,
            "error": entry_error,
            "official_host": official_host,
            "form_count": len(forms),
            "script_count": len(scripts),
            "link_count": len(links),
        },
        "forms": forms,
        "search_contract": contract,
        "positive_control": {
            "term": POSITIVE_CONTROL,
            "target_query_executed": False,
            **positive,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "entry_surface_qualified": entry_http_ok and official_host,
            "search_contract_signal_found": has_contract_signal,
            "positive_control_search_qualified": positive.get("qualified") is True,
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

    print("S224C GATE:", gate_224c)
    print("ENTRY HTTP:", out["entry"]["http"])
    print("ENTRY FINAL URL:", out["entry"]["final_url"])
    print("OFFICIAL HOST:", out["entry"]["official_host"])
    print("FORM COUNT:", out["entry"]["form_count"])
    print("SCRIPT COUNT:", out["entry"]["script_count"])
    print("LINK COUNT:", out["entry"]["link_count"])
    print("SEARCH FORM CANDIDATE COUNT:", len(contract.get("form_candidates") or []))
    print("SCRIPT ENDPOINT HINT COUNT:", len(contract.get("script_endpoint_hints") or []))
    print("LINK ENDPOINT HINT COUNT:", len(contract.get("link_endpoint_hints") or []))
    print("POSITIVE CONTROL ATTEMPT COUNT:", len(positive.get("attempts") or []))
    print("POSITIVE CONTROL QUALIFIED:", positive.get("qualified") is True)
    print("CLASSIFICATION:", classification)

    print("\nSEARCH CONTRACT")
    print(json.dumps(contract, ensure_ascii=False, indent=2))

    print("\nPOSITIVE CONTROL ATTEMPTS")
    for i, item in enumerate(positive.get("attempts") or [], 1):
        print(f"--- ATTEMPT {i} ---")
        print(json.dumps(item, ensure_ascii=False, indent=2))

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("Target query executed: False")
    print("Search hit equals designation identity: False")
    print("Search no-hit equals legal absence: False")
    print("Negative evidence allowed: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S224C terminal gate": gate_224c,
        "entry request attempted": r is not None or entry_error is not None,
        "response classified": classification in {
            "LOCAL_GOSI_OFFICIAL_ENTRY_AND_POSITIVE_CONTROL_SEARCH_CONTRACT_QUALIFIED",
            "LOCAL_GOSI_OFFICIAL_ENTRY_QUALIFIED_SEARCH_CONTRACT_PARTIAL",
            "LOCAL_GOSI_OFFICIAL_ENTRY_QUALIFIED_SEARCH_CONTRACT_UNRESOLVED",
            "LOCAL_GOSI_OFFICIAL_ENTRY_SURFACE_UNRESOLVED",
        },
        "positive control only": out["positive_control"]["term"] == POSITIVE_CONTROL,
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
        raise AssertionError("S225 local.gosi.go.kr entry contract forensic failed")


if __name__ == "__main__":
    main()
