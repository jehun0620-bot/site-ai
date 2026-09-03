# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_seongnam_urban_planning_board_contract_probe.json"
LIST_URL = "https://www.seongnam.go.kr/city/1000541/30228/bbsList.do"
HOST = "www.seongnam.go.kr"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 8 * 1024 * 1024

VIEW_RE = re.compile(r"bbsView\.do\?idx=(\d+)", re.I)
FORM_RE = re.compile(r"<form\b([^>]*)>(.*?)</form>", re.I | re.S)
ACTION_RE = re.compile(r"action\s*=\s*['\"]([^'\"]*)['\"]", re.I)
METHOD_RE = re.compile(r"method\s*=\s*['\"]([^'\"]*)['\"]", re.I)
FIELD_RE = re.compile(r"<(?:input|select|textarea)\b([^>]*)>", re.I | re.S)
NAME_RE = re.compile(r"name\s*=\s*['\"]([^'\"]+)['\"]", re.I)


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
    print("SEONGNAM URBAN PLANNING BOARD CONTRACT PROBE - S143")
    print("=" * 60)
    print("Target-term search: DISABLED")
    print("Negative evidence: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    res = bounded_get(session, LIST_URL)
    print("LIST STATE:", res["state"], "| HTTP:", res["http"], "| ERROR:", res["error"])

    identities = []
    forms = []
    if res["state"] == "HTTP_RESPONSE_CAPTURED" and res["http"] == 200 and host(res["final_url"]) == HOST:
        text = res["body"].decode("utf-8", errors="ignore")
        identities = sorted(set(VIEW_RE.findall(text)), key=int)
        for attrs, body in FORM_RE.findall(text):
            am = ACTION_RE.search(attrs)
            mm = METHOD_RE.search(attrs)
            action = urljoin(res["final_url"], am.group(1) if am else res["final_url"])
            if host(action) != HOST:
                continue
            fields = []
            for fa in FIELD_RE.findall(body):
                nm = NAME_RE.search(fa)
                if nm:
                    fields.append(nm.group(1))
            forms.append({"action": action, "method": (mm.group(1).upper() if mm else "GET"), "field_names": sorted(set(fields))})

    out = {
        "step": "STEP 17-21-C-16-8-T-39-S143",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "SEONGNAM_URBAN_PLANNING_BOARD",
        "list_url": LIST_URL,
        "request": {k: v for k, v in res.items() if k != "body"},
        "summary": {
            "detail_identity_count": len(identities),
            "form_count": len(forms),
            "transport_unknown_count": 1 if res["state"] == "TECHNICAL_REQUEST_UNKNOWN" else 0,
            "semantic_state": "SEONGNAM_URBAN_PLANNING_BOARD_CONTRACT_PROBED",
            "negative_evidence_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "detail_identities": identities,
        "forms": forms,
        "target_term_search_executed": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("DETAIL_IDENTITIES:", identities[:20])
    print("FORMS:")
    for f in forms:
        print(f)
    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    checks = {
        "official target host retained": host(res["final_url"]) == HOST,
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
        raise AssertionError("S143 contract probe failed")


if __name__ == "__main__":
    main()
