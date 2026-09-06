# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_national_law_seongnam_urban_planning_ordinance_historical_body_representation_forensic.json"

ENTRY = "https://www.law.go.kr/ordinSc.do"
DETAIL_PAGE = "https://www.law.go.kr/ordinInfoP.do"
DETAIL_AJAX = "https://www.law.go.kr/ordinInfoR.do"
TARGET = "성남시 도시계획 조례"
UA = "Mozilla/5.0"
MAX = 8 * 1024 * 1024

CASES = [
    {"label": "CURRENT", "ordin_seq": "2111431", "nw_yn": "3", "anc_yd": "20260224", "anc_no": "4356"},
    {"label": "OLDEST", "ordin_seq": "1061048", "nw_yn": "N", "anc_yd": "20080314", "anc_no": "2203"},
]


def dec(b: bytes):
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return b.decode(enc), enc
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", errors="ignore"), "utf-8-ignore"


def clean(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<script\b[^>]*>.*?</script>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<style\b[^>]*>.*?</style>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def compact(s: str) -> str:
    return re.sub(r"\s+", "", clean(s or ""))


def read_body(r):
    b = bytearray()
    overflow = False
    try:
        for chunk in r.iter_content(65536):
            if not chunk:
                continue
            if len(b) + len(chunk) > MAX:
                overflow = True
                break
            b.extend(chunk)
    finally:
        r.close()
    text, enc = dec(bytes(b))
    return bytes(b), text, enc, overflow


def get(session, url, *, params=None, referer=None):
    headers = {"Referer": referer} if referer else {}
    try:
        r = session.get(url, params=params, headers=headers, timeout=60, allow_redirects=True, stream=True)
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


def post(session, url, *, data, referer=None):
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    if referer:
        headers["Referer"] = referer
    try:
        r = session.post(url, data=data, headers=headers, timeout=60, allow_redirects=True, stream=True)
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


def article_count(text: str) -> int:
    return len(re.findall(r"제\s*\d+\s*조(?:의\s*\d+)?", clean(text or "")))


def capture_functions(text: str):
    names = []
    for m in re.finditer(r"function\s+([A-Za-z_$][\w$]*)\s*\(", text or "", re.I):
        name = m.group(1)
        if re.search(r"ordin|conDat|content|info|view|load|ajax|law|jo|bonmun", name, re.I) and name not in names:
            names.append(name)
    out = {}
    for name in names[:120]:
        hits = []
        for m in re.finditer(r"function\s+" + re.escape(name) + r"\s*\(([^)]*)\)\s*\{", text or "", re.I):
            start = m.start()
            i = m.end()
            depth = 1
            quote = None
            esc = False
            while i < len(text) and depth > 0:
                ch = text[i]
                if quote:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == quote:
                        quote = None
                else:
                    if ch in ('"', "'"):
                        quote = ch
                    elif ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                i += 1
            body = text[start:i] if depth == 0 else text[start:min(len(text), start + 12000)]
            hits.append({"args": m.group(1), "body": re.sub(r"\s+", " ", body).strip()[:12000]})
        if hits:
            out[name] = hits
    return out


def extract_contract_signals(text: str):
    text = text or ""
    endpoints = sorted(set(re.findall(r"[A-Za-z0-9_./-]+\.do(?:\?[^\"'<>\s]*)?", text, re.I)))
    likely_endpoints = [
        x for x in endpoints
        if re.search(r"ordin|info|cont|body|conDat|jo|law", x, re.I)
    ]
    ajax_contexts = []
    for m in re.finditer(r"(?:ajax|\$\.post|\$\.get|\.load\s*\(|url\s*:)", text, re.I):
        ctx = re.sub(r"\s+", " ", text[max(0, m.start() - 1000):min(len(text), m.start() + 3000)]).strip()
        if ctx not in ajax_contexts:
            ajax_contexts.append(ctx[:4000])
        if len(ajax_contexts) >= 40:
            break
    ids = sorted(set(re.findall(r"(?:id|name)=[\"']([^\"']+)[\"']", text, re.I)))
    likely_dom = [x for x in ids if re.search(r"ordin|law|cont|body|jo|view|info|content", x, re.I)]
    hidden = {}
    for m in re.finditer(r"<input\b([^>]*)>", text, re.I):
        attrs = m.group(1)
        km = re.search(r"\b(?:id|name)=[\"']([^\"']+)", attrs, re.I)
        if not km:
            continue
        key = km.group(1)
        if re.search(r"ordin|conDat|gubun|nwYn|seq|id|anc", key, re.I):
            vm = re.search(r"\bvalue=[\"']([^\"']*)", attrs, re.I)
            hidden[key] = html.unescape(vm.group(1)) if vm else ""
    scripts = re.findall(r"<script\b[^>]*src=[\"']([^\"']+)[\"']", text, re.I)
    return {
        "endpoints": endpoints[:200],
        "likely_endpoints": likely_endpoints[:100],
        "ajax_contexts": ajax_contexts,
        "likely_dom_ids": likely_dom[:100],
        "hidden_identity": hidden,
        "script_srcs": scripts[:100],
        "functions": capture_functions(text),
    }


def representation_metrics(text: str):
    visible = clean(text)
    return {
        "raw_length": len(text or ""),
        "visible_length": len(visible),
        "article_signal_count": article_count(text),
        "target_seen": compact(TARGET) in compact(text),
        "uqq700_term_seen": "개발밀도관리구역" in compact(text),
    }


def main():
    print("=" * 76)
    print("NATIONAL LAW SEONGNAM URBAN PLANNING ORDINANCE HISTORICAL BODY REPRESENTATION FORENSIC - S218")
    print("=" * 76)
    print("Purpose: recover the actual ordinance-body representation contract")
    print("Scope: 2 bounded versions only")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})

    pre = get(s, ENTRY)
    print("PRECHECK HTTP:", pre["http"], "ERROR:", pre["error"])

    cases = []
    external_scripts = {}

    for case in CASES:
        seq = case["ordin_seq"]
        params = {
            "ordinSeq": seq,
            "chrClsCd": "010202",
            "gubun": "ELIS",
            "nwYn": case["nw_yn"],
            "conDatGubunCd": "1",
        }
        page = get(s, DETAIL_PAGE, params=params, referer=ENTRY)
        page_signals = extract_contract_signals(page["text"])
        page_metrics = representation_metrics(page["text"])

        # Browser-equivalent AJAX detail replay, inherited from the already recovered S215 current-detail contract.
        post_data = {
            "ordinSeq": seq,
            "chrClsCd": "010202",
            "nwYn": case["nw_yn"],
            "vSct": TARGET,
            "conDatGubunCd": "1",
            "gubun": "ELIS",
        }
        ajax = post(s, DETAIL_AJAX, data=post_data, referer=page["final_url"] or DETAIL_PAGE)
        ajax_signals = extract_contract_signals(ajax["text"])
        ajax_metrics = representation_metrics(ajax["text"])

        for src in page_signals["script_srcs"] + ajax_signals["script_srcs"]:
            abs_url = urljoin("https://www.law.go.kr/", src)
            if abs_url in external_scripts:
                continue
            if not re.search(r"ordin|law|common|search|info", abs_url, re.I):
                continue
            er = get(s, abs_url, referer=page["final_url"] or DETAIL_PAGE)
            external_scripts[abs_url] = {
                "http": er["http"],
                "error": er["error"],
                "bytes": len(er["body"]),
                "signals": extract_contract_signals(er["text"]) if er["http"] == 200 else {},
            }
            if len(external_scripts) >= 20:
                break

        body_source = None
        if ajax_metrics["article_signal_count"] >= 3:
            body_source = "POST_ordinInfoR.do"
        elif page_metrics["article_signal_count"] >= 3:
            body_source = "GET_ordinInfoP.do"

        item = {
            "case": case,
            "page_request": {"method": "GET", "url": DETAIL_PAGE, "params": params},
            "page_response": {
                "http": page["http"],
                "final_url": page["final_url"],
                "bytes": len(page["body"]),
                "encoding": page["encoding"],
                "overflow": page["overflow"],
                "error": page["error"],
            },
            "page_metrics": page_metrics,
            "page_contract_signals": page_signals,
            "ajax_request": {"method": "POST", "url": DETAIL_AJAX, "data": post_data},
            "ajax_response": {
                "http": ajax["http"],
                "final_url": ajax["final_url"],
                "bytes": len(ajax["body"]),
                "encoding": ajax["encoding"],
                "overflow": ajax["overflow"],
                "error": ajax["error"],
            },
            "ajax_metrics": ajax_metrics,
            "ajax_contract_signals": ajax_signals,
            "body_source_candidate": body_source,
            "legal_fact_promoted": False,
            "legal_absence_inferred": False,
            "site_fact_promoted": False,
        }
        cases.append(item)
        print(
            f"{case['label']}: seq={seq} "
            f"GET={page['http']} GET_articles={page_metrics['article_signal_count']} "
            f"POST={ajax['http']} POST_articles={ajax_metrics['article_signal_count']} "
            f"candidate={body_source}"
        )

    qualified_candidates = [x for x in cases if x["body_source_candidate"]]
    same_candidate = len(qualified_candidates) == len(cases) and len({x["body_source_candidate"] for x in cases}) == 1
    technical_unknown_count = sum(
        1
        for x in cases
        if x["page_response"]["http"] != 200
        or x["page_response"]["error"]
        or x["page_response"]["overflow"]
        or x["ajax_response"]["http"] != 200
        or x["ajax_response"]["error"]
        or x["ajax_response"]["overflow"]
    )

    if same_candidate:
        representation_state = "HISTORICAL_BODY_REPRESENTATION_CANDIDATE_QUALIFIED_FOR_BOUNDED_REPLAY"
        next_action = "BUILD_S219_42_VERSION_BODY_REPLAY_USING_QUALIFIED_REPRESENTATION"
    else:
        # Contract signals are still useful even if neither direct response contains article text.
        any_contract_signal = any(
            x["page_contract_signals"]["likely_endpoints"]
            or x["page_contract_signals"]["ajax_contexts"]
            or x["ajax_contract_signals"]["likely_endpoints"]
            or x["ajax_contract_signals"]["ajax_contexts"]
            for x in cases
        ) or any(v.get("signals", {}).get("likely_endpoints") for v in external_scripts.values())
        representation_state = (
            "HISTORICAL_BODY_REPRESENTATION_CONTRACT_SIGNALS_CAPTURED_BUT_NOT_YET_QUALIFIED"
            if any_contract_signal
            else "HISTORICAL_BODY_REPRESENTATION_CONTRACT_UNRESOLVED"
        )
        next_action = "INSPECT_CAPTURED_JS_ENDPOINT_AND_AJAX_CONTRACT_SIGNALS_BEFORE_42_VERSION_REPLAY"

    out = {
        "step": "STEP 17-21-C-16-8-T-112-S218",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY",
        "source_role": "AUTHORITY_CONTEXT_TIMELINE_ANCHOR_ONLY",
        "purpose": "Recover historical ordinance body representation contract after S217 returned 42 technical unknowns with zero article signals.",
        "preflight": {"http": pre["http"], "error": pre["error"]},
        "cases": cases,
        "external_scripts": external_scripts,
        "summary": {
            "bounded_case_count": len(cases),
            "qualified_body_source_candidate_count": len(qualified_candidates),
            "same_candidate_across_cases": same_candidate,
            "body_source_candidate": qualified_candidates[0]["body_source_candidate"] if same_candidate else None,
            "technical_unknown_count": technical_unknown_count,
            "semantic_state": representation_state,
            "next_action": next_action,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "legal_absence": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    checks = {
        "preflight 200": pre["http"] == 200,
        "2 bounded cases emitted": len(cases) == 2,
        "current case present": any(x["case"]["ordin_seq"] == "2111431" for x in cases),
        "oldest case present": any(x["case"]["ordin_seq"] == "1061048" for x in cases),
        "GET responses 200": all(x["page_response"]["http"] == 200 for x in cases),
        "POST responses 200": all(x["ajax_response"]["http"] == 200 for x in cases),
        "negative evidence disabled": not out["summary"]["negative_evidence_allowed"],
        "legal absence inference disabled": not out["summary"]["legal_absence_inference_allowed"],
        "legal absence false": out["summary"]["legal_absence"] is False,
        "SITE promotion blocked": not out["site_positive_allowed"] and not out["site_negative_allowed"],
        "runtime registration blocked": not out["runtime_registration_allowed"],
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nSUMMARY")
    print("Semantic:", representation_state)
    print("Body source candidate:", out["summary"]["body_source_candidate"])
    print("Same candidate across cases:", same_candidate)
    print("Technical unknown count:", technical_unknown_count)
    print("Next action:", next_action)
    print("UQQ700 final resolution:", out["summary"]["uqq700_final_resolution"])
    print("Output:", OUT)

    print("\nVALIDATION")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("all_pass:", all(checks.values()))
    if not all(checks.values()):
        raise AssertionError("S218 historical body representation forensic failed")


if __name__ == "__main__":
    main()
