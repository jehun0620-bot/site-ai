# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_eum_gosi_external_script_contract_forensic.json"
URL = "https://www.eum.go.kr/web/gs/gv/gvGosiList.jsp"
HOST = "www.eum.go.kr"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 12 * 1024 * 1024
MAX_SCRIPT_BYTES = 4 * 1024 * 1024
MAX_SCRIPT_REQUESTS = 20

SCRIPT_SRC_RE = re.compile(r'<script\b[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']', re.I)
KEYWORDS = ("zonenm_t", "searchWord_T", "zonenm", "mode", "pageNo", "gosino", "gosiStartDt", "gosiEndDt", "form.submit", ".submit()", "gvGosiList.jsp")


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def bounded_get(session: requests.Session, url: str, ceiling: int) -> dict:
    try:
        r = session.get(url, timeout=25, stream=True, allow_redirects=True)
        buf = bytearray()
        overflow = False
        try:
            for chunk in r.iter_content(65536):
                if not chunk:
                    continue
                if len(buf) + len(chunk) > ceiling:
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
        return {"state": "TECHNICAL_REQUEST_UNKNOWN", "http": None, "final_url": url, "body": b"", "overflow": False, "error": f"{type(exc).__name__}: {exc}"}


def decode(raw: bytes) -> tuple[str, str]:
    for enc in ("euc-kr", "utf-8", "cp949"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="ignore"), "utf-8-ignore"


def main() -> None:
    print("=" * 60)
    print("EUM GOSI EXTERNAL SCRIPT CONTRACT FORENSIC - S164")
    print("=" * 60)
    print("Search execution: DISABLED")
    print("UQQ700 target search: DISABLED")
    print("Negative evidence: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    page = bounded_get(session, URL, MAX_BYTES)
    text, enc = decode(page["body"])
    ok = page["state"] == "HTTP_RESPONSE_CAPTURED" and page["http"] == 200 and host(page["final_url"]) == HOST
    print("LIST STATE:", page["state"], "| HTTP:", page["http"], "| ENCODING:", enc)

    scripts = []
    if ok:
        seen = set()
        for raw in SCRIPT_SRC_RE.findall(text):
            u = urljoin(page["final_url"], html.unescape(raw))
            if host(u) != HOST or u in seen:
                continue
            seen.add(u)
            scripts.append(u)

    script_results = []
    relevant = []
    for u in scripts[:MAX_SCRIPT_REQUESTS]:
        res = bounded_get(session, u, MAX_SCRIPT_BYTES)
        body, senc = decode(res["body"])
        hits = [k for k in KEYWORDS if k.lower() in body.lower()]
        rec = {
            "url": u,
            "state": res["state"],
            "http": res["http"],
            "encoding": senc,
            "keyword_hits": hits,
            "error": res["error"],
        }
        script_results.append(rec)
        print("SCRIPT:", u, "| STATE:", rec["state"], "| HTTP:", rec["http"], "| HITS:", hits)
        if hits:
            snippets = []
            low = body.lower()
            for key in hits:
                pos = low.find(key.lower())
                if pos >= 0:
                    s = max(0, pos - 700)
                    e = min(len(body), pos + 1800)
                    snippets.append(re.sub(r"\s+", " ", body[s:e]).strip())
            relevant.append({"url": u, "keyword_hits": hits, "snippets": snippets[:10]})

    technical = sum(1 for r in script_results if r["state"] == "TECHNICAL_REQUEST_UNKNOWN")
    out = {
        "step": "STEP 17-21-C-16-8-T-60-S164",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "NATIONAL_LAND_USE_PORTAL",
        "list_endpoint": URL,
        "script_src_count": len(scripts),
        "script_request_count": len(script_results),
        "script_results": script_results,
        "relevant_scripts": relevant,
        "summary": {
            "relevant_script_count": len(relevant),
            "technical_script_unknown_count": technical,
            "semantic_state": "EUM_GOSI_EXTERNAL_SCRIPT_CONTRACT_FORENSIC_CAPTURED",
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

    print("\nRELEVANT SCRIPTS")
    for x in relevant:
        print(x)
    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    checks = {
        "list response qualified": ok,
        "script request ceiling respected": len(script_results) <= MAX_SCRIPT_REQUESTS,
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
        raise AssertionError("S164 EUM external script forensic failed")


if __name__ == "__main__":
    main()
