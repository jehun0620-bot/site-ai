# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
S220A = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_search_js_submit_contract_forensic.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_search_positive_control_replay.json"

BASE_URL = "https://www.gwanbo.go.kr/"
ENTRY = urljoin(BASE_URL, "main.do")
SEARCH = urljoin(BASE_URL, "user/search/searchKeyword.do")
ADVANCED = urljoin(BASE_URL, "user/search/searchDetail.do")
POSITIVE_CONTROL = "성남시"
TARGET = "개발밀도관리구역"
UA = "Mozilla/5.0"
MAX = 8 * 1024 * 1024
MAX_CASES = 12


def dec(b: bytes):
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return b.decode(enc), enc
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", errors="ignore"), "utf-8-ignore"


def read_body(r):
    buf = bytearray()
    overflow = False
    try:
        for chunk in r.iter_content(65536):
            if not chunk:
                continue
            if len(buf) + len(chunk) > MAX:
                overflow = True
                break
            buf.extend(chunk)
    finally:
        r.close()
    text, enc = dec(bytes(buf))
    return bytes(buf), text, enc, overflow


def request(session, method, url, payload=None, referer=None):
    headers = {"Referer": referer or ADVANCED}
    try:
        if method == "GET":
            r = session.get(url, params=payload or {}, headers=headers, timeout=60, allow_redirects=True, stream=True)
        else:
            r = session.post(url, data=payload or {}, headers=headers, timeout=60, allow_redirects=True, stream=True)
        status = r.status_code
        final_url = str(r.url)
        ctype = r.headers.get("Content-Type")
        body, text, enc, overflow = read_body(r)
        return {
            "http": status,
            "final_url": final_url,
            "content_type": ctype,
            "body": body,
            "text": text,
            "encoding": enc,
            "overflow": overflow,
            "error": None,
        }
    except requests.RequestException as ex:
        return {
            "http": None,
            "final_url": url,
            "content_type": None,
            "body": b"",
            "text": "",
            "encoding": None,
            "overflow": False,
            "error": f"{type(ex).__name__}: {ex}",
        }


def visible_text(text: str) -> str:
    x = re.sub(r"<script\b[^>]*>.*?</script>", " ", text or "", flags=re.I | re.S)
    x = re.sub(r"<style\b[^>]*>.*?</style>", " ", x, flags=re.I | re.S)
    x = re.sub(r"<[^>]+>", " ", x)
    return re.sub(r"\s+", " ", html.unescape(x)).strip()


def attrs(tag: str):
    out = {}
    for m in re.finditer(r"([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*([\"'])(.*?)\2", tag or "", re.S):
        out[m.group(1).lower()] = html.unescape(m.group(3))
    return out


def extract_links(text: str, base: str):
    rows = []
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", text or "", re.I | re.S):
        a = attrs(m.group(1))
        label = visible_text(m.group(2))
        href = a.get("href")
        onclick = a.get("onclick")
        if not href and not onclick:
            continue
        abs_href = urljoin(base, href) if href and not href.lower().startswith("javascript:") else href
        blob = " ".join(x for x in (label, href, onclick) if x)
        if not re.search(r"ofctt|detail|view|download|search|gwanbo|관보|공고|고시|성남|시행", blob, re.I):
            continue
        q = parse_qs(urlparse(abs_href).query) if abs_href and abs_href.startswith("http") else {}
        rows.append({
            "text": label[:500],
            "href": abs_href,
            "onclick": onclick[:1000] if onclick else None,
            "query": {k: v[:10] for k, v in q.items()},
        })
        if len(rows) >= 250:
            break
    return rows


def extract_pagination(text: str, base: str):
    out = []
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", text or "", re.I | re.S):
        a = attrs(m.group(1))
        label = visible_text(m.group(2))
        href = a.get("href") or ""
        onclick = a.get("onclick") or ""
        blob = " ".join((label, href, onclick))
        if re.search(r"pageNo|paging|goPage|fnPage|javascript:.*page|[?&]page=", blob, re.I):
            out.append({
                "text": label[:100],
                "href": urljoin(base, href) if href and not href.lower().startswith("javascript:") else href or None,
                "onclick": onclick[:700] or None,
            })
        if len(out) >= 100:
            break
    for pat in (r"pageNo\s*[:=]\s*[\"']?(\d+)", r"goPage\s*\(\s*(\d+)", r"fnPage\s*\(\s*(\d+)"):
        for m in re.finditer(pat, text or "", re.I):
            item = {"text": m.group(1), "href": None, "onclick": m.group(0)}
            if item not in out:
                out.append(item)
    return out[:100]


def result_signals(text: str):
    vis = visible_text(text)
    positive_count = vis.count(POSITIVE_CONTROL)
    no_result = any(x in vis for x in ("검색결과가 없습니다", "검색 결과가 없습니다", "조회된 결과가 없습니다", "조회 결과가 없습니다"))
    result_words = sum(vis.count(x) for x in ("검색결과", "검색 결과", "총 ", "건", "관보", "고시", "공고"))
    return {
        "positive_control_visible_count": positive_count,
        "explicit_no_result": no_result,
        "result_word_signal_count": result_words,
        "visible_sample": vis[:1200],
    }


def replay_cases():
    # S220A recovered these names/selectors. Keep bounded variants only.
    base = [
        ("GET_QUERY", "GET", {"query": POSITIVE_CONTROL, "pageNo": "1"}),
        ("GET_KEYWORD", "GET", {"keyword": POSITIVE_CONTROL, "pageNo": "1"}),
        ("GET_SEARCHKEYWORD", "GET", {"searchKeyword": POSITIVE_CONTROL, "pageNo": "1"}),
        ("GET_PKEYWORD", "GET", {"pKeyword": POSITIVE_CONTROL, "pageNo": "1"}),
        ("GET_QUERY_MENU", "GET", {"query": POSITIVE_CONTROL, "pageNo": "1", "menuMode": "m2"}),
        ("GET_KEYWORD_MENU", "GET", {"keyword": POSITIVE_CONTROL, "pageNo": "1", "menuMode": "m2"}),
        ("POST_QUERY", "POST", {"query": POSITIVE_CONTROL, "pageNo": "1"}),
        ("POST_KEYWORD", "POST", {"keyword": POSITIVE_CONTROL, "pageNo": "1"}),
        ("POST_SEARCHKEYWORD", "POST", {"searchKeyword": POSITIVE_CONTROL, "pageNo": "1"}),
        ("POST_PKEYWORD", "POST", {"pKeyword": POSITIVE_CONTROL, "pageNo": "1"}),
        ("POST_QUERY_MENU", "POST", {"query": POSITIVE_CONTROL, "pageNo": "1", "menuMode": "m2"}),
        ("POST_KEYWORD_MENU", "POST", {"keyword": POSITIVE_CONTROL, "pageNo": "1", "menuMode": "m2"}),
    ]
    return base[:MAX_CASES]


def main():
    print("=" * 78)
    print("E-GAZETTE SEARCH POSITIVE CONTROL REPLAY - S221")
    print("=" * 78)
    print("Positive control:", POSITIVE_CONTROL)
    print("Target UQQ700 query is NOT replayed in this stage")
    print("Purpose: qualify request/result identity/pagination contract only")
    print("Search hit != designation fact")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s220a = json.loads(S220A.read_text(encoding="utf-8"))
    agg = s220a.get("aggregated_contract") or {}
    summary = s220a.get("summary") or {}
    if not agg.get("contract_recovered_for_positive_control_replay"):
        raise AssertionError("S220A contract gate not qualified")
    if summary.get("technical_unknown_count") != 0:
        raise AssertionError("S220A technical state not clean")
    if summary.get("query_replay_performed") is not False:
        raise AssertionError("S220A stage boundary violated")

    session = requests.Session()
    session.headers.update({
        "User-Agent": UA,
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    pre_entry = request(session, "GET", ENTRY, {}, None)
    pre_search = request(session, "GET", ADVANCED, {}, ENTRY)

    cases = []
    for i, (name, method, payload) in enumerate(replay_cases(), 1):
        r = request(session, method, SEARCH, payload, ADVANCED)
        sig = result_signals(r["text"])
        links = extract_links(r["text"], r["final_url"] or SEARCH)
        pagination = extract_pagination(r["text"], r["final_url"] or SEARCH)
        detail_links = [x for x in links if re.search(r"ofctt|detail|view|download|ofcttNo|ofcttSeq|seq|no=", " ".join(str(v or "") for v in x.values()), re.I)]
        accepted = (
            r["http"] == 200
            and not r["error"]
            and not r["overflow"]
            and sig["positive_control_visible_count"] > 0
            and not sig["explicit_no_result"]
            and (len(detail_links) > 0 or len(pagination) > 0 or sig["result_word_signal_count"] > 5)
        )
        row = {
            "case": name,
            "method": method,
            "payload": payload,
            "response": {
                "http": r["http"],
                "final_url": r["final_url"],
                "bytes": len(r["body"]),
                "encoding": r["encoding"],
                "overflow": r["overflow"],
                "error": r["error"],
            },
            "signals": sig,
            "links": links[:80],
            "detail_link_candidates": detail_links[:50],
            "pagination": pagination[:50],
            "accepted_positive_control_contract": accepted,
        }
        cases.append(row)
        print(
            f"[{i:02d}/{len(replay_cases()):02d}] {name} method={method} http={r['http']} "
            f"positive={sig['positive_control_visible_count']} links={len(links)} "
            f"detail={len(detail_links)} paging={len(pagination)} accepted={accepted}"
        )

    accepted_cases = [x for x in cases if x["accepted_positive_control_contract"]]
    technical_unknown_count = sum(
        1 for x in cases
        if x["response"]["http"] != 200 or x["response"]["error"] or x["response"]["overflow"]
    )

    best = None
    if accepted_cases:
        best = max(
            accepted_cases,
            key=lambda x: (
                len(x["detail_link_candidates"]),
                len(x["pagination"]),
                x["signals"]["positive_control_visible_count"],
            ),
        )

    request_contract_qualified = best is not None
    result_identity_signal = bool(best and (best["detail_link_candidates"] or best["links"]))
    pagination_signal = bool(best and best["pagination"])
    replay_qualified = request_contract_qualified and result_identity_signal

    if replay_qualified:
        semantic = "E_GAZETTE_POSITIVE_CONTROL_SEARCH_AND_RESULT_IDENTITY_QUALIFIED"
        next_action = "BUILD_S222_UQQ700_BOUNDED_DESIGNATION_NOTICE_REVERSE_DISCOVERY"
    elif request_contract_qualified:
        semantic = "E_GAZETTE_POSITIVE_CONTROL_REQUEST_QUALIFIED_RESULT_IDENTITY_UNRESOLVED"
        next_action = "RECOVER_E_GAZETTE_RESULT_ROW_DETAIL_IDENTITY_BEFORE_UQQ700_QUERY"
    else:
        semantic = "E_GAZETTE_POSITIVE_CONTROL_REPLAY_UNRESOLVED"
        next_action = "NARROW_JS_PAYLOAD_CONTRACT_FROM_CAPTURED_CONTEXTS_BEFORE_UQQ700_QUERY"

    out = {
        "step": "STEP 17-21-C-16-8-T-116-S221",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "source_role": "OFFICIAL_NOTICE_IDENTITY_DISCOVERY_CANDIDATE",
        "input_s220a": str(S220A),
        "positive_control": POSITIVE_CONTROL,
        "uqq700_query_replayed": False,
        "preflight": {
            "entry_http": pre_entry["http"],
            "advanced_http": pre_search["http"],
            "entry_error": pre_entry["error"],
            "advanced_error": pre_search["error"],
        },
        "cases": cases,
        "qualified_contract": {
            "accepted_case_count": len(accepted_cases),
            "best_case": best,
            "request_contract_qualified": request_contract_qualified,
            "result_identity_signal_observed": result_identity_signal,
            "pagination_signal_observed": pagination_signal,
            "positive_control_replay_qualified": replay_qualified,
        },
        "summary": {
            "technical_unknown_count": technical_unknown_count,
            "semantic_state": semantic,
            "next_action": next_action,
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

    print("\nSUMMARY")
    print("Accepted positive-control case count:", len(accepted_cases))
    print("Best case:", best["case"] if best else None)
    print("Best method:", best["method"] if best else None)
    print("Best payload:", best["payload"] if best else None)
    print("Request contract qualified:", request_contract_qualified)
    print("Result identity signal observed:", result_identity_signal)
    print("Pagination signal observed:", pagination_signal)
    print("Positive control replay qualified:", replay_qualified)
    print("Technical unknown count:", technical_unknown_count)
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S220A contract gate": agg.get("contract_recovered_for_positive_control_replay") is True,
        "entry preflight 200": pre_entry["http"] == 200,
        "advanced preflight 200": pre_search["http"] == 200,
        "bounded replay cases emitted": len(cases) == len(replay_cases()) and 1 <= len(cases) <= MAX_CASES,
        "UQQ700 query not replayed": out["uqq700_query_replayed"] is False,
        "positive control request qualified": request_contract_qualified,
        "positive control result identity observed": result_identity_signal,
        "positive control replay qualified": replay_qualified,
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
        raise AssertionError("S221 e-gazette positive control replay failed")


if __name__ == "__main__":
    main()
