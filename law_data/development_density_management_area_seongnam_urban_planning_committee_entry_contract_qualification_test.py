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
OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_entry_contract_qualification.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_URBAN_PLANNING_COMMITTEE_RECORD"

# Official Seongnam City urban-planning committee result board/detail surface.
# S226 intentionally performs contract qualification only; it does not execute a
# UQQ700 query or infer any legal/site fact from board availability.
ENTRY_URL = "https://www.seongnam.go.kr/city/1000557/30229/bbsView.do?idx=374215"
OFFICIAL_HOST = "www.seongnam.go.kr"

BOARD_TERMS = (
    "도시계획위원회",
    "개최 결과",
    "도시계획과",
)
ATTACHMENT_EXTENSIONS = (".pdf", ".hwp", ".hwpx")
SEARCH_FIELD_TERMS = ("search", "keyword", "query", "searchword", "searchtext", "keyfield")
PAGING_TERMS = ("page", "pageindex", "pageno", "currentpage", "recordcountperpage")


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def attrs(tag: str) -> dict[str, str]:
    pairs = re.findall(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', tag, flags=re.S)
    return {k.lower(): unescape(v) for k, _, v in pairs}


def extract_forms(html: str, base_url: str) -> list[dict]:
    rows: list[dict] = []
    for m in re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", html or ""):
        fa = attrs("<form" + m.group(1) + ">")
        body = m.group(2)
        controls: list[dict] = []
        for cm in re.finditer(r"(?is)<(input|select|textarea|button)\b([^>]*)>", body):
            tag = cm.group(1).lower()
            ca = attrs(f"<{tag}" + cm.group(2) + ">")
            controls.append({
                "tag": tag,
                "type": (ca.get("type") or "").lower() or None,
                "name": ca.get("name"),
                "id": ca.get("id"),
                "value": ca.get("value"),
            })
        names = sorted({c["name"] for c in controls if c.get("name")})
        rows.append({
            "id": fa.get("id"),
            "name": fa.get("name"),
            "method": (fa.get("method") or "GET").upper(),
            "action_raw": fa.get("action"),
            "action_absolute": urljoin(base_url, fa.get("action")) if fa.get("action") else base_url,
            "control_names": names,
            "text": clean_html(body)[:1200],
        })
    return rows


def extract_links(html: str, base_url: str) -> list[dict]:
    rows: list[dict] = []
    for m in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", html or ""):
        a = attrs("<a" + m.group(1) + ">")
        href = a.get("href")
        text = clean_html(m.group(2))[:300]
        absolute = None
        if href and not href.lower().startswith("javascript:"):
            absolute = urljoin(base_url, href)
        rows.append({
            "text": text,
            "href_raw": href,
            "href_absolute": absolute,
            "onclick": a.get("onclick"),
        })
    return rows


def extract_title(html: str) -> str | None:
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html or "")
    return clean_html(m.group(1)) if m else None


def main() -> None:
    print("=" * 78)
    print("SEONGNAM URBAN PLANNING COMMITTEE ENTRY CONTRACT QUALIFICATION - S226")
    print("=" * 78)
    print("Purpose: qualify the official committee record surface before any UQQ700 historical query")
    print("Positive-control target search: NOT EXECUTED")
    print("UQQ700 target query: NOT EXECUTED")
    print("Search request: NOT EXECUTED")
    print("Search hit != legal fact")
    print("Committee record hit != designation notice")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    error = None
    resp = None
    try:
        resp = session.get(ENTRY_URL, timeout=60, allow_redirects=True)
    except requests.RequestException as ex:
        error = f"{type(ex).__name__}: {ex}"

    html = resp.text if resp is not None else ""
    final_url = resp.url if resp is not None else None
    text = clean_html(html)
    forms = extract_forms(html, final_url or ENTRY_URL)
    links = extract_links(html, final_url or ENTRY_URL)

    official_host = bool(final_url and urlparse(final_url).hostname == OFFICIAL_HOST)
    http_ok = bool(resp is not None and resp.status_code == 200)
    board_term_hits = [t for t in BOARD_TERMS if t in text]
    board_identity = bool("도시계획위원회" in text and ("개최 결과" in text or "심의" in text))

    attachment_links = []
    for row in links:
        raw = (row.get("href_raw") or "") + " " + (row.get("text") or "") + " " + (row.get("onclick") or "")
        if any(ext in raw.lower() for ext in ATTACHMENT_EXTENSIONS) or "첨부" in raw or "다운로드" in raw:
            attachment_links.append(row)

    same_host_navigation = [
        row for row in links
        if row.get("href_absolute") and urlparse(row["href_absolute"]).hostname == OFFICIAL_HOST
    ]
    board_navigation = [
        row for row in same_host_navigation
        if any(x in ((row.get("href_raw") or "") + " " + (row.get("text") or "")).lower()
               for x in ("bbs", "list", "view", "30229", "1000557"))
    ]

    all_control_names = sorted({name for form in forms for name in form.get("control_names", [])})
    search_fields = [
        name for name in all_control_names
        if any(t in name.lower() for t in SEARCH_FIELD_TERMS)
    ]
    paging_fields = [
        name for name in all_control_names
        if any(t in name.lower() for t in PAGING_TERMS)
    ]

    raw_lower = html.lower()
    pagination_signal = bool(
        paging_fields
        or re.search(r"(?i)(pageindex|pageno|currentpage|goPage|fn_.*page|page=)", html)
    )
    search_contract_signal = bool(
        search_fields
        or re.search(r"(?i)(searchword|searchkeyword|searchtext|keyfield|searchcondition)", html)
    )
    attachment_contract_signal = bool(
        attachment_links
        or any(x in raw_lower for x in ("filedown", "download", "atchfile", "file_id", "fileid"))
    )

    contract_qualified = bool(
        http_ok
        and official_host
        and board_identity
        and len(board_navigation) >= 1
        and attachment_contract_signal
    )

    if contract_qualified:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_OFFICIAL_BOARD_ENTRY_CONTRACT_QUALIFIED"
        semantic = "SEONGNAM_URBAN_PLANNING_COMMITTEE_OFFICIAL_RECORD_SURFACE_QUALIFIED_WITHOUT_TARGET_QUERY"
        next_action = "BUILD_S226A_POSITIVE_CONTROL_HISTORY_PAGINATION_CONTRACT_WITHOUT_UQQ700_QUERY"
    elif http_ok and official_host:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_ENTRY_CONTRACT_PARTIAL"
        semantic = "SEONGNAM_URBAN_PLANNING_COMMITTEE_OFFICIAL_SURFACE_REACHED_BUT_BOARD_CONTRACT_NOT_FULLY_QUALIFIED"
        next_action = "HARDEN_SEONGNAM_URBAN_PLANNING_COMMITTEE_BOARD_CONTRACT_WITHOUT_UQQ700_QUERY"
    else:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_ENTRY_CONTRACT_TECHNICAL_UNKNOWN"
        semantic = "SEONGNAM_URBAN_PLANNING_COMMITTEE_ENTRY_SURFACE_NOT_TECHNICALLY_QUALIFIED"
        next_action = "FORENSICALLY_RECOVER_OFFICIAL_COMMITTEE_ENTRY_SURFACE_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-141-S226",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "entry_url": ENTRY_URL,
        "request": {
            "http": resp.status_code if resp is not None else None,
            "final_url": final_url,
            "official_host": official_host,
            "error": error,
            "title": extract_title(html),
            "body_bytes": len(resp.content) if resp is not None else 0,
        },
        "contract": {
            "board_term_hits": board_term_hits,
            "board_identity_verified": board_identity,
            "form_count": len(forms),
            "control_names": all_control_names,
            "search_fields": search_fields,
            "paging_fields": paging_fields,
            "search_contract_signal": search_contract_signal,
            "pagination_signal": pagination_signal,
            "link_count": len(links),
            "same_host_navigation_count": len(same_host_navigation),
            "board_navigation_count": len(board_navigation),
            "board_navigation_sample": board_navigation[:20],
            "attachment_contract_signal": attachment_contract_signal,
            "attachment_link_count": len(attachment_links),
            "attachment_links_sample": attachment_links[:20],
            "entry_contract_qualified": contract_qualified,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "positive_control_search_executed": False,
            "search_request_executed": False,
            "target_query_executed": False,
            "committee_record_hit_equals_designation_notice": False,
            "search_hit_equals_legal_fact": False,
            "search_no_hit_equals_legal_absence": False,
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

    print(f"HTTP: {out['request']['http']}")
    print(f"FINAL URL: {out['request']['final_url']}")
    print(f"OFFICIAL HOST: {official_host}")
    print(f"BOARD TERM HITS: {board_term_hits}")
    print(f"BOARD IDENTITY VERIFIED: {board_identity}")
    print(f"FORM COUNT: {len(forms)}")
    print(f"SEARCH CONTRACT SIGNAL: {search_contract_signal}")
    print(f"PAGINATION SIGNAL: {pagination_signal}")
    print(f"BOARD NAVIGATION COUNT: {len(board_navigation)}")
    print(f"ATTACHMENT CONTRACT SIGNAL: {attachment_contract_signal}")
    print(f"ATTACHMENT LINK COUNT: {len(attachment_links)}")
    print(f"ENTRY CONTRACT QUALIFIED: {contract_qualified}")
    print(f"CLASSIFICATION: {classification}")
    print("-" * 78)
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Target query executed: False")
    print("Legal absence inference allowed: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "request classified": classification in {
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_OFFICIAL_BOARD_ENTRY_CONTRACT_QUALIFIED",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_ENTRY_CONTRACT_PARTIAL",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_ENTRY_CONTRACT_TECHNICAL_UNKNOWN",
        },
        "positive control search not executed": out["summary"]["positive_control_search_executed"] is False,
        "search request not executed": out["summary"]["search_request_executed"] is False,
        "target query not executed": out["summary"]["target_query_executed"] is False,
        "committee hit not designation notice": out["summary"]["committee_record_hit_equals_designation_notice"] is False,
        "search no-hit not legal absence": out["summary"]["search_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "SITE promotion blocked": out["summary"]["site_positive_allowed"] is False and out["summary"]["site_negative_allowed"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists(),
    }
    all_pass = all(validation.values())
    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for key, value in validation.items():
        print(f"{key}: {value}")
    print(f"all_pass: {all_pass}")
    print(f"Output: {OUT}")

    if not all_pass:
        raise AssertionError("S226 validation failed")


if __name__ == "__main__":
    main()
