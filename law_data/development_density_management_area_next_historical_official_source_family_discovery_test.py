# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_next_historical_official_source_family_discovery.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 8 * 1024 * 1024
TIMEOUT = 25

# Endpoint discovery only. No UQQ700 target query is sent in this stage.
SEEDS = [
    {"family": "NATIONAL_LAND_USE_PORTAL", "url": "https://www.eum.go.kr/"},
    {"family": "GG_URBAN_PLANNING_PORTAL", "url": "https://gris.gg.go.kr/"},
    {"family": "NATIONAL_LAW_NOTICE_AUXILIARY", "url": "https://www.law.go.kr/"},
]

KEYWORDS = (
    "도시계획", "도시관리계획", "고시", "공고", "지형도면", "토지이용", "결정", "변경",
    "notice", "gosi", "gonggo", "urban", "plan", "archive", "history", "bbs", "board",
)

A_RE = re.compile(r'<a\b[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
FORM_RE = re.compile(r'<form\b([^>]*)>(.*?)</form>', re.I | re.S)
ACTION_RE = re.compile(r'action\s*=\s*["\']([^"\']*)["\']', re.I)
METHOD_RE = re.compile(r'method\s*=\s*["\']([^"\']*)["\']', re.I)
TAG_RE = re.compile(r'<[^>]+>')


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def official_host(h: str) -> bool:
    return h.endswith("go.kr") or h.endswith("eum.go.kr") or h.endswith("gg.go.kr")


def strip_tags(v: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", v or ""))).strip()


def bounded_get(session: requests.Session, url: str) -> dict:
    try:
        r = session.get(url, timeout=TIMEOUT, stream=True, allow_redirects=True)
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


def decode(raw: bytes) -> tuple[str, str]:
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="ignore"), "utf-8-ignore"


def main() -> None:
    print("=" * 60)
    print("NEXT HISTORICAL OFFICIAL SOURCE FAMILY DISCOVERY - S158")
    print("=" * 60)
    print("UQQ700 target search: DISABLED")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})

    seed_results = []
    endpoints = {}
    forms = []

    for seed in SEEDS:
        res = bounded_get(session, seed["url"])
        text, encoding = decode(res["body"])
        final_host = host(res["final_url"])
        rec = {
            "family": seed["family"],
            "seed_url": seed["url"],
            "state": res["state"],
            "http": res["http"],
            "final_url": res["final_url"],
            "official_host": official_host(final_host),
            "encoding": encoding,
            "overflow": res["overflow"],
            "error": res["error"],
        }
        seed_results.append(rec)
        print("SEED:", seed["family"], "| STATE:", rec["state"], "| HTTP:", rec["http"], "| FINAL:", rec["final_url"])

        if res["state"] != "HTTP_RESPONSE_CAPTURED" or res["http"] != 200 or not rec["official_host"]:
            continue

        for href, body in A_RE.findall(text):
            url = urljoin(res["final_url"], html.unescape(href))
            h = host(url)
            if not official_host(h):
                continue
            label = strip_tags(body)
            hay = (label + " " + url).lower()
            hits = [k for k in KEYWORDS if k.lower() in hay]
            if not hits:
                continue
            endpoints[url] = {
                "family": seed["family"],
                "url": url,
                "anchor_text": label,
                "keyword_hits": hits,
            }

        for attrs, body in FORM_RE.findall(text):
            am = ACTION_RE.search(attrs)
            mm = METHOD_RE.search(attrs)
            action = urljoin(res["final_url"], html.unescape(am.group(1) if am else res["final_url"]))
            if not official_host(host(action)):
                continue
            plain = strip_tags(body)
            hay = (plain + " " + action).lower()
            hits = [k for k in KEYWORDS if k.lower() in hay]
            if not hits:
                continue
            forms.append({
                "family": seed["family"],
                "action": action,
                "method": (mm.group(1).upper() if mm else "GET"),
                "keyword_hits": hits,
                "form_text": plain[:1000],
            })

    endpoint_list = sorted(endpoints.values(), key=lambda x: (x["family"], -len(x["keyword_hits"]), x["url"]))
    successful = sum(1 for r in seed_results if r["state"] == "HTTP_RESPONSE_CAPTURED" and r["http"] == 200 and r["official_host"])
    technical = sum(1 for r in seed_results if r["state"] == "TECHNICAL_REQUEST_UNKNOWN")

    out = {
        "step": "STEP 17-21-C-16-8-T-54-S158",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "purpose": "DISCOVER_NEXT_HISTORICAL_OFFICIAL_SOURCE_FAMILY_ENDPOINTS",
        "seed_results": seed_results,
        "candidate_endpoints": endpoint_list,
        "candidate_forms": forms,
        "summary": {
            "seed_count": len(SEEDS),
            "successful_seed_count": successful,
            "technical_seed_unknown_count": technical,
            "candidate_endpoint_count": len(endpoint_list),
            "candidate_form_count": len(forms),
            "semantic_state": "NEXT_HISTORICAL_OFFICIAL_SOURCE_FAMILY_ENDPOINTS_DISCOVERED" if endpoint_list or forms else "NEXT_HISTORICAL_OFFICIAL_SOURCE_FAMILY_DISCOVERY_NO_ENDPOINT_YET",
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "uqq700_target_search_executed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nCANDIDATE ENDPOINTS")
    for x in endpoint_list[:100]:
        print(x)
    print("\nCANDIDATE FORMS")
    for x in forms[:50]:
        print(x)
    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    checks = {
        "at least one official seed reachable": successful >= 1,
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
        raise AssertionError("S158 next historical official source family discovery failed")


if __name__ == "__main__":
    main()
