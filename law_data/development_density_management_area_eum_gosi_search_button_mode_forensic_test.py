# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_eum_gosi_search_button_mode_forensic.json"
LIST_URL = "https://www.eum.go.kr/web/gs/gv/gvGosiList.jsp"
JS_URL = "https://www.eum.go.kr/web/js/gs/gv/gvGosiList.js"
HOST = "www.eum.go.kr"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 8 * 1024 * 1024

PATTERNS = [
    r"mode",
    r"zonenm_t",
    r"chrgorg_t",
    r"frmGosi",
    r"\.submit\s*\(",
    r"\.attr\s*\(\s*[\"']action[\"']",
    r"\.on\s*\(\s*[\"']click[\"']",
    r"\.click\s*\(",
    r"search",
    r"검색",
    r"btn",
    r"pageNo",
]


def bounded_get(session: requests.Session, url: str) -> dict:
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
            "error": "RESPONSE_SIZE_LIMIT_EXCEEDED" if overflow else None,
        }
    except requests.RequestException as exc:
        return {"state": "TECHNICAL_REQUEST_UNKNOWN", "http": None, "final_url": url, "body": b"", "error": f"{type(exc).__name__}: {exc}"}


def decode(raw: bytes) -> tuple[str, str]:
    for enc in ("euc-kr", "utf-8", "cp949"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="ignore"), "utf-8-ignore"


def snippets(text: str, pattern: str, before: int = 900, after: int = 2200) -> list[str]:
    out = []
    for m in re.finditer(pattern, text, re.I):
        s = max(0, m.start() - before)
        e = min(len(text), m.end() + after)
        frag = re.sub(r"\s+", " ", text[s:e]).strip()
        if frag not in out:
            out.append(frag)
        if len(out) >= 12:
            break
    return out


def main() -> None:
    print("=" * 60)
    print("EUM GOSI SEARCH BUTTON/MODE FORENSIC - S170")
    print("=" * 60)
    print("Search execution: DISABLED")
    print("UQQ700 target search: DISABLED")
    print("Negative evidence: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})

    list_res = bounded_get(s, LIST_URL)
    list_text, list_enc = decode(list_res["body"])
    js_res = bounded_get(s, JS_URL)
    js_text, js_enc = decode(js_res["body"])

    sources = [("LIST_HTML", list_text), ("GV_GOSI_LIST_JS", js_text)]
    findings = []
    for source_name, text in sources:
        for pat in PATTERNS:
            frags = snippets(text, pat)
            if frags:
                findings.append({"source": source_name, "pattern": pat, "snippets": frags})

    # Explicitly capture controls/buttons near frmGosi from HTML.
    form_match = re.search(r'(<form\b[^>]*(?:id|name)=["\']frmGosi["\'][\s\S]*?</form>)', list_text, re.I)
    form_html = form_match.group(1) if form_match else ""
    buttons = []
    if form_html:
        for m in re.finditer(r'<(?:button|input|a)\b[^>]*(?:type=["\']?(?:submit|button|image)["\']?|class=["\'][^"\']*(?:btn|search|sch)[^"\']*["\']|onclick=["\'][^"\']+["\'])[^>]*>', form_html, re.I):
            tag = re.sub(r"\s+", " ", m.group(0)).strip()
            if tag not in buttons:
                buttons.append(tag)
            if len(buttons) >= 30:
                break

    # Extract assignment-like evidence for hidden fields / action / mode.
    assignment_patterns = [
        r'(?:find\([^\n]{0,120}name\s*=\s*mode[^\n]{0,250})',
        r'(?:\[name\s*=\s*["\']?mode["\']?\][^\n]{0,250})',
        r'(?:mode\s*[:=]\s*["\'][^"\']*["\'])',
        r'(?:zonenm_t[^\n]{0,300})',
        r'(?:chrgorg_t[^\n]{0,300})',
        r'(?:frmGosi[^\n]{0,500}(?:submit|action|mode)[^\n]{0,300})',
    ]
    assignments = []
    combined = list_text + "\n" + js_text
    for pat in assignment_patterns:
        for m in re.finditer(pat, combined, re.I):
            frag = re.sub(r"\s+", " ", m.group(0)).strip()
            if frag not in assignments:
                assignments.append(frag)
            if len(assignments) >= 50:
                break

    out = {
        "step": "STEP 17-21-C-16-8-T-66-S170",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "NATIONAL_LAND_USE_PORTAL",
        "list_endpoint": LIST_URL,
        "js_endpoint": JS_URL,
        "list_state": list_res["state"],
        "list_http": list_res["http"],
        "list_encoding": list_enc,
        "js_state": js_res["state"],
        "js_http": js_res["http"],
        "js_encoding": js_enc,
        "button_or_control_tags": buttons,
        "assignment_evidence": assignments,
        "findings": findings,
        "summary": {
            "button_or_control_tag_count": len(buttons),
            "assignment_evidence_count": len(assignments),
            "finding_group_count": len(findings),
            "technical_unknown_count": int(list_res["state"] == "TECHNICAL_REQUEST_UNKNOWN") + int(js_res["state"] == "TECHNICAL_REQUEST_UNKNOWN"),
            "semantic_state": "EUM_GOSI_SEARCH_BUTTON_MODE_FORENSIC_CAPTURED",
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

    print("\nBUTTON/CONTROL TAGS")
    for x in buttons:
        print(x)
    print("\nASSIGNMENT EVIDENCE")
    for x in assignments:
        print(x)
    print("\nFINDINGS")
    for group in findings:
        print("SOURCE:", group["source"], "| PATTERN:", group["pattern"])
        for frag in group["snippets"][:5]:
            print(" ", frag)
    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    checks = {
        "list response qualified": list_res["state"] == "HTTP_RESPONSE_CAPTURED" and list_res["http"] == 200,
        "target js response qualified": js_res["state"] == "HTTP_RESPONSE_CAPTURED" and js_res["http"] == 200,
        "technical unknown zero": out["summary"]["technical_unknown_count"] == 0,
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
        raise AssertionError("S170 EUM search button/mode forensic failed")


if __name__ == "__main__":
    main()
