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
OUT = OUT_DIR / "development_density_management_area_krihs_publication_item_anchor_raw_contract_recovery.json"

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
    ("REPORT_2001", "도시성장관리를 위한 개발밀도에 관한 연구"),
    ("ARTICLE_2005", "주거환경을 고려한 개발밀도론 제시"),
    ("BRIEF_842", "도시개발밀도 관리를 위한 공간 관리방안"),
]

CONTEXT_RADIUS = 2600
MAX_MATCHES_PER_TITLE = 6


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


def parse_attributes(opening_tag: str):
    attrs = []
    for m in re.finditer(
        r'([:\w-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))',
        opening_tag or "",
        flags=re.I | re.S,
    ):
        name = m.group(1)
        value = next((g for g in m.groups()[1:] if g is not None), "")
        attrs.append({"name": name, "value": unescape(value)[:2000]})
    return attrs


def get_attr(attrs: list[dict], name: str):
    for row in attrs:
        if row["name"].lower() == name.lower():
            return row["value"]
    return None


def find_enclosing_anchor(html: str, pos: int):
    starts = list(re.finditer(r'<a\b[^>]*>', html[:pos], flags=re.I | re.S))
    if not starts:
        return None
    start_match = starts[-1]
    start = start_match.start()
    close = re.search(r'</a\s*>', html[pos:], flags=re.I | re.S)
    if not close:
        return None
    end = pos + close.end()
    raw = html[start:end]
    if raw.lower().count("<a") > 1:
        return None
    return {
        "start": start,
        "end": end,
        "opening_tag": start_match.group(0),
        "full_anchor_html": raw,
        "anchor_text": strip_tags(raw),
    }


def resolve_href(href: str | None):
    result = {
        "href": href,
        "absolute_url": None,
        "query_params": [],
        "is_javascript": False,
        "javascript_body": None,
    }
    if not href:
        return result
    href = unescape(href).strip()
    result["href"] = href
    if href.lower().startswith("javascript:"):
        result["is_javascript"] = True
        result["javascript_body"] = href[len("javascript:"):][:2000]
        return result
    if href.startswith("#"):
        return result
    absolute = urljoin(EXPECTED_ACTION, href)
    parsed = urlparse(absolute)
    if parsed.netloc and parsed.netloc != KRIHS_HOST:
        return result
    result["absolute_url"] = absolute
    result["query_params"] = list(parse_qsl(parsed.query, keep_blank_values=True))
    return result


def capture_parent_and_siblings(html: str, start: int, end: int):
    left = max(0, start - CONTEXT_RADIUS)
    right = min(len(html), end + CONTEXT_RADIUS)
    raw = html[left:right]
    return {
        "raw_context": raw[:7000],
        "text_context": strip_tags(raw)[:3500],
    }


def probe_url(session: requests.Session, url: str | None, needle: str):
    if not url:
        return None
    row = {
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
        row.update({
            "http": response.status_code,
            "final_url": response.url,
            "content_type": response.headers.get("Content-Type"),
            "page_title": strip_tags(tm.group(1))[:700] if tm else None,
            "needle_present": needle in strip_tags(text),
            "technical_unknown": False,
        })
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def recover_title(session: requests.Session, html: str, key: str, needle: str):
    matches = []
    seen = set()
    for m in re.finditer(re.escape(needle), html or "", flags=re.I):
        anchor = find_enclosing_anchor(html, m.start())
        if not anchor:
            continue
        signature = (anchor["start"], anchor["end"])
        if signature in seen:
            continue
        seen.add(signature)

        attrs = parse_attributes(anchor["opening_tag"])
        href_info = resolve_href(get_attr(attrs, "href"))
        context = capture_parent_and_siblings(html, anchor["start"], anchor["end"])
        probe = probe_url(session, href_info["absolute_url"], needle)

        matches.append({
            "opening_tag_raw": anchor["opening_tag"][:4000],
            "full_anchor_html": anchor["full_anchor_html"][:9000],
            "anchor_text": anchor["anchor_text"][:2500],
            "attributes": attrs,
            "href_contract": href_info,
            "onclick": get_attr(attrs, "onclick"),
            "target": get_attr(attrs, "target"),
            "class": get_attr(attrs, "class"),
            "data_attributes": [a for a in attrs if a["name"].lower().startswith("data-")],
            "context": context,
            "probe": probe,
        })
        if len(matches) >= MAX_MATCHES_PER_TITLE:
            break

    verified = sum(
        1 for row in matches
        if row.get("probe")
        and row["probe"].get("technical_unknown") is False
        and row["probe"].get("http") == 200
        and row["probe"].get("needle_present") is True
    )
    return {
        "key": key,
        "needle": needle,
        "occurrence_count": len(list(re.finditer(re.escape(needle), html or "", flags=re.I))),
        "anchor_match_count": len(matches),
        "matches": matches,
        "verified_detail_probe_count": verified,
    }


def main():
    print("=" * 78)
    print("KRIHS PUBLICATION ITEM ANCHOR RAW CONTRACT RECOVERY")
    print("=" * 78)
    print("Purpose: recover raw <a class=\"item\"> opening tags and exact href/detail mechanics for three observed publications")
    print("Recovered item anchor != designation/current validity/site inclusion")
    print("No recovered item anchor != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    prev = load_json(IN_PREV)
    contract_qualified = validate_contract(prev)
    if not contract_qualified:
        raise AssertionError("Qualified semantic KRIHS contract prerequisite not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; site-ai STEP17 KRIHS item anchor raw recovery)",
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

    title_rows = [recover_title(session, search_html, key, needle) for key, needle in TITLE_TARGETS]
    total_anchor_matches = sum(row["anchor_match_count"] for row in title_rows)
    total_verified_detail_probes = sum(row["verified_detail_probe_count"] for row in title_rows)
    direct_href_count = sum(
        1 for row in title_rows for match in row["matches"]
        if match["href_contract"].get("absolute_url")
    )
    technical_unknown = bool(search_error)

    if technical_unknown:
        classification = "KRIHS_PUBLICATION_ITEM_ANCHOR_RAW_CONTRACT_TECHNICAL_UNKNOWN"
        next_action = "HARDEN_ONLY_KRIHS_SEARCH_RESPONSE_CAPTURE_WITHOUT_LEGAL_INFERENCE"
    elif total_verified_detail_probes > 0:
        classification = "KRIHS_PUBLICATION_ITEM_DETAIL_HREF_RECOVERED_AND_TITLE_HTTP_VERIFIED"
        next_action = "REVIEW_VERIFIED_KRIHS_PUBLICATION_DOCUMENT_IDENTITIES_AS_NON_DISPOSITIVE_DISCOVERY_LEADS"
    elif direct_href_count > 0:
        classification = "KRIHS_PUBLICATION_ITEM_DIRECT_HREF_RECOVERED_NOT_TITLE_VERIFIED"
        next_action = "QUALIFY_RECOVERED_ITEM_HREF_AS_DOCUMENT_DETAIL_OR_REDIRECT_CONTRACT_ONLY"
    elif total_anchor_matches > 0:
        classification = "KRIHS_PUBLICATION_ITEM_RAW_ANCHOR_RECOVERED_WITHOUT_DIRECT_HREF"
        next_action = "RESOLVE_NON_STANDARD_ANCHOR_ATTRIBUTE_OR_CLIENT_SIDE_BINDING_WITHOUT_LEGAL_INFERENCE"
    else:
        classification = "KRIHS_PUBLICATION_ITEM_ANCHOR_NOT_RECOVERED"
        next_action = "INSPECT_RESULT_ITEM_TEMPLATE_BOUNDARIES_WITHOUT_NEGATIVE_EVIDENCE"

    out = {
        "step": "STEP 17-KRIHS-PUBLICATION-ITEM-ANCHOR-RAW-CONTRACT-RECOVERY",
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
        "total_anchor_match_count": total_anchor_matches,
        "direct_href_count": direct_href_count,
        "verified_detail_probe_count": total_verified_detail_probes,
        "classification": classification,
        "summary": {
            "next_action": next_action,
            "item_anchor_equals_designation": False,
            "item_anchor_equals_current_validity": False,
            "item_anchor_equals_site_inclusion": False,
            "no_item_anchor_equals_legal_absence": False,
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
    print("RAW ANCHOR CONTRACT RESULT")
    print("=" * 78)
    print(f"CONTRACT QUALIFIED: {contract_qualified}")
    print(f"ENTRY HTTP: {entry_http}")
    print(f"ENTRY CSRF FOUND: {bool(csrf)}")
    print(f"SEARCH HTTP: {search_http}")
    for row in title_rows:
        print(
            f'{row["key"]}: occurrences={row["occurrence_count"]} '
            f'anchor_matches={row["anchor_match_count"]} '
            f'verified_probes={row["verified_detail_probe_count"]}'
        )
        for idx, match in enumerate(row["matches"][:4], 1):
            print(f'  [{idx}] OPENING_TAG: {match["opening_tag_raw"]}')
            print(f'      class={match["class"]!r} target={match["target"]!r}')
            print(f'      href={match["href_contract"].get("href")!r}')
            print(f'      absolute={match["href_contract"].get("absolute_url")!r}')
            print(f'      onclick={match["onclick"]!r}')
            print(f'      data={match["data_attributes"]}')
            if match.get("probe"):
                probe = match["probe"]
                print(
                    f'      PROBE http={probe["http"]} final={probe["final_url"]} '
                    f'needle_present={probe["needle_present"]} title={probe["page_title"]!r} '
                    f'technical_unknown={probe["technical_unknown"]}'
                )
            print(f'      ANCHOR_TEXT: {match["anchor_text"][:700]}')

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print("Item anchor == designation: False")
    print("Item anchor == current validity: False")
    print("Item anchor == site inclusion: False")
    print("No item anchor == legal absence: False")
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
        "item anchor not designation": out["summary"]["item_anchor_equals_designation"] is False,
        "item anchor not validity": out["summary"]["item_anchor_equals_current_validity"] is False,
        "item anchor not site inclusion": out["summary"]["item_anchor_equals_site_inclusion"] is False,
        "no item anchor not legal absence": out["summary"]["no_item_anchor_equals_legal_absence"] is False,
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
        raise AssertionError("KRIHS publication item anchor raw contract recovery validation failed")


if __name__ == "__main__":
    main()
