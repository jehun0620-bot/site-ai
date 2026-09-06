# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE = Path(__file__).resolve().parent.parent
S221A = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_search_exact_js_payload_contract_forensic.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_search_narrowed_positive_control_replay.json"

BASE_URL = "https://www.gwanbo.go.kr/"
ENTRY = urljoin(BASE_URL, "main.do")
SEARCH = urljoin(BASE_URL, "user/search/searchKeyword.do")
TARGET = "개발밀도관리구역"
POSITIVE_CONTROL = "성남시"
UA = "Mozilla/5.0"
MAX = 8 * 1024 * 1024


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
    try:
        kwargs = {
            "headers": {"Referer": referer} if referer else {},
            "timeout": 60,
            "allow_redirects": True,
            "stream": True,
        }
        if method == "POST":
            kwargs["data"] = payload or {}
            r = session.post(url, **kwargs)
        else:
            kwargs["params"] = payload or {}
            r = session.get(url, **kwargs)
        status = r.status_code
        final_url = str(r.url)
        body, text, enc, overflow = read_body(r)
        return {"http": status, "final_url": final_url, "body": body, "text": text, "encoding": enc, "overflow": overflow, "error": None}
    except requests.RequestException as ex:
        return {"http": None, "final_url": url, "body": b"", "text": "", "encoding": None, "overflow": False, "error": f"{type(ex).__name__}: {ex}"}


def strip_tags(s: str) -> str:
    s = re.sub(r"<script\b.*?</script>", " ", s or "", flags=re.I | re.S)
    s = re.sub(r"<style\b.*?</style>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def link_signals(text: str):
    links = []
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", text or "", re.I | re.S):
        attrs = m.group(1)
        label = strip_tags(m.group(2))[:500]
        href_m = re.search(r"href\s*=\s*['\"]([^'\"]*)['\"]", attrs, re.I)
        onclick_m = re.search(r"onclick\s*=\s*['\"]([^'\"]*)['\"]", attrs, re.I)
        href = html.unescape(href_m.group(1)) if href_m else ""
        onclick = html.unescape(onclick_m.group(1)) if onclick_m else ""
        links.append({"label": label, "href": href, "onclick": onclick})
    return links


def analyze(text: str):
    visible = strip_tags(text)
    positive_count = visible.count(POSITIVE_CONTROL)
    links = link_signals(text)
    detail = [x for x in links if re.search(r"ofctt|detail|view|download|seq|no", (x["href"] + " " + x["onclick"]), re.I)]
    positive_links = [x for x in links if POSITIVE_CONTROL in x["label"]]
    paging = []
    for x in links:
        blob = x["label"] + " " + x["href"] + " " + x["onclick"]
        if re.search(r"pageNo|paging|fn_page|goPage|movePage|javascript:.*page", blob, re.I):
            paging.append(x)
    hidden = {}
    for m in re.finditer(r"<input\b[^>]*>", text or "", re.I):
        tag = m.group(0)
        nm = re.search(r"(?:name|id)\s*=\s*['\"]([^'\"]+)['\"]", tag, re.I)
        val = re.search(r"value\s*=\s*['\"]([^'\"]*)['\"]", tag, re.I)
        if nm:
            hidden[nm.group(1)] = html.unescape(val.group(1)) if val else ""
    echoed = {k: v for k, v in hidden.items() if k in {"query", "pQuery_tmp", "pKeyword", "searchKeyword", "searchGubun", "pageNo", "sort", "category_num", "organ_code", "organ_name"}}
    identity_signal = positive_count > 0 and (len(positive_links) > 0 or len(detail) > 0)
    pagination_signal = len(paging) > 0 or bool(re.search(r"pageNo\s*[=:]", text or "", re.I))
    return {
        "positive_count": positive_count,
        "link_count": len(links),
        "detail_link_count": len(detail),
        "positive_link_count": len(positive_links),
        "paging_link_count": len(paging),
        "identity_signal": identity_signal,
        "pagination_signal": pagination_signal,
        "echoed_fields": echoed,
        "positive_links": positive_links[:20],
        "detail_links": detail[:30],
        "paging_links": paging[:20],
    }


def main():
    print("=" * 78)
    print("E-GAZETTE SEARCH NARROWED POSITIVE CONTROL REPLAY - S221B")
    print("=" * 78)
    print("Positive control:", POSITIVE_CONTROL)
    print("Target UQQ700 query is NOT replayed in this stage")
    print("Endpoint: POST searchKeyword.do")
    print("Purpose: qualify narrowed JS payload with positive-control result identity")
    print("Search hit != designation fact")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s221a = json.loads(S221A.read_text(encoding="utf-8"))
    inferred = s221a.get("inferred_contract") or {}
    summary_a = s221a.get("summary") or {}
    gate_exact = bool(inferred.get("exact_payload_signal_recovered"))
    gate_endpoint = inferred.get("best_endpoint") == "searchKeyword.do"
    gate_method = inferred.get("best_method") == "POST"
    gate_safe = summary_a.get("uqq700_final_resolution") == "UNKNOWN"
    if not (gate_exact and gate_endpoint and gate_method and gate_safe):
        raise AssertionError("S221A narrowed contract gate not satisfied")

    # Bounded variants only.  Values are limited to fields recovered as strong
    # S221A signals; no target UQQ700 query is used here.
    cases = [
        ("PKEYWORD_SEARCHKEYWORD", {"pKeyword": POSITIVE_CONTROL, "searchKeyword": POSITIVE_CONTROL, "pageNo": "1"}),
        ("QUERY_PQUERY", {"query": POSITIVE_CONTROL, "pQuery_tmp": POSITIVE_CONTROL, "pageNo": "1"}),
        ("FOUR_QUERY_FIELDS", {"query": POSITIVE_CONTROL, "pQuery_tmp": POSITIVE_CONTROL, "pKeyword": POSITIVE_CONTROL, "searchKeyword": POSITIVE_CONTROL, "pageNo": "1"}),
        ("FOUR_PLUS_GUBUN_EMPTY", {"query": POSITIVE_CONTROL, "pQuery_tmp": POSITIVE_CONTROL, "pKeyword": POSITIVE_CONTROL, "searchKeyword": POSITIVE_CONTROL, "searchGubun": "", "pageNo": "1"}),
        ("FOUR_PLUS_GUBUN_ALL", {"query": POSITIVE_CONTROL, "pQuery_tmp": POSITIVE_CONTROL, "pKeyword": POSITIVE_CONTROL, "searchKeyword": POSITIVE_CONTROL, "searchGubun": "all", "pageNo": "1"}),
        ("FOUR_PLUS_SORT", {"query": POSITIVE_CONTROL, "pQuery_tmp": POSITIVE_CONTROL, "pKeyword": POSITIVE_CONTROL, "searchKeyword": POSITIVE_CONTROL, "pageNo": "1", "sort": ""}),
        ("FOUR_PLUS_CATEGORY", {"query": POSITIVE_CONTROL, "pQuery_tmp": POSITIVE_CONTROL, "pKeyword": POSITIVE_CONTROL, "searchKeyword": POSITIVE_CONTROL, "pageNo": "1", "category_num": ""}),
        ("FOUR_PLUS_ORGAN", {"query": POSITIVE_CONTROL, "pQuery_tmp": POSITIVE_CONTROL, "pKeyword": POSITIVE_CONTROL, "searchKeyword": POSITIVE_CONTROL, "pageNo": "1", "organ_code": "", "organ_name": ""}),
    ]

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    pre = request(session, "GET", ENTRY)

    results = []
    technical_unknown_count = 0
    for i, (name, payload) in enumerate(cases, 1):
        r = request(session, "POST", SEARCH, payload=payload, referer=ENTRY)
        if r["http"] != 200 or r["error"] or r["overflow"]:
            technical_unknown_count += 1
        sig = analyze(r["text"]) if r["http"] == 200 and not r["overflow"] else {}
        accepted = bool(sig.get("identity_signal"))
        row = {
            "case": name,
            "method": "POST",
            "endpoint": SEARCH,
            "payload": payload,
            "response": {"http": r["http"], "final_url": r["final_url"], "bytes": len(r["body"]), "encoding": r["encoding"], "overflow": r["overflow"], "error": r["error"]},
            "signals": sig,
            "accepted_positive_control_identity": accepted,
        }
        results.append(row)
        print(f"[{i:02d}/{len(cases):02d}] {name} http={r['http']} positive={sig.get('positive_count', 0)} positive_links={sig.get('positive_link_count', 0)} detail={sig.get('detail_link_count', 0)} paging={sig.get('paging_link_count', 0)} accepted={accepted}")

    accepted = [x for x in results if x["accepted_positive_control_identity"]]
    best = max(accepted, key=lambda x: (x["signals"].get("positive_link_count", 0), x["signals"].get("positive_count", 0), x["signals"].get("detail_link_count", 0))) if accepted else None
    result_identity = bool(best)
    pagination = bool(best and best["signals"].get("pagination_signal"))
    request_contract = bool(best and best["response"]["http"] == 200)
    replay_qualified = request_contract and result_identity and technical_unknown_count == 0

    semantic = "E_GAZETTE_NARROWED_POSITIVE_CONTROL_REPLAY_QUALIFIED" if replay_qualified else "E_GAZETTE_NARROWED_POSITIVE_CONTROL_REPLAY_UNRESOLVED"
    next_action = "BUILD_S222_BOUNDED_UQQ700_DESIGNATION_NOTICE_REVERSE_DISCOVERY" if replay_qualified else "INSPECT_EXACT_F_SEARCHDETAIL_FUNCTION_AND_FORM_STATE_BEFORE_TARGET_QUERY"

    out = {
        "step": "STEP 17-21-C-16-8-T-118-S221B",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "source_role": "OFFICIAL_NOTICE_IDENTITY_DISCOVERY_CANDIDATE",
        "positive_control": POSITIVE_CONTROL,
        "input_s221a": str(S221A),
        "preflight": {"http": pre["http"], "error": pre["error"], "overflow": pre["overflow"]},
        "cases": results,
        "best_case": best,
        "summary": {
            "accepted_positive_control_case_count": len(accepted),
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

    print("\nSUMMARY")
    print("Accepted positive-control case count:", len(accepted))
    print("Best case:", best["case"] if best else None)
    print("Best payload:", best["payload"] if best else None)
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
        "S221A exact payload gate": gate_exact,
        "S221A endpoint gate": gate_endpoint,
        "S221A method gate": gate_method,
        "entry preflight 200": pre["http"] == 200 and not pre["error"] and not pre["overflow"],
        "bounded narrowed cases emitted": len(results) == len(cases),
        "technical unknown zero": technical_unknown_count == 0,
        "positive control request qualified": request_contract,
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
        raise AssertionError("S221B e-gazette narrowed positive control replay failed")


if __name__ == "__main__":
    main()
