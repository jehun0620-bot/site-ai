# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_eum_gosi_list_search_contract_forensic.json"
URL = "https://www.eum.go.kr/web/gs/gv/gvGosiList.jsp"
HOST = "www.eum.go.kr"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 12 * 1024 * 1024

FORM_RE = re.compile(r'<form\b([^>]*)>(.*?)</form>', re.I | re.S)
ACTION_RE = re.compile(r'action\s*=\s*["\']([^"\']*)["\']', re.I)
METHOD_RE = re.compile(r'method\s*=\s*["\']([^"\']*)["\']', re.I)
FIELD_RE = re.compile(r'<(?:input|select|textarea)\b([^>]*)>', re.I | re.S)
ATTR_RE = re.compile(r'([:\w-]+)\s*=\s*(["\'])(.*?)\2', re.I | re.S)
SCRIPT_RE = re.compile(r'<script\b[^>]*>(.*?)</script>', re.I | re.S)
FUNC_RE = re.compile(r'function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{(.*?)\}', re.I | re.S)
DETAIL_RE = re.compile(r'gvGosiDet\.jsp[^"\']*seq\s*=\s*([^&"\']+)', re.I)
KEYWORDS = ("zonenm", "gosino", "gosichrg", "chrgorg", "startdt", "enddt", "prj_nm", "pageNo", "listSize", "gihyung_yn", "silsi_yn", "geul_yn", "selSggCd", "select2", "select_3", "검색", "search", "gosi")


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def attrs_dict(raw: str) -> dict[str, str]:
    return {m.group(1).lower(): html.unescape(m.group(3)) for m in ATTR_RE.finditer(raw or "")}


def bounded_get(session: requests.Session) -> dict:
    try:
        r = session.get(URL, timeout=25, stream=True, allow_redirects=True)
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
        return {"state": "TECHNICAL_REQUEST_UNKNOWN", "http": None, "final_url": URL, "body": b"", "overflow": False, "error": f"{type(exc).__name__}: {exc}"}


def decode(raw: bytes) -> tuple[str, str]:
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            text = raw.decode(enc)
            if "고시정보" in text or "고시제목" in text:
                return text, enc
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="ignore"), "utf-8-ignore"


def main() -> None:
    print("=" * 60)
    print("EUM GOSI LIST/SEARCH CONTRACT FORENSIC - S161")
    print("=" * 60)
    print("Search execution: DISABLED")
    print("UQQ700 target search: DISABLED")
    print("Negative evidence: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    res = bounded_get(session)
    text, encoding = decode(res["body"])
    ok_host = host(res["final_url"]) == HOST
    print("LIST STATE:", res["state"], "| HTTP:", res["http"], "| HOST_OK:", ok_host, "| ENCODING:", encoding)

    forms = []
    relevant_functions = []
    detail_hints = []

    if res["state"] == "HTTP_RESPONSE_CAPTURED" and res["http"] == 200 and ok_host:
        for attrs, body in FORM_RE.findall(text):
            ad = attrs_dict(attrs)
            am = ACTION_RE.search(attrs)
            mm = METHOD_RE.search(attrs)
            action = urljoin(res["final_url"], html.unescape(am.group(1) if am else res["final_url"]))
            fields = []
            for raw in FIELD_RE.findall(body):
                d = attrs_dict(raw)
                if "name" not in d:
                    continue
                fields.append({k: d.get(k) for k in ("name", "value", "type", "id") if d.get(k) is not None})
            hay = (action + " " + " ".join(str(x.get("name", "")) for x in fields)).lower()
            hits = [k for k in KEYWORDS if k.lower() in hay]
            if hits:
                forms.append({
                    "action": action,
                    "method": (mm.group(1).upper() if mm else "GET"),
                    "onsubmit": ad.get("onsubmit"),
                    "fields": fields,
                    "keyword_hits": hits,
                })

        for sm in SCRIPT_RE.findall(text):
            for fn, args, body in FUNC_RE.findall(sm):
                hay = (fn + " " + args + " " + body).lower()
                if any(k.lower() in hay for k in KEYWORDS):
                    relevant_functions.append({
                        "name": fn,
                        "args": args.strip(),
                        "body": re.sub(r"\s+", " ", body).strip()[:3000],
                    })
        detail_hints = sorted(set(DETAIL_RE.findall(text)))[:100]

    out = {
        "step": "STEP 17-21-C-16-8-T-57-S161",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "NATIONAL_LAND_USE_PORTAL",
        "list_endpoint": URL,
        "request": {k: v for k, v in res.items() if k != "body"},
        "encoding": encoding,
        "forms": forms,
        "relevant_functions": relevant_functions,
        "detail_identity_hints": detail_hints,
        "summary": {
            "form_count": len(forms),
            "relevant_function_count": len(relevant_functions),
            "detail_identity_hint_count": len(detail_hints),
            "transport_unknown_count": 1 if res["state"] == "TECHNICAL_REQUEST_UNKNOWN" else 0,
            "semantic_state": "EUM_GOSI_LIST_SEARCH_CONTRACT_FORENSIC_CAPTURED",
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "search_request_executed": False,
        "uqq700_target_search_executed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nFORMS")
    for x in forms:
        print(x)
    print("\nRELEVANT FUNCTIONS")
    for x in relevant_functions:
        print(x)
    print("\nDETAIL IDENTITY HINTS")
    for x in detail_hints:
        print(x)
    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    checks = {
        "list response qualified": res["state"] == "HTTP_RESPONSE_CAPTURED" and res["http"] == 200 and ok_host,
        "search request disabled": not out["search_request_executed"],
        "UQQ700 target search disabled": not out["uqq700_target_search_executed"],
        "negative evidence disabled": not out["summary"]["negative_evidence_allowed"],
        "legal absence inference disabled": not out["summary"]["legal_absence_inference_allowed"],
        "unsafe promotion leakage zero": not any(out[k] for k in ["site_positive_allowed", "site_negative_allowed", "runtime_registration_allowed"]),
        "final resolution unknown": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("\nVALIDATION")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("all_pass:", all(checks.values()))
    if not all(checks.values()):
        raise AssertionError("S161 EUM gosi list/search contract forensic failed")


if __name__ == "__main__":
    main()
