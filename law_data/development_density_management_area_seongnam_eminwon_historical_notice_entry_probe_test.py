# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_seongnam_eminwon_historical_notice_entry_probe.json"
HOST = "eminwon.seongnam.go.kr"
SEEDS = [
    "https://eminwon.seongnam.go.kr/",
    "http://eminwon.seongnam.go.kr/",
]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 4 * 1024 * 1024


def host(url):
    return (urlparse(url).hostname or "").lower()


def bounded_get(session, url):
    try:
        r = session.get(url, timeout=20, stream=True, allow_redirects=True)
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
            "content_type": r.headers.get("Content-Type", ""),
            "bytes": len(buf),
            "overflow": overflow,
            "error": "RESPONSE_SIZE_LIMIT_EXCEEDED" if overflow else None,
        }
    except requests.RequestException as exc:
        return {
            "state": "TECHNICAL_REQUEST_UNKNOWN",
            "http": None,
            "final_url": url,
            "content_type": "",
            "bytes": 0,
            "overflow": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def main():
    print("=" * 60)
    print("SEONGNAM EMINWON HISTORICAL NOTICE ENTRY PROBE - S144")
    print("=" * 60)
    print("Target-term search: DISABLED")
    print("Negative evidence: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})

    results = []
    for seed in SEEDS:
        res = bounded_get(session, seed)
        res["seed"] = seed
        res["official_host"] = host(res["final_url"]) == HOST
        results.append(res)
        print("SEED:", seed, "| STATE:", res["state"], "| HTTP:", res["http"], "| FINAL:", res["final_url"])
        if res["error"]:
            print("  ERROR:", res["error"])

    success = [r for r in results if r["state"] == "HTTP_RESPONSE_CAPTURED" and r["http"] is not None and r["official_host"]]
    transport_unknown = [r for r in results if r["state"] == "TECHNICAL_REQUEST_UNKNOWN"]

    out = {
        "step": "STEP 17-21-C-16-8-T-40-S144",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "SEONGNAM_EMINWON_HISTORICAL_NOTICE",
        "summary": {
            "seed_request_count": len(results),
            "reachable_seed_count": len(success),
            "technical_seed_unknown_count": len(transport_unknown),
            "semantic_state": "SEONGNAM_EMINWON_HISTORICAL_NOTICE_ENTRY_PROBED",
            "negative_evidence_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "results": results,
        "target_term_search_executed": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    checks = {
        "seed request exact": len(results) == len(SEEDS),
        "official destination retained when reachable": all(r["official_host"] for r in success),
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
        raise AssertionError("S144 eminwon entry probe failed")


if __name__ == "__main__":
    main()
