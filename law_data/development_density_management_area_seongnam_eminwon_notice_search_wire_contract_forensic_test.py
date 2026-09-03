# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_seongnam_eminwon_notice_search_wire_contract_forensic.json"
URL = "http://eminwon.seongnam.go.kr/emwp/gov/mogaha/ntis/web/ofr/action/OfrAction.do"
HOST = "eminwon.seongnam.go.kr"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 8 * 1024 * 1024

DETAIL_PARAMS = {
    "Key": "B_Subject",
    "context": "NTIS",
    "countYn": "Y",
    "homepage_pbs_yn": "Y",
    "initValue": "Y",
    "jndinm": "OfrNotAncmtEJB",
    "list_gubun": "A",
    "method": "selectOfrNotAncmt",
    "methodnm": "selectOfrNotAncmtRegst",
    "not_ancmt_se_code": "01,02,03,04,05,06,07",
    "not_ancmt_mgt_no": "66727",
    "ofr_pageSize": "10",
    "subCheck": "Y",
    "title": "고시공고",
}

FORM_RE = re.compile(r'<form\b([^>]*)>(.*?)</form>', re.I | re.S)
INPUT_RE = re.compile(r'<input\b([^>]*)>', re.I | re.S)
BUTTON_RE = re.compile(r'<(?:button|input)\b([^>]*)>(.*?)</(?:button)>|<input\b([^>]*)>', re.I | re.S)
ATTR_RE = re.compile(r'([:\w-]+)\s*=\s*(["\'])(.*?)\2', re.I | re.S)
SCRIPT_RE = re.compile(r'<script\b[^>]*>(.*?)</script>', re.I | re.S)
FUNC_DEF_RE = re.compile(r'function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{(.*?)\}', re.I | re.S)
EVENT_NAME_RE = re.compile(r'\b(?:onclick|onsubmit)\s*=\s*["\']([^"\']+)["\']', re.I)
KEYWORDS = ("not_ancmt_sj", "not_ancmt_cn", "pageIndex", "methodnm", "selectOfrNotAncmt", "search", "검색", "Key", "B_Subject")


def host(url):
    return (urlparse(url).hostname or "").lower()


def attrs_dict(raw):
    return {m.group(1).lower(): html.unescape(m.group(3)) for m in ATTR_RE.finditer(raw or "")}


def bounded_get(session):
    try:
        r = session.get(URL, params=DETAIL_PARAMS, timeout=25, stream=True, allow_redirects=True)
        buf = bytearray()
        overflow = False
        try:
            for chunk in r.iter_content(65536):
                if not chunk:
                    continue
                if len(buf) + len(chunk) > MAX_BYTES:
                    overflow = True
                    break
                buf.extend(chunk)
        finally:
            r.close()
        return {
            "state": "HTTP_RESPONSE_CAPTURED" if not overflow else "TECHNICAL_REQUEST_UNKNOWN",
            "http": r.status_code,
            "final_url": str(r.url),
            "body": bytes(buf),
            "overflow": overflow,
            "error": "RESPONSE_SIZE_LIMIT_EXCEEDED" if overflow else None,
        }
    except requests.RequestException as exc:
        return {
            "state": "TECHNICAL_REQUEST_UNKNOWN",
            "http": None,
            "final_url": URL,
            "body": b"",
            "overflow": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def decode(raw):
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            t = raw.decode(enc)
            if "고시" in t or "공고" in t:
                return t, enc
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="ignore"), "utf-8-ignore"


def main():
    print("=" * 60)
    print("SEONGNAM EMINWON NOTICE SEARCH WIRE CONTRACT FORENSIC - S150")
    print("=" * 60)
    print("Search request execution: DISABLED")
    print("UQQ700 target search: DISABLED")
    print("Negative evidence: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    res = bounded_get(session)
    text, encoding = decode(res["body"])
    ok_host = host(res["final_url"]) == HOST
    print("DETAIL STATE:", res["state"], "| HTTP:", res["http"], "| HOST_OK:", ok_host, "| ENCODING:", encoding)

    form_events = []
    submit_controls = []
    relevant_functions = []
    script_snippets = []

    if res["state"] == "HTTP_RESPONSE_CAPTURED" and res["http"] == 200 and ok_host:
        for attrs, body in FORM_RE.findall(text):
            ad = attrs_dict(attrs)
            events = {k: v for k, v in ad.items() if k in ("onsubmit", "onclick")}
            if events:
                form_events.append(events)

            for raw in INPUT_RE.findall(body):
                d = attrs_dict(raw)
                typ = d.get("type", "").lower()
                if typ in ("submit", "button", "image") or "onclick" in d:
                    submit_controls.append({k: d.get(k) for k in ("type", "name", "value", "id", "onclick") if d.get(k) is not None})

        for sm in SCRIPT_RE.findall(text):
            for fn, args, body in FUNC_DEF_RE.findall(sm):
                hay = (fn + " " + args + " " + body).lower()
                if any(k.lower() in hay for k in KEYWORDS):
                    compact = re.sub(r"\s+", " ", body).strip()
                    relevant_functions.append({"name": fn, "args": args.strip(), "body": compact[:2000]})
            compact_script = re.sub(r"\s+", " ", sm).strip()
            if any(k.lower() in compact_script.lower() for k in KEYWORDS):
                script_snippets.append(compact_script[:4000])

    out = {
        "step": "STEP 17-21-C-16-8-T-46-S150",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "SEONGNAM_EMINWON_HISTORICAL_NOTICE",
        "summary": {
            "form_event_count": len(form_events),
            "submit_control_count": len(submit_controls),
            "relevant_function_count": len(relevant_functions),
            "script_snippet_count": len(script_snippets),
            "transport_unknown_count": 1 if res["state"] == "TECHNICAL_REQUEST_UNKNOWN" else 0,
            "semantic_state": "SEONGNAM_EMINWON_NOTICE_SEARCH_WIRE_CONTRACT_FORENSIC_CAPTURED",
            "negative_evidence_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "request": {k: v for k, v in res.items() if k != "body"},
        "encoding": encoding,
        "form_events": form_events,
        "submit_controls": submit_controls,
        "relevant_functions": relevant_functions,
        "script_snippets": script_snippets,
        "search_request_executed": False,
        "uqq700_target_search_executed": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nFORM EVENTS")
    for x in form_events:
        print(x)
    print("\nSUBMIT CONTROLS")
    for x in submit_controls:
        print(x)
    print("\nRELEVANT FUNCTIONS")
    for x in relevant_functions:
        print(x)
    print("\nSCRIPT SNIPPETS")
    for x in script_snippets:
        print(x)

    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    checks = {
        "detail response qualified": res["state"] == "HTTP_RESPONSE_CAPTURED" and res["http"] == 200 and ok_host,
        "search request disabled": not out["search_request_executed"],
        "UQQ700 target search disabled": not out["uqq700_target_search_executed"],
        "negative evidence disabled": not out["negative_evidence_allowed"],
        "legal absence inference disabled": not out["legal_absence_inference_allowed"],
        "unsafe promotion leakage zero": not any(out[k] for k in ["site_positive_allowed", "site_negative_allowed", "runtime_registration_allowed"]),
        "final resolution unknown": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("\nVALIDATION")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("all_pass:", all(checks.values()))
    if not all(checks.values()):
        raise AssertionError("S150 eminwon search wire contract forensic failed")


if __name__ == "__main__":
    main()
