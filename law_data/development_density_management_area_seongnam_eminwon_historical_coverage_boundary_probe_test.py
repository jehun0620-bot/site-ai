# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_seongnam_eminwon_historical_coverage_boundary_probe.json"
URL = "http://eminwon.seongnam.go.kr/emwp/gov/mogaha/ntis/web/ofr/action/OfrAction.do"
HOST = "eminwon.seongnam.go.kr"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 8 * 1024 * 1024

BASE_FORM = {
    "jndinm": "OfrNotAncmtEJB",
    "context": "NTIS",
    "method": "selectListOfrNotAncmt",
    "methodnm": "selectListOfrNotAncmtHomepage",
    "not_ancmt_sj": "",
    "pageIndex": "1",
    "ofr_pageSize": "10",
    "homepage_pbs_yn": "Y",
    "subCheck": "Y",
    "epcCheck": "Y",
    "not_ancmt_se_code": "01,02,03,04,05,06,07",
    "cha_dep_code_nm": "",
    "countYn": "Y",
    "list_gubun": "A",
    "recent_mm": "",
    "yyyy": "",
    "yyyymmdd": "",
    "last_mm": "",
    "temp": "",
    "Key": "B_Subject",
    "not_ancmt_cn": "",
    "dept_nm": "",
    "nodate_recent_mm": "",
    "nodate_last_mm": "",
    "cgg_code": "",
}

# Positive controls already qualified by S147/S151.
# The purpose here is ONLY to test whether explicit yyyy filtering preserves those known records
# and therefore whether the historical search surface can be scoped beyond any implicit default range.
CONTROLS = [
    {"year": "2018", "query": "가마절", "expected_mgt_no": "66727", "expected_notice": "2018-168"},
    {"year": "2020", "query": "방재시설", "expected_mgt_no": "83899", "expected_notice": "2020-170"},
]


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def bounded_post(session: requests.Session, data: dict[str, str]) -> dict:
    try:
        r = session.post(URL, data=data, timeout=25, stream=True, allow_redirects=True)
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
            "final_url": URL,
            "body": b"",
            "overflow": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def decode_body(raw: bytes) -> tuple[str, str]:
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            text = raw.decode(enc)
            if "고시" in text or "공고" in text or "검색" in text:
                return text, enc
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="ignore"), "utf-8-ignore"


def main() -> None:
    print("=" * 60)
    print("SEONGNAM EMINWON HISTORICAL COVERAGE BOUNDARY PROBE - S153")
    print("=" * 60)
    print("UQQ700 target search: DISABLED")
    print("Historical year filter qualification: ENABLED")
    print("Negative evidence: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    results = []

    for control in CONTROLS:
        data = dict(BASE_FORM)
        data["Key"] = "B_Subject"
        data["temp"] = control["query"]
        data["not_ancmt_sj"] = control["query"]
        data["yyyy"] = control["year"]

        res = bounded_post(session, data)
        text, encoding = decode_body(res["body"])
        official = host(res["final_url"]) == HOST
        query_echo = control["query"] in text
        year_echo = control["year"] in text
        mgt_match = control["expected_mgt_no"] in text
        y, n = control["expected_notice"].split("-")
        notice_match = bool(re.search(r"성남시\s*고시\s*제?\s*" + re.escape(y) + r"\s*[-－]\s*" + re.escape(n) + r"\s*호?", text))
        qualified = (
            res["state"] == "HTTP_RESPONSE_CAPTURED"
            and res["http"] == 200
            and official
            and query_echo
            and (mgt_match or notice_match)
        )
        row = {
            "year": control["year"],
            "query": control["query"],
            "expected_mgt_no": control["expected_mgt_no"],
            "expected_notice": control["expected_notice"],
            "state": "YEAR_FILTER_POSITIVE_CONTROL_QUALIFIED" if qualified else ("TECHNICAL_REQUEST_UNKNOWN" if res["state"] == "TECHNICAL_REQUEST_UNKNOWN" else "YEAR_FILTER_POSITIVE_CONTROL_NOT_RESOLVED"),
            "http": res["http"],
            "official_host": official,
            "encoding": encoding,
            "query_echo": query_echo,
            "year_echo": year_echo,
            "expected_mgt_no_match": mgt_match,
            "expected_notice_match": notice_match,
            "overflow": res["overflow"],
            "error": res["error"],
        }
        results.append(row)
        print(
            "YEAR:", row["year"],
            "| QUERY:", row["query"],
            "| STATE:", row["state"],
            "| HTTP:", row["http"],
            "| MGT_NO_OK:", row["expected_mgt_no_match"],
            "| NOTICE_OK:", row["expected_notice_match"],
            "| QUERY_ECHO:", row["query_echo"],
            "| YEAR_ECHO:", row["year_echo"],
        )

    qualified = sum(1 for r in results if r["state"] == "YEAR_FILTER_POSITIVE_CONTROL_QUALIFIED")
    technical = sum(1 for r in results if r["state"] == "TECHNICAL_REQUEST_UNKNOWN")
    unresolved = sum(1 for r in results if r["state"] == "YEAR_FILTER_POSITIVE_CONTROL_NOT_RESOLVED")

    out = {
        "step": "STEP 17-21-C-16-8-T-49-S153",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "SEONGNAM_EMINWON_HISTORICAL_NOTICE",
        "search_endpoint": URL,
        "purpose": "QUALIFY_EXPLICIT_YEAR_FILTER_FOR_HISTORICAL_COVERAGE",
        "results": results,
        "summary": {
            "positive_control_count": len(results),
            "year_filter_qualified_count": qualified,
            "technical_unknown_count": technical,
            "positive_control_unresolved_count": unresolved,
            "semantic_state": "SEONGNAM_EMINWON_EXPLICIT_YEAR_FILTER_QUALIFIED" if qualified == len(CONTROLS) else "SEONGNAM_EMINWON_EXPLICIT_YEAR_FILTER_NOT_YET_QUALIFIED",
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

    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    checks = {
        "positive control request exact": len(results) == len(CONTROLS),
        "all explicit year controls qualified": qualified == len(CONTROLS),
        "technical unknown zero": technical == 0,
        "positive control unresolved zero": unresolved == 0,
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
        raise AssertionError("S153 eminwon historical coverage boundary probe failed")


if __name__ == "__main__":
    main()
