# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import parse_qsl, urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_PREV = OUT_DIR / "development_density_management_area_krihs_search_contract_semantic_dedup_hardening.json"
OUT = OUT_DIR / "development_density_management_area_krihs_publication_title_detail_link_recovery.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
EXPECTED_ACTION = "https://www.krihs.re.kr/aivorySearch.es?mid=a11800000000"
EXPECTED_METHOD = "POST"
EXPECTED_FIELD = "allKeyWord"
ENTRY_URL = "https://www.krihs.re.kr/"
KRIHS_HOST = "www.krihs.re.kr"

SEARCH_TERM = "개발밀도"
TITLE_TARGETS = [
    {
        "key": "REPORT_2001",
        "needle": "도시성장관리를 위한 개발밀도에 관한 연구",
    },
    {
        "key": "ARTICLE_2005",
        "needle": "주거환경을 고려한 개발밀도론 제시",
    },
    {
        "key": "BRIEF_842",
        "needle": "도시개발밀도 관리를 위한 공간 관리방안",
    },
]
CONTEXT_RADIUS = 3500
MAX_CONTEXTS_PER_TITLE = 8
MAX_LINKS_PER_TITLE = 80


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_space(value: str):
    return re.sub(r"\s+", " ", unescape(value or "")).strip()


def strip_tags(value: str):
    return normalize_space(re.sub(r"<[^>]+>", " ", value or ""))


def extract_csrf(html: str):
    patterns = [
        r'<input[^>]+name=["\']_csrf["\'][^>]+value=["\']([^"\']+)',
        r'<input[^>]+value=["\']([^"\']+)["\'][^>]+name=["\']_csrf["\']',
    ]
    for pattern in patterns:
        m = re.search(pattern, html or "", flags=re.I)
        if m:
            return unescape(m.group(1))
    return None


def validate_contract(prev: dict):
    contracts = prev.get("canonical_contracts") or []
    return (
        prev.get("contract_qualified") is True
        and prev.get("semantic_unique_contract_count") == 1
        and len(contracts) == 1
        and str(contracts[0].get("method") or "").upper() == EXPECTED_METHOD
        and contracts[0].get("action") == EXPECTED_ACTION
        and contracts[0].get("field") == EXPECTED_FIELD
        and contracts[0].get("all_runs_credible") is True
        and contracts[0].get("run_consistent") is True
    )


def parse_js_arguments(arg_text: str):
    args = []
    token_re = re.compile(r'''["']([^"']*)["']|([^,\s\)]+)''')
    for m in token_re.finditer(arg_text or ""):
        value = m.group(1) if m.group(1) is not None else m.group(2)
        value = normalize_space(value)
        if value:
            args.append(value)
    return args


def capture_title_contexts(html: str, needle: str):
    contexts = []
    seen = set()
    for m in re.finditer(re.escape(needle), html or "", flags=re.I):
        left = max(0, m.start() - CONTEXT_RADIUS)
        right = min(len(html), m.end() + CONTEXT_RADIUS)
        raw = (html or "")[left:right]
        plain = strip_tags(raw)
        key = plain[:1200]
        if not key or key in seen:
            continue
        seen.add(key)
        contexts.append({
            "raw_html": raw,
            "text_preview": plain[:3500],
        })
        if len(contexts) >= MAX_CONTEXTS_PER_TITLE:
            break
    return contexts


def local_title_match(title: str, needle: str):
    t = normalize_space(title)
    n = normalize_space(needle)
    return bool(t and n and (n in t or t in n or n.replace(" ", "") in t.replace(" ", "")))


def extract_links_from_context(raw: str, needle: str):
    rows = []
    seen = set()

    anchor_re = re.compile(
        r'<a\b([^>]*)href=["\']([^"\']+)["\']([^>]*)>(.*?)</a>',
        flags=re.I | re.S,
    )
    for m in anchor_re.finditer(raw or ""):
        href = unescape(m.group(2)).strip()
        title = strip_tags(m.group(4))
        attrs = normalize_space(f"{m.group(1)} {m.group(3)}")
        around = strip_tags((raw or "")[max(0, m.start() - 500): min(len(raw or ""), m.end() + 900)])
        proximity = 0
        if local_title_match(title, needle):
            proximity += 100
        if needle in around:
            proximity += 25
        if "저자" in around:
            proximity += 5
        if "발행일" in around or "등록일" in around:
            proximity += 5

        item = {
            "source": "ANCHOR",
            "anchor_text": title[:700],
            "href": href[:1600],
            "absolute_url": None,
            "onclick": None,
            "function_name": None,
            "function_args": [],
            "query_params": [],
            "attributes": attrs[:1200],
            "context_preview": around[:1800],
            "proximity_score": proximity,
        }

        if href.lower().startswith("javascript:"):
            js = href[len("javascript:"):]
            fm = re.match(r'\s*([A-Za-z_$][\w$\.]*)\s*\((.*)\)\s*;?\s*$', js, flags=re.S)
            if fm:
                item["function_name"] = fm.group(1)
                item["function_args"] = parse_js_arguments(fm.group(2))
        elif href and not href.startswith("#"):
            absolute = urljoin(EXPECTED_ACTION, href)
            parsed = urlparse(absolute)
            if not parsed.netloc or parsed.netloc == KRIHS_HOST:
                item["absolute_url"] = absolute[:1800]
                item["query_params"] = list(parse_qsl(parsed.query, keep_blank_values=True))

        key = (item["anchor_text"], item["href"], item["function_name"], tuple(item["function_args"]))
        if key in seen:
            continue
        seen.add(key)
        rows.append(item)

    onclick_re = re.compile(r'<([A-Za-z0-9]+)\b([^>]*)\bonclick=["\']([^"\']+)["\']([^>]*)>(.*?)</\1>', re.I | re.S)
    for m in onclick_re.finditer(raw or ""):
        onclick = unescape(m.group(3)).strip()
        title = strip_tags(m.group(5))
        around = strip_tags((raw or "")[max(0, m.start() - 500): min(len(raw or ""), m.end() + 900)])
        fm = re.search(r'([A-Za-z_$][\w$\.]*)\s*\(([^\)]*)\)', onclick, flags=re.S)
        function_name = fm.group(1) if fm else None
        function_args = parse_js_arguments(fm.group(2)) if fm else []
        proximity = 0
        if local_title_match(title, needle):
            proximity += 100
        if needle in around:
            proximity += 25
        if "저자" in around:
            proximity += 5
        if "발행일" in around or "등록일" in around:
            proximity += 5

        key = ("ONCLICK", title, onclick)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "source": "ONCLICK",
            "anchor_text": title[:700],
            "href": None,
            "absolute_url": None,
            "onclick": onclick[:1600],
            "function_name": function_name,
            "function_args": function_args,
            "query_params": [],
            "attributes": normalize_space(f"{m.group(2)} {m.group(4)}")[:1200],
            "context_preview": around[:1800],
            "proximity_score": proximity,
        })

    data_re = re.compile(r'\b(data-[A-Za-z0-9_-]+)\s*=\s*["\']([^"\']*)["\']', re.I)
    for m in data_re.finditer(raw or ""):
        around = strip_tags((raw or "")[max(0, m.start() - 700): min(len(raw or ""), m.end() + 900)])
        if needle not in around:
            continue
        key = ("DATA", m.group(1), m.group(2))
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "source": "DATA_ATTRIBUTE",
            "anchor_text": None,
            "href": None,
            "absolute_url": None,
            "onclick": None,
            "function_name": None,
            "function_args": [],
            "query_params": [],
            "attributes": f"{m.group(1)}={m.group(2)}"[:1200],
            "context_preview": around[:1800],
            "proximity_score": 40,
        })

    rows.sort(key=lambda x: (-x["proximity_score"], x.get("anchor_text") or "", x.get("href") or ""))
    return rows[:MAX_LINKS_PER_TITLE]


def extract_function_definitions(html: str, function_names: set[str]):
    definitions = []
    for full_name in sorted(n for n in function_names if n):
        name = full_name.split(".")[-1]
        patterns = [
            rf'function\s+{re.escape(name)}\s*\([^\)]*\)\s*\{{',
            rf'{re.escape(name)}\s*=\s*function\s*\([^\)]*\)\s*\{{',
        ]
        for pattern in patterns:
            m = re.search(pattern, html or "", flags=re.I | re.S)
            if m:
                definitions.append({
                    "function_name": full_name,
                    "definition_preview": (html or "")[m.start(): min(len(html or ""), m.start() + 5000)],
                })
                break
    return definitions


def probe_direct_url(session: requests.Session, url: str, needle: str):
    result = {
        "url": url,
        "http": None,
        "final_url": None,
        "content_type": None,
        "page_title": None,
        "needle_present": False,
        "technical_unknown": True,
        "error": None,
    }
    try:
        response = session.get(url, timeout=30, allow_redirects=True)
        response.raise_for_status()
        text = response.text or ""
        tm = re.search(r'<title[^>]*>(.*?)</title>', text, flags=re.I | re.S)
        result.update({
            "http": response.status_code,
            "final_url": response.url,
            "content_type": response.headers.get("Content-Type"),
            "page_title": strip_tags(tm.group(1))[:600] if tm else None,
            "needle_present": needle in strip_tags(text),
            "technical_unknown": False,
        })
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def main():
    print("=" * 78)
    print("KRIHS PUBLICATION TITLE DETAIL LINK RECOVERY")
    print("=" * 78)
    print("Purpose: recover detail-link mechanics around three observed KRIHS publication titles")
    print("Recovered title/detail link != designation/current validity/site inclusion")
    print("No recovered title/detail link != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    prev = load_json(IN_PREV)
    contract_qualified = validate_contract(prev)
    if not contract_qualified:
        raise AssertionError("Qualified semantic KRIHS contract prerequisite not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; site-ai STEP17 KRIHS publication title detail recovery)",
        "Referer": ENTRY_URL,
    })

    entry_http = None
    csrf = None
    entry_error = None
    try:
        entry = session.get(ENTRY_URL, timeout=30)
        entry.raise_for_status()
        entry_http = entry.status_code
        csrf = extract_csrf(entry.text)
    except Exception as exc:
        entry_error = f"{type(exc).__name__}: {exc}"

    payload = {EXPECTED_FIELD: SEARCH_TERM}
    if csrf:
        payload["_csrf"] = csrf

    search_http = None
    search_error = None
    search_html = ""
    try:
        response = session.post(EXPECTED_ACTION, data=payload, timeout=30)
        response.raise_for_status()
        search_http = response.status_code
        search_html = response.text or ""
    except Exception as exc:
        search_error = f"{type(exc).__name__}: {exc}"

    title_rows = []
    all_function_names = set()
    successful_detail_like_probes = 0

    for target in TITLE_TARGETS:
        needle = target["needle"]
        contexts = capture_title_contexts(search_html, needle)
        links = []
        seen = set()
        for context in contexts:
            for item in extract_links_from_context(context["raw_html"], needle):
                key = (
                    item.get("source"),
                    item.get("anchor_text"),
                    item.get("href"),
                    item.get("onclick"),
                    item.get("attributes"),
                )
                if key in seen:
                    continue
                seen.add(key)
                links.append(item)
                if item.get("function_name"):
                    all_function_names.add(item["function_name"])
        links.sort(key=lambda x: (-x["proximity_score"], x.get("anchor_text") or ""))
        links = links[:MAX_LINKS_PER_TITLE]

        probes = []
        for item in links[:15]:
            url = item.get("absolute_url")
            if not url or item.get("proximity_score", 0) < 100:
                continue
            probe = probe_direct_url(session, url, needle)
            probes.append(probe)
            if probe.get("technical_unknown") is False and probe.get("http") == 200 and probe.get("needle_present") is True:
                successful_detail_like_probes += 1

        title_rows.append({
            "key": target["key"],
            "needle": needle,
            "title_occurrence_count": len(list(re.finditer(re.escape(needle), search_html or "", flags=re.I))),
            "context_count": len(contexts),
            "candidate_count": len(links),
            "candidates": links,
            "direct_probes": probes,
        })

    function_definitions = extract_function_definitions(search_html, all_function_names)
    technical_unknown = bool(search_error)

    if technical_unknown:
        classification = "KRIHS_PUBLICATION_TITLE_DETAIL_LINK_RECOVERY_TECHNICAL_UNKNOWN"
        next_action = "HARDEN_ONLY_KRIHS_TITLE_SCOPED_SEARCH_TRANSPORT_WITHOUT_LEGAL_INFERENCE"
    elif successful_detail_like_probes > 0:
        classification = "KRIHS_PUBLICATION_TITLE_SCOPED_DETAIL_LINK_HTTP_VERIFIED"
        next_action = "REVIEW_ONLY_VERIFIED_KRIHS_PUBLICATION_DOCUMENT_IDENTITIES_AS_NON_DISPOSITIVE_DISCOVERY_LEADS"
    elif any(row["candidate_count"] > 0 for row in title_rows):
        classification = "KRIHS_PUBLICATION_TITLE_SCOPED_LINK_MECHANICS_CAPTURED"
        next_action = "RESOLVE_TITLE_SCOPED_JS_OR_DETAIL_PARAMETER_CONTRACT_WITHOUT_LEGAL_INFERENCE"
    else:
        classification = "KRIHS_PUBLICATION_TITLE_SCOPED_LINK_NOT_RECOVERED"
        next_action = "INSPECT_EXACT_RESULT_ITEM_TEMPLATE_OR_CLIENT_SIDE_BINDING_WITHOUT_NEGATIVE_EVIDENCE"

    out = {
        "step": "STEP 17-KRIHS-PUBLICATION-TITLE-DETAIL-LINK-RECOVERY",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "contract_qualified": contract_qualified,
        "entry_http": entry_http,
        "entry_csrf_found": bool(csrf),
        "entry_error": entry_error,
        "search_term": SEARCH_TERM,
        "search_http": search_http,
        "search_error": search_error,
        "title_targets": title_rows,
        "function_definitions": function_definitions,
        "successful_detail_like_probe_count": successful_detail_like_probes,
        "classification": classification,
        "summary": {
            "next_action": next_action,
            "title_detail_link_equals_designation": False,
            "title_detail_link_equals_current_validity": False,
            "title_detail_link_equals_site_inclusion": False,
            "no_title_detail_link_equals_legal_absence": False,
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

    print("\n" + "=" * 78)
    print("TITLE-SCOPED RECOVERY RESULT")
    print("=" * 78)
    print(f"CONTRACT QUALIFIED: {contract_qualified}")
    print(f"ENTRY HTTP: {entry_http}")
    print(f"ENTRY CSRF FOUND: {bool(csrf)}")
    print(f"SEARCH HTTP: {search_http}")
    for row in title_rows:
        print(
            f'{row["key"]}: occurrences={row["title_occurrence_count"]} '
            f'contexts={row["context_count"]} candidates={row["candidate_count"]} '
            f'probes={len(row["direct_probes"])}'
        )
        for idx, item in enumerate(row["candidates"][:12], 1):
            print(
                f'  [{idx}] score={item["proximity_score"]} source={item["source"]} '
                f'text={item["anchor_text"]!r}'
            )
            if item.get("absolute_url"):
                print(f'      url={item["absolute_url"]}')
            if item.get("function_name"):
                print(f'      function={item["function_name"]} args={item["function_args"]}')
            if item.get("onclick"):
                print(f'      onclick={item["onclick"][:600]}')
            if item.get("attributes"):
                print(f'      attrs={item["attributes"][:600]}')
        for idx, probe in enumerate(row["direct_probes"][:8], 1):
            print(
                f'      PROBE[{idx}] http={probe["http"]} final={probe["final_url"]} '
                f'needle_present={probe["needle_present"]} title={probe["page_title"]!r} '
                f'technical_unknown={probe["technical_unknown"]}'
            )

    print(f"FUNCTION DEFINITIONS CAPTURED: {len(function_definitions)}")
    for idx, definition in enumerate(function_definitions[:10], 1):
        preview = strip_tags(definition["definition_preview"][:900])
        print(f'  FN[{idx}] {definition["function_name"]}: {preview[:700]}')

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print("Title/detail link == designation: False")
    print("Title/detail link == current validity: False")
    print("Title/detail link == site inclusion: False")
    print("No title/detail link == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "canonical contract qualified": out["contract_qualified"] is True,
        "weak search term fixed": out["search_term"] == "개발밀도",
        "three observed publication titles fixed": len(out["title_targets"]) == 3,
        "title detail link not designation": out["summary"]["title_detail_link_equals_designation"] is False,
        "title detail link not validity": out["summary"]["title_detail_link_equals_current_validity"] is False,
        "title detail link not site inclusion": out["summary"]["title_detail_link_equals_site_inclusion"] is False,
        "no title detail link not legal absence": out["summary"]["no_title_detail_link_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
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
        raise AssertionError("KRIHS publication title detail link recovery validation failed")


if __name__ == "__main__":
    main()
