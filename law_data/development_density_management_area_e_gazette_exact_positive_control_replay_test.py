# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE = Path(__file__).resolve().parent.parent
S221C = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_f_searchdetail_form_state_forensic.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_exact_positive_control_replay.json"

BASE_URL = "https://www.gwanbo.go.kr/"
ENTRY = urljoin(BASE_URL, "main.do")
SEARCH_PAGE = urljoin(BASE_URL, "user/search/searchKeyword.do")
INSERT_KEYWORD = urljoin(BASE_URL, "user/search/insertKeyword.do")
TARGET = "개발밀도관리구역"
POSITIVE_CONTROL = "성남시"
MAX = 8 * 1024 * 1024


def decode_bytes(b: bytes):
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return b.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", errors="ignore"), "utf-8-ignore"


def read_response(r):
    data = bytearray()
    overflow = False
    try:
        for chunk in r.iter_content(65536):
            if not chunk:
                continue
            if len(data) + len(chunk) > MAX:
                overflow = True
                break
            data.extend(chunk)
    finally:
        r.close()
    text, enc = decode_bytes(bytes(data))
    return bytes(data), text, enc, overflow


def req(session, method, url, *, data=None, referer=None):
    headers = {}
    if referer:
        headers["Referer"] = referer
    try:
        if method == "POST":
            r = session.post(url, data=data or {}, headers=headers, timeout=60, allow_redirects=True, stream=True)
        else:
            r = session.get(url, headers=headers, timeout=60, allow_redirects=True, stream=True)
        status = r.status_code
        final_url = str(r.url)
        body, text, enc, overflow = read_response(r)
        return {
            "http": status,
            "final_url": final_url,
            "bytes": len(body),
            "text": text,
            "encoding": enc,
            "overflow": overflow,
            "error": None,
        }
    except requests.RequestException as ex:
        return {
            "http": None,
            "final_url": url,
            "bytes": 0,
            "text": "",
            "encoding": None,
            "overflow": False,
            "error": f"{type(ex).__name__}: {ex}",
        }


def visible_text(text: str) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", text or "", flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def extract_links(text: str):
    rows = []
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", text or "", re.I | re.S):
        attrs = m.group(1)
        label = visible_text(m.group(2))[:600]
        href_m = re.search(r"href\s*=\s*['\"]([^'\"]*)['\"]", attrs, re.I)
        onclick_m = re.search(r"onclick\s*=\s*['\"]([^'\"]*)['\"]", attrs, re.I)
        href = html.unescape(href_m.group(1)) if href_m else ""
        onclick = html.unescape(onclick_m.group(1)) if onclick_m else ""
        rows.append({"label": label, "href": href, "onclick": onclick})
    return rows


def analyze_result(text: str):
    visible = visible_text(text)
    positive_count = visible.count(POSITIVE_CONTROL)
    links = extract_links(text)
    positive_links = [x for x in links if POSITIVE_CONTROL in x["label"]]
    detail_links = [
        x for x in links
        if re.search(r"ofctt|detail|view|download|seq|noti|pblicte|searchOfctt", x["href"] + " " + x["onclick"], re.I)
    ]
    paging_links = [
        x for x in links
        if re.search(r"pageNo|paging|goPage|movePage|fn_page|javascript:.*page", x["href"] + " " + x["onclick"] + " " + x["label"], re.I)
    ]
    explicit_no_result = bool(re.search(r"검색\s*결과가\s*없|조회\s*결과가\s*없|검색된\s*자료가\s*없|자료가\s*없습니다", visible, re.I))
    result_identity = positive_count > 0 and len(detail_links) > 0 and not explicit_no_result
    pagination = len(paging_links) > 0 or bool(re.search(r"pageNo\s*[=:]", text or "", re.I))
    return {
        "positive_count": positive_count,
        "link_count": len(links),
        "positive_link_count": len(positive_links),
        "detail_link_count": len(detail_links),
        "paging_link_count": len(paging_links),
        "explicit_no_result": explicit_no_result,
        "result_identity_signal": result_identity,
        "pagination_signal": pagination,
        "positive_links": positive_links[:20],
        "detail_links": detail_links[:30],
        "paging_links": paging_links[:20],
    }


def main():
    print("=" * 78)
    print("E-GAZETTE EXACT POSITIVE CONTROL REPLAY - S221D")
    print("=" * 78)
    print("Positive control:", POSITIVE_CONTROL)
    print("Target UQQ700 query is NOT replayed in this stage")
    print("Recovered browser flow: insertKeyword.do -> POST searchKeyword.do with pKeyword only")
    print("Search hit != designation fact")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s221c = json.loads(S221C.read_text(encoding="utf-8"))
    state = s221c.get("recovered_form_state") or {}
    summary_c = s221c.get("summary") or {}
    gate_recovered = bool(state.get("exact_function_state_recovered"))
    gate_endpoint = state.get("best_endpoint") == "searchKeyword.do"
    gate_pkeyword = bool(state.get("pkeyword_signal_seen"))
    gate_safe = summary_c.get("uqq700_final_resolution") == "UNKNOWN"
    if not (gate_recovered and gate_endpoint and gate_pkeyword and gate_safe):
        raise AssertionError("S221C recovered form-state gate not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    entry = req(session, "GET", ENTRY)
    search_preflight = req(session, "GET", SEARCH_PAGE, referer=ENTRY)

    insert = req(
        session,
        "POST",
        INSERT_KEYWORD,
        data={"keyword": POSITIVE_CONTROL, "page_gubun": "1"},
        referer=SEARCH_PAGE,
    )

    search = req(
        session,
        "POST",
        SEARCH_PAGE,
        data={"pKeyword": POSITIVE_CONTROL},
        referer=SEARCH_PAGE,
    )

    signals = analyze_result(search["text"]) if search["http"] == 200 and not search["overflow"] else {}

    technical_unknown_count = 0
    for r in (entry, search_preflight, insert, search):
        if r["http"] is None or r["error"] or r["overflow"]:
            technical_unknown_count += 1
    # insertKeyword is an auxiliary logging call in the recovered JS. HTTP 4xx/5xx there
    # is recorded, but does not by itself invalidate the search contract if the actual
    # search POST succeeds and produces identity-bearing results.

    request_contract = search["http"] == 200 and not search["error"] and not search["overflow"]
    result_identity = bool(signals.get("result_identity_signal"))
    pagination = bool(signals.get("pagination_signal"))
    replay_qualified = request_contract and result_identity and technical_unknown_count == 0

    semantic = (
        "E_GAZETTE_EXACT_POSITIVE_CONTROL_SEARCH_AND_RESULT_IDENTITY_QUALIFIED"
        if replay_qualified
        else "E_GAZETTE_EXACT_POSITIVE_CONTROL_REPLAY_UNRESOLVED"
    )
    next_action = (
        "BUILD_S222_BOUNDED_UQQ700_DESIGNATION_NOTICE_REVERSE_DISCOVERY"
        if replay_qualified
        else "INSPECT_RESULT_ROW_HTML_AND_SEARCH_RESPONSE_STATE_BEFORE_TARGET_QUERY"
    )

    out = {
        "step": "STEP 17-21-C-16-8-T-120-S221D",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "source_role": "OFFICIAL_NOTICE_IDENTITY_DISCOVERY_CANDIDATE",
        "positive_control": POSITIVE_CONTROL,
        "input_s221c": str(S221C),
        "recovered_browser_flow": {
            "keyword_log": {"method": "POST", "endpoint": INSERT_KEYWORD, "payload": {"keyword": POSITIVE_CONTROL, "page_gubun": "1"}},
            "search": {"method": "POST", "endpoint": SEARCH_PAGE, "payload": {"pKeyword": POSITIVE_CONTROL}},
        },
        "entry": {k: entry[k] for k in ("http", "final_url", "bytes", "encoding", "overflow", "error")},
        "search_preflight": {k: search_preflight[k] for k in ("http", "final_url", "bytes", "encoding", "overflow", "error")},
        "insert_keyword": {k: insert[k] for k in ("http", "final_url", "bytes", "encoding", "overflow", "error")},
        "search_response": {k: search[k] for k in ("http", "final_url", "bytes", "encoding", "overflow", "error")},
        "result_signals": signals,
        "summary": {
            "request_contract_qualified": request_contract,
            "result_identity_signal_observed": result_identity,
            "pagination_signal_observed": pagination,
            "positive_control_replay_qualified": replay_qualified,
            "technical_unknown_count": technical_unknown_count,
            "semantic_state": semantic,
            "next_action": next_action,
            "uqq700_query_replayed": False,
            "search_hit_equals_designation_fact": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "legal_absence": False,
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

    print("ENTRY HTTP:", entry["http"])
    print("SEARCH PREFLIGHT HTTP:", search_preflight["http"])
    print("INSERT KEYWORD HTTP:", insert["http"])
    print("SEARCH HTTP:", search["http"])
    print("SEARCH FINAL URL:", search["final_url"])
    print("Positive control visible count:", signals.get("positive_count", 0))
    print("Positive-control link count:", signals.get("positive_link_count", 0))
    print("Detail-link count:", signals.get("detail_link_count", 0))
    print("Paging-link count:", signals.get("paging_link_count", 0))
    print("Explicit no-result:", signals.get("explicit_no_result", False))
    print("Result identity signal:", result_identity)
    print("Pagination signal:", pagination)

    print("\nDETAIL LINK SAMPLE")
    for i, row in enumerate(signals.get("detail_links", [])[:12], 1):
        print(f"[{i:02d}] label={row['label']!r} href={row['href']!r} onclick={row['onclick']!r}")

    print("\nSUMMARY")
    print("Request contract qualified:", request_contract)
    print("Result identity signal observed:", result_identity)
    print("Pagination signal observed:", pagination)
    print("Positive control replay qualified:", replay_qualified)
    print("Technical unknown count:", technical_unknown_count)
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S221C form-state gate": gate_recovered,
        "S221C endpoint gate": gate_endpoint,
        "S221C pKeyword gate": gate_pkeyword,
        "entry preflight 200": entry["http"] == 200 and not entry["error"] and not entry["overflow"],
        "search preflight 200": search_preflight["http"] == 200 and not search_preflight["error"] and not search_preflight["overflow"],
        "search POST 200": request_contract,
        "technical unknown zero": technical_unknown_count == 0,
        "positive control result identity observed": result_identity,
        "positive control replay qualified": replay_qualified,
        "UQQ700 query not replayed": out["summary"]["uqq700_query_replayed"] is False,
        "search hit not designation fact": out["summary"]["search_hit_equals_designation_fact"] is False,
        "negative evidence disabled": not out["summary"]["negative_evidence_allowed"],
        "legal absence inference disabled": not out["summary"]["legal_absence_inference_allowed"],
        "legal absence false": out["summary"]["legal_absence"] is False,
        "designation identity not promoted": out["official_designation_identity_verified"] is False,
        "current validity not promoted": out["current_validity_verified"] is False,
        "site inclusion not promoted": out["site_spatial_inclusion_verified"] is False,
        "SITE promotion blocked": not out["site_positive_allowed"] and not out["site_negative_allowed"],
        "runtime registration blocked": not out["runtime_registration_allowed"],
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nVALIDATION")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("all_pass:", all(checks.values()))
    if not all(checks.values()):
        raise AssertionError("S221D exact e-gazette positive control replay failed")


if __name__ == "__main__":
    main()
