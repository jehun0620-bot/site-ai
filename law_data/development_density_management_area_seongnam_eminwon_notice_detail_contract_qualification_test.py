# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlencode, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_seongnam_eminwon_notice_detail_contract_qualification.json"
BASE_URL = "http://eminwon.seongnam.go.kr/emwp/gov/mogaha/ntis/web/ofr/action/OfrAction.do"
HOST = "eminwon.seongnam.go.kr"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 8 * 1024 * 1024

SAMPLES = [
    {"not_ancmt_mgt_no": "66727", "expected_notice": "2018-168", "expected_term": "가마절"},
    {"not_ancmt_mgt_no": "83899", "expected_notice": "2020-170", "expected_term": "방재시설"},
]

BASE_PARAMS = {
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
    "ofr_pageSize": "10",
    "subCheck": "Y",
    "title": "고시공고",
}


def host(url):
    return (urlparse(url).hostname or "").lower()


def bounded_get(session, params):
    try:
        r = session.get(BASE_URL, params=params, timeout=25, stream=True, allow_redirects=True)
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
            "final_url": BASE_URL + "?" + urlencode(params),
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
    print("SEONGNAM EMINWON NOTICE DETAIL CONTRACT QUALIFICATION - S147")
    print("=" * 60)
    print("Target UQQ700 search: DISABLED")
    print("Negative evidence: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    results = []

    for sample in SAMPLES:
        params = dict(BASE_PARAMS)
        params["not_ancmt_mgt_no"] = sample["not_ancmt_mgt_no"]
        res = bounded_get(session, params)
        text, encoding = decode_body(res["body"])
        notice_ok = bool(re.search(r"성남시\s*고시\s*제?\s*" + re.escape(sample["expected_notice"].split("-")[0]) + r"\s*[-－]\s*" + re.escape(sample["expected_notice"].split("-")[1]) + r"\s*호?", text))
        term_ok = sample["expected_term"] in text
        detail_ok = res["state"] == "HTTP_RESPONSE_CAPTURED" and res["http"] == 200 and host(res["final_url"]) == HOST and notice_ok and term_ok
        row = {
            "not_ancmt_mgt_no": sample["not_ancmt_mgt_no"],
            "expected_notice": sample["expected_notice"],
            "expected_term": sample["expected_term"],
            "state": "DETAIL_CONTRACT_QUALIFIED" if detail_ok else ("TECHNICAL_REQUEST_UNKNOWN" if res["state"] == "TECHNICAL_REQUEST_UNKNOWN" else "DETAIL_IDENTITY_MISMATCH"),
            "http": res["http"],
            "final_url": res["final_url"],
            "official_host": host(res["final_url"]) == HOST,
            "encoding": encoding,
            "notice_identity_match": notice_ok,
            "expected_term_match": term_ok,
            "overflow": res["overflow"],
            "error": res["error"],
        }
        results.append(row)
        print("MGT_NO:", row["not_ancmt_mgt_no"], "| STATE:", row["state"], "| HTTP:", row["http"], "| NOTICE_OK:", notice_ok, "| TERM_OK:", term_ok)
        if row["error"]:
            print("  ERROR:", row["error"])

    qualified = sum(1 for r in results if r["state"] == "DETAIL_CONTRACT_QUALIFIED")
    technical = sum(1 for r in results if r["state"] == "TECHNICAL_REQUEST_UNKNOWN")
    mismatch = sum(1 for r in results if r["state"] == "DETAIL_IDENTITY_MISMATCH")

    out = {
        "step": "STEP 17-21-C-16-8-T-43-S147",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "SEONGNAM_EMINWON_HISTORICAL_NOTICE",
        "detail_endpoint": BASE_URL,
        "identity_parameter": "not_ancmt_mgt_no",
        "method_parameter": "selectOfrNotAncmt",
        "summary": {
            "sample_count": len(results),
            "detail_contract_qualified_count": qualified,
            "technical_unknown_count": technical,
            "identity_mismatch_count": mismatch,
            "semantic_state": "SEONGNAM_EMINWON_NOTICE_DETAIL_CONTRACT_QUALIFIED" if qualified == len(SAMPLES) else "SEONGNAM_EMINWON_NOTICE_DETAIL_CONTRACT_PARTIALLY_QUALIFIED",
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
        "sample request exact": len(results) == len(SAMPLES),
        "all detail contracts qualified": qualified == len(SAMPLES),
        "technical unknown zero": technical == 0,
        "identity mismatch zero": mismatch == 0,
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
        raise AssertionError("S147 eminwon detail contract qualification failed")


if __name__ == "__main__":
    main()
