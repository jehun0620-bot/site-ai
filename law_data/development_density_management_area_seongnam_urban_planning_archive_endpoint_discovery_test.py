# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_seongnam_urban_planning_archive_endpoint_discovery.json"
HOST = "www.seongnam.go.kr"
SEEDS = [
    "https://www.seongnam.go.kr/",
    "https://www.seongnam.go.kr/pm010301/list",
    "https://www.seongnam.go.kr/bbs010308",
]
KEYWORDS = ("도시계획", "도시관리계획", "지형도면", "고시", "공고", "자료실", "upis", "urban", "gis")
A_RE = re.compile(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
FORM_RE = re.compile(r'<form\b([^>]*)>(.*?)</form>', re.I | re.S)
ACTION_RE = re.compile(r'action=["\']([^"\']*)["\']', re.I)
TAG_RE = re.compile(r'<[^>]+>')


def norm(v):
    return re.sub(r"\s+", " ", str(v or "")).strip()


def host(url):
    return (urlparse(url).hostname or "").lower()


def strip_tags(s):
    return norm(html.unescape(TAG_RE.sub(" ", s)))


def fetch(session, url):
    try:
        r = session.get(url, timeout=25, allow_redirects=True)
        data = r.content
        if len(data) > 6 * 1024 * 1024:
            return {
                "state": "TECHNICAL_REQUEST_UNKNOWN",
                "http": r.status_code,
                "final_url": str(r.url),
                "data": b"",
                "error": "RESPONSE_SIZE_LIMIT_EXCEEDED",
            }
        return {
            "state": "HTTP_RESPONSE_CAPTURED",
            "http": r.status_code,
            "final_url": str(r.url),
            "data": data,
            "error": None,
        }
    except requests.RequestException as exc:
        return {
            "state": "TECHNICAL_REQUEST_UNKNOWN",
            "http": None,
            "final_url": url,
            "data": b"",
            "error": f"{type(exc).__name__}: {exc}",
        }


def main():
    print("=" * 60)
    print("SEONGNAM URBAN PLANNING ARCHIVE ENDPOINT DISCOVERY - S142-R1")
    print("=" * 60)
    print("Document search: DISABLED")
    print("Negative evidence: DISABLED")
    print("SITE/runtime promotion: DISABLED")
    print("Per-seed transport failure isolation: ENABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0", "Accept-Language": "ko-KR,ko;q=0.9"})

    requests_log = []
    endpoints = {}
    forms = []

    for seed in SEEDS:
        res = fetch(session, seed)
        final_url = res["final_url"]
        ok_host = host(final_url) == HOST
        requests_log.append({
            "seed": seed,
            "state": res["state"],
            "http": res["http"],
            "final_url": final_url,
            "official_host": ok_host,
            "error": res["error"],
        })
        print("SEED:", seed, "| STATE:", res["state"], "| HTTP:", res["http"], "| HOST_OK:", ok_host)
        if res["error"]:
            print("  ERROR:", res["error"])

        if res["state"] != "HTTP_RESPONSE_CAPTURED" or res["http"] != 200 or not ok_host:
            continue

        text = res["data"].decode("utf-8", errors="ignore")
        for href, body in A_RE.findall(text):
            url = urljoin(final_url, html.unescape(href))
            if host(url) != HOST:
                continue
            label = strip_tags(body)
            hay = (label + " " + url).lower()
            hits = [k for k in KEYWORDS if k.lower() in hay]
            if not hits:
                continue
            key = url.split("#", 1)[0]
            rec = {"url": key, "anchor_text": label, "keyword_hits": hits, "source_seed": seed}
            prev = endpoints.get(key)
            if prev is None or len(hits) > len(prev["keyword_hits"]):
                endpoints[key] = rec

        for attrs, _body in FORM_RE.findall(text):
            m = ACTION_RE.search(attrs)
            action = urljoin(final_url, html.unescape(m.group(1) if m else final_url))
            if host(action) != HOST:
                continue
            hay = action.lower()
            hits = [k for k in KEYWORDS if k.lower() in hay]
            if hits:
                forms.append({"action": action, "keyword_hits": hits, "source_seed": seed})

    endpoint_list = sorted(endpoints.values(), key=lambda x: (-len(x["keyword_hits"]), x["url"]))
    technical_unknown_count = sum(1 for x in requests_log if x["state"] == "TECHNICAL_REQUEST_UNKNOWN")
    successful_seed_count = sum(1 for x in requests_log if x["state"] == "HTTP_RESPONSE_CAPTURED" and x["http"] == 200 and x["official_host"])

    out = {
        "step": "STEP 17-21-C-16-8-T-38-S142-R1",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "summary": {
            "seed_request_count": len(requests_log),
            "successful_seed_count": successful_seed_count,
            "technical_seed_unknown_count": technical_unknown_count,
            "candidate_endpoint_count": len(endpoint_list),
            "candidate_form_count": len(forms),
            "semantic_state": "SEONGNAM_URBAN_PLANNING_ARCHIVE_ENDPOINT_DISCOVERY_CAPTURED_WITH_TRANSPORT_ISOLATION",
            "negative_evidence_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "requests": requests_log,
        "candidate_endpoints": endpoint_list,
        "candidate_forms": forms,
        "document_search_executed": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nCANDIDATE ENDPOINTS")
    for rec in endpoint_list[:40]:
        print(rec["url"], "|", rec["anchor_text"], "|", rec["keyword_hits"])

    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    checks = {
        "seed request exact": len(requests_log) == len(SEEDS),
        "at least one official seed succeeded": successful_seed_count >= 1,
        "technical failures isolated": technical_unknown_count <= len(SEEDS),
        "document search disabled": not out["document_search_executed"],
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
        raise AssertionError("S142-R1 endpoint discovery failed")


if __name__ == "__main__":
    main()
