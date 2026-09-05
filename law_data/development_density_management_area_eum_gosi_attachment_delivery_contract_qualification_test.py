# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "law_data" / "output" / "development_density_management_area_eum_gosi_detail_representation_qualification.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_eum_gosi_attachment_delivery_contract_qualification.json"
UA = "Mozilla/5.0"
MAX_BYTES = 32 * 1024 * 1024


def bounded_get(session: requests.Session, url: str) -> dict:
    try:
        r = session.get(url, timeout=30, stream=True, allow_redirects=True)
        body = bytearray()
        overflow = False
        try:
            for chunk in r.iter_content(65536):
                if not chunk:
                    continue
                if len(body) + len(chunk) > MAX_BYTES:
                    overflow = True
                    break
                body.extend(chunk)
        finally:
            r.close()
        return {
            "state": "HTTP_RESPONSE_CAPTURED" if not overflow else "TECHNICAL_REQUEST_UNKNOWN",
            "http": r.status_code,
            "final_url": str(r.url),
            "content_type": r.headers.get("Content-Type"),
            "content_disposition": r.headers.get("Content-Disposition"),
            "content_length": len(body),
            "signature_hex": bytes(body[:16]).hex(),
            "overflow": overflow,
            "error": "RESPONSE_SIZE_LIMIT_EXCEEDED" if overflow else None,
        }
    except requests.RequestException as exc:
        return {
            "state": "TECHNICAL_REQUEST_UNKNOWN",
            "http": None,
            "final_url": url,
            "content_type": None,
            "content_disposition": None,
            "content_length": 0,
            "signature_hex": "",
            "overflow": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> None:
    print("=" * 60)
    print("EUM GOSI ATTACHMENT DELIVERY CONTRACT QUALIFICATION - S179")
    print("=" * 60)
    print("Sample source: S177")
    print("Attachment text extraction: DISABLED")
    print("OCR: DISABLED")
    print("Negative evidence: DISABLED")
    print("UQQ700 resolution: UNKNOWN")

    src = json.loads(SRC.read_text(encoding="utf-8"))
    samples = src.get("samples", [])
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})

    results = []
    for sample in samples:
        seq = str(sample.get("seq", ""))
        links = sample.get("attachment_like_links") or []
        if not links:
            results.append({"seq": seq, "state": "ATTACHMENT_LINK_NOT_AVAILABLE", "error": None})
            print("SEQ:", seq, "| STATE: ATTACHMENT_LINK_NOT_AVAILABLE")
            continue
        url = links[0].get("url")
        r = bounded_get(session, url)
        official_host = (urlparse(r["final_url"]).hostname or "").endswith("eum.go.kr")
        delivered = r["state"] == "HTTP_RESPONSE_CAPTURED" and r["http"] == 200 and r["content_length"] > 0 and official_host
        state = "ATTACHMENT_DELIVERY_QUALIFIED" if delivered else ("TECHNICAL_REQUEST_UNKNOWN" if r["state"] == "TECHNICAL_REQUEST_UNKNOWN" else "ATTACHMENT_DELIVERY_NOT_RESOLVED")
        row = {"seq": seq, "source_url": url, "official_host": official_host, "state": state, **r}
        results.append(row)
        print("SEQ:", seq, "| STATE:", state, "| HTTP:", r["http"], "| TYPE:", r["content_type"], "| BYTES:", r["content_length"], "| SIG:", r["signature_hex"])

    qualified = sum(1 for x in results if x.get("state") == "ATTACHMENT_DELIVERY_QUALIFIED")
    technical = sum(1 for x in results if x.get("state") == "TECHNICAL_REQUEST_UNKNOWN")
    missing = sum(1 for x in results if x.get("state") == "ATTACHMENT_LINK_NOT_AVAILABLE")

    out = {
        "step": "STEP 17-21-C-16-8-T-75-S179",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "NATIONAL_LAND_USE_PORTAL",
        "results": results,
        "summary": {
            "sample_count": len(results),
            "attachment_delivery_qualified_count": qualified,
            "technical_unknown_count": technical,
            "attachment_link_missing_count": missing,
            "semantic_state": "EUM_ATTACHMENT_DELIVERY_CONTRACT_QUALIFIED" if qualified == len(results) and technical == 0 and missing == 0 else "EUM_ATTACHMENT_DELIVERY_CONTRACT_NOT_YET_QUALIFIED",
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "attachment_text_extraction_executed": False,
        "ocr_allowed": False,
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
        "sample count positive": len(results) > 0,
        "technical unknown zero": technical == 0,
        "attachment links present": missing == 0,
        "all attachment deliveries qualified": qualified == len(results),
        "attachment text extraction disabled": not out["attachment_text_extraction_executed"],
        "OCR disabled": not out["ocr_allowed"],
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
        raise AssertionError("S179 EUM attachment delivery contract qualification failed")


if __name__ == "__main__":
    main()
