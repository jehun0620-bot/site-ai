# -*- coding: utf-8 -*-

"""
District-unit-plan VWorld ↔ Seoul UPIS announcement identity join probe.

Diagnostic purpose only:
- Read the official Seoul upisAnnouncement dataset.
- Compare the VWorld LT_C_UPISUQ161 NTFC_SN value with ANCMNT_MNG_CD.
- Print matching official announcement identity fields.
- Write no output files.
- A missing match remains NOT_FOUND / UNKNOWN; it is never FALSE evidence.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
API_BASE = "http://openapi.seoul.go.kr:8088"
SERVICE_NAME = "upisAnnouncement"
PAGE_SIZE = 1000
TIMEOUT = 30

DEFAULT_VWORLD_NTFC_SN = "11000NTC199603305909"
TARGET_ENV = "DISTRICT_UNIT_PLAN_VWORLD_NTFC_SN"

IDENTITY_FIELDS = (
    "ANCMNT_MNG_CD",
    "ANCMNT_YMD",
    "ANCMNT_NO",
    "ANCMNT_INST",
    "TKCG_INST",
    "TTL",
    "CN",
)

load_dotenv(BASE_DIR / ".env")
SEOUL_OPEN_API_KEY = os.getenv("SEOUL_OPEN_API_KEY")


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    service = payload.get(SERVICE_NAME, {})
    result = service.get("RESULT", {})
    rows = service.get("row", [])
    return {
        "result_code": result.get("CODE"),
        "result_message": result.get("MESSAGE"),
        "total_count": int(service.get("list_total_count", 0) or 0),
        "rows": rows if isinstance(rows, list) else [],
    }


def _request_page(start: int, end: int) -> Dict[str, Any]:
    url = (
        f"{API_BASE}/{SEOUL_OPEN_API_KEY}/json/"
        f"{SERVICE_NAME}/{start}/{end}/"
    )
    try:
        response = requests.get(url, timeout=TIMEOUT)
        return {
            "http_status": response.status_code,
            "payload": response.json(),
            "error": None,
        }
    except Exception as exc:
        return {
            "http_status": None,
            "payload": None,
            "error": str(exc),
        }


def _fetch_all() -> Dict[str, Any]:
    if not SEOUL_OPEN_API_KEY:
        return {
            "query_status": "QUERY_FAILED",
            "rows": [],
            "error": "SEOUL_OPEN_API_KEY is missing",
        }

    first = _request_page(1, PAGE_SIZE)
    payload = first.get("payload")
    if not isinstance(payload, dict):
        return {
            "query_status": "QUERY_FAILED",
            "rows": [],
            "error": first.get("error") or "invalid first-page payload",
        }

    parsed = _parse_payload(payload)
    if parsed["result_code"] != "INFO-000":
        return {
            "query_status": "QUERY_FAILED",
            "rows": [],
            "error": parsed["result_message"],
            "result_code": parsed["result_code"],
        }

    rows: List[Dict[str, Any]] = list(parsed["rows"])
    total = parsed["total_count"]
    start = PAGE_SIZE + 1

    while start <= total:
        end = min(start + PAGE_SIZE - 1, total)
        page = _request_page(start, end)
        page_payload = page.get("payload")
        if not isinstance(page_payload, dict):
            return {
                "query_status": "QUERY_FAILED",
                "rows": rows,
                "error": page.get("error") or f"invalid payload at {start}-{end}",
                "result_code": parsed["result_code"],
                "total_count": total,
            }

        page_parsed = _parse_payload(page_payload)
        if page_parsed["result_code"] != "INFO-000":
            return {
                "query_status": "QUERY_FAILED",
                "rows": rows,
                "error": page_parsed["result_message"],
                "result_code": page_parsed["result_code"],
                "total_count": total,
            }

        rows.extend(page_parsed["rows"])
        start = end + 1

    return {
        "query_status": "QUERY_SUCCESS",
        "rows": rows,
        "result_code": parsed["result_code"],
        "total_count": total,
        "error": None,
    }


def _summarize(row: Dict[str, Any]) -> Dict[str, Any]:
    return {field: row.get(field) for field in IDENTITY_FIELDS}


def main() -> int:
    target_ntfc_sn = _text(os.getenv(TARGET_ENV)) or DEFAULT_VWORLD_NTFC_SN

    print("=" * 72)
    print("DISTRICT UNIT PLAN VWORLD ↔ SEOUL NOTICE IDENTITY JOIN PROBE")
    print("=" * 72)
    print("VWorld dataset: LT_C_UPISUQ161")
    print("VWorld NTFC_SN:", target_ntfc_sn)
    print("Seoul dataset:", SERVICE_NAME)
    print("Comparison: NTFC_SN == ANCMNT_MNG_CD (diagnostic exact match only)")
    print("Purpose: inspect identity linkage; no truth/promotion decision")

    api = _fetch_all()
    print("API status:", api.get("query_status"))
    print("API result code:", api.get("result_code"))
    print("API total count:", api.get("total_count"))
    print("Received rows:", len(api.get("rows", [])))

    if api.get("query_status") != "QUERY_SUCCESS":
        print("API error:", api.get("error"))
        print("Join status: UNKNOWN")
        print("No FALSE inference is allowed from API failure.")
        return 1

    matches = [
        row
        for row in api["rows"]
        if _text(row.get("ANCMNT_MNG_CD")) == target_ntfc_sn
    ]

    print("Exact ANCMNT_MNG_CD matches:", len(matches))

    if not matches:
        print("Join status: NOT_FOUND / UNKNOWN")
        print("No exact management-code match was found in this API response.")
        print("Absence is not SITE FALSE and does not prove identities differ globally.")
        print("=" * 72)
        print("PROBE_COMPLETE")
        return 0

    for index, row in enumerate(matches, start=1):
        print("-" * 72)
        print(f"MATCH {index}")
        print(json.dumps(_summarize(row), ensure_ascii=False, indent=2, default=str))

    print("=" * 72)
    print("Join status: EXACT_MANAGEMENT_CODE_MATCH_FOUND")
    print("This proves only an exact value match in the queried datasets.")
    print("It does not by itself prove current validity, SITE truth, promotion,")
    print("production registration, or runtime registration authority.")
    print("PROBE_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
