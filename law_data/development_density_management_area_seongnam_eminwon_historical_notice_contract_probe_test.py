# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_seongnam_eminwon_historical_notice_contract_probe.json"
ENTRY_URL = "http://eminwon.seongnam.go.kr/emwp/emwpIndex.html"
HOST = "eminwon.seongnam.go.kr"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 6 * 1024 * 1024

A_RE = re.compile(r'<a\b[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
FORM_RE = re.compile(r'<form\b([^>]*)>(.*?)</form>', re.I | re.S)
ACTION_RE = re.compile(r'action\s*=\s*["\']([^"\']*)["\']', re.I)
METHOD_RE = re.compile(r'method\s*=\s*["\']([^"\']*)["\']', re.I)
FIELD_RE = re.compile(r'<(?:input|select|textarea)\b([^>]*)>', re.I | re.S)
NAME_RE = re.compile(r'name\s*=\s*["\']([^"\']+)["\']', re.I)
TAG_RE = re.compile(r'<[^>]+>')
KEYWORDS = ("고시", "공고", "입법", "예고", "notice", "announce", "gosi", "gonggo", "singo", "eminwon", "emwp")


def norm(v):
    return re.sub(r"\s+", " ", str(v or "")).strip()


def strip_tags(v):
    return norm(html.unescape(TAG_RE.sub(" ", str(v or ""))))


def host(url):
    return (urlparse(url).hostname or "").lower()


def bounded_get(session, url):
    try:
        r = session.get(url, timeout=25, stream=True, allow_redirects=True)
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


def main():
    print("=" * 60)
    print("SEONGNAM EMINWON HISTORICAL NOTICE CONTRACT PROBE - S145")
    print("=" * 60)
    print("Target-term search: DISABLED")
    print("Negative evidence: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    res = bounded_get(session, ENTRY_URL)
    ok_host = host(res["final_url"]) == HOST
    print("ENTRY STATE:", res["state"], "| HTTP:", res["http"], "| HOST_OK:", ok_host)
    if res["error"]:
        print("ERROR:", res["error"])

    links = []
    forms = []
    if res["state"] == "HTTP_RESPONSE_CAPTURED" and res["http"] == 200 and ok_host:
        text = res["body"].decode("utf-8", errors="ignore")
        dedup = {}
        for href, body in A_RE.findall(text):
            url = urljoin(res["final_url"], html.unescape(href))
            if host(url) != HOST:
                continue
            label = strip_tags(body)
            hay = (label + " " + url).lower()
            hits = [k for k in KEYWORDS if k.lower() in hay]
            if not hits:
                continue
            key = url.split("#", 1)[0]
            rec = {"url": key, "anchor_text": label, "keyword_hits": hits}
            prev = dedup.get(key)
            if prev is None or len(hits) > len(prev["keyword_hits"]):
                dedup[key] = rec
        links = sorted(dedup.values(), key=lambda x: (-len(x["keyword_hits"]), x["url"]))

        for attrs, body in FORM_RE.findall(text):
            am = ACTION_RE.search(attrs)
            mm = METHOD_RE.search(attrs)
            action = urljoin(res["final_url"], html.unescape(am.group(1) if am else res["final_url"]))
            if host(action) != HOST:
                continue
            fields = []
            for raw_attrs in FIELD_RE.findall(body):
                nm = NAME_RE.search(raw_attrs)
                if nm:
                    fields.append(nm.group(1))
            body_text = strip_tags(body)
            hay = (body_text + " " + action).lower()
            hits = [k for k in KEYWORDS if k.lower() in hay]
            forms.append({
                "action": action,
                "method": (mm.group(1).upper() if mm else "GET"),
                "field_names": sorted(set(fields)),
                "keyword_hits": hits,
            })

    out = {
        "step": "STEP 17-21-C-16-8-T-41-S145",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "SEONGNAM_EMINWON_HISTORICAL_NOTICE",
        "entry_url": ENTRY_URL,
        "request": {k: v for k, v in res.items() if k != "body"},
        "summary": {
            "candidate_link_count": len(links),
            "form_count": len(forms),
            "transport_unknown_count": 1 if res["state"] == "TECHNICAL_REQUEST_UNKNOWN" else 0,
            "semantic_state": "SEONGNAM_EMINWON_HISTORICAL_NOTICE_CONTRACT_PROBED",
            "negative_evidence_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "candidate_links": links,
        "forms": forms,
        "target_term_search_executed": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nCANDIDATE LINKS")
    for rec in links[:50]:
        print(rec["url"], "|", rec["anchor_text"], "|", rec["keyword_hits"])
    print("\nFORMS")
    for rec in forms:
        print(rec)

    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    checks = {
        "entry host official": ok_host,
        "target search disabled": not out["target_term_search_executed"],
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
        raise AssertionError("S145 eminwon contract probe failed")


if __name__ == "__main__":
    main()
