# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_seongnam_eminwon_notice_list_search_contract_probe.json"
HOST = "eminwon.seongnam.go.kr"
DETAIL_URL = "http://eminwon.seongnam.go.kr/emwp/gov/mogaha/ntis/web/ofr/action/OfrAction.do"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 8 * 1024 * 1024

SAMPLE_PARAMS = {
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
ACTION_RE = re.compile(r'action\s*=\s*["\']([^"\']*)["\']', re.I)
METHOD_RE = re.compile(r'method\s*=\s*["\']([^"\']*)["\']', re.I)
FIELD_RE = re.compile(r'<(?:input|select|textarea)\b([^>]*)>', re.I | re.S)
NAME_RE = re.compile(r'name\s*=\s*["\']([^"\']+)["\']', re.I)
VALUE_RE = re.compile(r'value\s*=\s*["\']([^"\']*)["\']', re.I)
A_RE = re.compile(r'<a\b[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
JS_URL_RE = re.compile(r'["\']([^"\']*(?:OfrAction\.do|selectOfrNotAncmt|not_ancmt_mgt_no)[^"\']*)["\']', re.I)
TAG_RE = re.compile(r'<[^>]+>')

SEARCH_HINTS = ("search", "검색", "key", "subject", "title", "not_ancmt", "ofr", "page", "list")


def host(url):
    return (urlparse(url).hostname or "").lower()


def strip_tags(v):
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", str(v or "")))).strip()


def bounded_get(session, url, params):
    try:
        r = session.get(url, params=params, timeout=25, stream=True, allow_redirects=True)
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
            "final_url": url,
            "body": b"",
            "overflow": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def decode_body(raw):
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            text = raw.decode(enc)
            if "고시" in text or "공고" in text:
                return text, enc
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="ignore"), "utf-8-ignore"


def main():
    print("=" * 60)
    print("SEONGNAM EMINWON NOTICE LIST/SEARCH CONTRACT PROBE - S148")
    print("=" * 60)
    print("Target UQQ700 search: DISABLED")
    print("Negative evidence: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    res = bounded_get(session, DETAIL_URL, SAMPLE_PARAMS)
    ok_host = host(res["final_url"]) == HOST
    text, encoding = decode_body(res["body"])
    print("DETAIL STATE:", res["state"], "| HTTP:", res["http"], "| HOST_OK:", ok_host, "| ENCODING:", encoding)

    forms = []
    links = []
    js_refs = []
    if res["state"] == "HTTP_RESPONSE_CAPTURED" and res["http"] == 200 and ok_host:
        for attrs, body in FORM_RE.findall(text):
            am = ACTION_RE.search(attrs)
            mm = METHOD_RE.search(attrs)
            action = urljoin(res["final_url"], html.unescape(am.group(1) if am else res["final_url"]))
            if host(action) != HOST:
                continue
            fields = []
            for raw_attrs in FIELD_RE.findall(body):
                nm = NAME_RE.search(raw_attrs)
                if not nm:
                    continue
                vm = VALUE_RE.search(raw_attrs)
                fields.append({"name": nm.group(1), "value": vm.group(1) if vm else None})
            hay = (strip_tags(body) + " " + action + " " + " ".join(f["name"] for f in fields)).lower()
            hints = [h for h in SEARCH_HINTS if h.lower() in hay]
            forms.append({
                "action": action,
                "method": (mm.group(1).upper() if mm else "GET"),
                "fields": fields,
                "search_hints": hints,
            })

        dedup = {}
        for href, body in A_RE.findall(text):
            url = urljoin(res["final_url"], html.unescape(href))
            if host(url) != HOST:
                continue
            label = strip_tags(body)
            hay = (label + " " + url).lower()
            hints = [h for h in SEARCH_HINTS if h.lower() in hay]
            if not hints:
                continue
            dedup[url] = {"url": url, "anchor_text": label, "search_hints": hints}
        links = sorted(dedup.values(), key=lambda x: (-len(x["search_hints"]), x["url"]))

        js_refs = sorted(set(html.unescape(x) for x in JS_URL_RE.findall(text)))

    out = {
        "step": "STEP 17-21-C-16-8-T-44-S148",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "SEONGNAM_EMINWON_HISTORICAL_NOTICE",
        "detail_endpoint": DETAIL_URL,
        "request": {k: v for k, v in res.items() if k != "body"},
        "encoding": encoding,
        "summary": {
            "form_count": len(forms),
            "candidate_link_count": len(links),
            "js_contract_reference_count": len(js_refs),
            "transport_unknown_count": 1 if res["state"] == "TECHNICAL_REQUEST_UNKNOWN" else 0,
            "semantic_state": "SEONGNAM_EMINWON_NOTICE_LIST_SEARCH_CONTRACT_FORENSIC_CAPTURED",
            "negative_evidence_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "forms": forms,
        "candidate_links": links,
        "js_contract_references": js_refs,
        "target_term_search_executed": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nFORMS")
    for rec in forms:
        print(rec)
    print("\nCANDIDATE LINKS")
    for rec in links[:50]:
        print(rec)
    print("\nJS CONTRACT REFERENCES")
    for ref in js_refs[:100]:
        print(ref)

    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    checks = {
        "detail response qualified": res["state"] == "HTTP_RESPONSE_CAPTURED" and res["http"] == 200 and ok_host,
        "target UQQ700 search disabled": not out["target_term_search_executed"],
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
        raise AssertionError("S148 eminwon list/search contract probe failed")


if __name__ == "__main__":
    main()
