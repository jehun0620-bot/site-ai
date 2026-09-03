# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_eum_gosi_canonical_get_positive_control.json"
URL = "https://www.eum.go.kr/web/gs/gv/gvGosiList.jsp"
HOST = "www.eum.go.kr"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 12 * 1024 * 1024

CANONICAL_QUERY = {
    "pageNo": "",
    "zonenm": "",
    "startdt": "",
    "enddt": "",
    "chrgorg": "",
    "selSggCd": "",
    "select2": "",
    "select_3": "",
    "gosino": "",
    "gosichrg": "",
    "prj_nm": "",
    "prj_cat_cd": "",
    "geul_yn": "",
    "gihyung_yn": "",
    "silsi_yn": "",
    "mobile_yn": "",
}

CONTROLS = [
    {"query": "분당지구단위계획", "expected_seq": "638968", "expected_notice": "2026-121"},
    {"query": "모란생태공원", "expected_seq": "632588", "expected_notice": "2026-87"},
]


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def bounded_get(session: requests.Session, params: dict[str, str]) -> dict:
    try:
        r = session.get(URL, params=params, headers={"Referer": URL}, timeout=25, stream=True, allow_redirects=True)
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
    for enc in ("euc-kr", "utf-8", "cp949"):
        try:
            text = raw.decode(enc)
            if "고시정보" in text or "고시제목" in text:
                return text, enc
        except UnicodeDecodeError:
            pass
    return raw.decode("euc-kr", errors="ignore"), "euc-kr-ignore"


def main() -> None:
    print("=" * 60)
    print("EUM GOSI CANONICAL GET POSITIVE CONTROL - S168")
    print("=" * 60)
    print("POST replay: DISCONTINUED")
    print("UQQ700 target search: DISABLED")
    print("Negative evidence: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    results = []

    for c in CONTROLS:
        params = dict(CANONICAL_QUERY)
        params["zonenm"] = c["query"]
        res = bounded_get(session, params)
        text, encoding = decode(res["body"])
        official = host(res["final_url"]) == HOST
        seq_ok = bool(re.search(r"gvGosiDet\.jsp[^\"']*seq\s*=\s*" + re.escape(c["expected_seq"]), text, re.I)) or c["expected_seq"] in text
        year, num = c["expected_notice"].split("-")
        notice_ok = bool(re.search(r"성남시\s*고시\s*제?\s*" + re.escape(year) + r"\s*[-－]\s*" + re.escape(num) + r"\s*호", text))
        query_echo = c["query"] in text
        qualified = res["state"] == "HTTP_RESPONSE_CAPTURED" and res["http"] == 200 and official and seq_ok and notice_ok and query_echo
        state = "EUM_GOSI_CANONICAL_GET_QUALIFIED" if qualified else ("TECHNICAL_REQUEST_UNKNOWN" if res["state"] == "TECHNICAL_REQUEST_UNKNOWN" else "EUM_GOSI_CANONICAL_GET_NOT_RESOLVED")
        row = {
            "query": c["query"],
            "expected_seq": c["expected_seq"],
            "expected_notice": c["expected_notice"],
            "state": state,
            "http": res["http"],
            "official_host": official,
            "encoding": encoding,
            "seq_ok": seq_ok,
            "notice_ok": notice_ok,
            "query_echo": query_echo,
            "final_url": res["final_url"],
            "overflow": res["overflow"],
            "error": res["error"],
        }
        results.append(row)
        print("QUERY:", row["query"], "| STATE:", state, "| HTTP:", row["http"], "| SEQ_OK:", seq_ok, "| NOTICE_OK:", notice_ok, "| QUERY_ECHO:", query_echo)

    qualified_count = sum(1 for r in results if r["state"] == "EUM_GOSI_CANONICAL_GET_QUALIFIED")
    technical = sum(1 for r in results if r["state"] == "TECHNICAL_REQUEST_UNKNOWN")
    unresolved = sum(1 for r in results if r["state"] == "EUM_GOSI_CANONICAL_GET_NOT_RESOLVED")

    out = {
        "step": "STEP 17-21-C-16-8-T-64-S168",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "NATIONAL_LAND_USE_PORTAL",
        "search_endpoint": URL,
        "search_transport": "GET_CANONICAL_LIST_STATE_PROBE",
        "canonical_keys": list(CANONICAL_QUERY.keys()),
        "results": results,
        "summary": {
            "positive_control_count": len(results),
            "canonical_get_qualified_count": qualified_count,
            "technical_unknown_count": technical,
            "positive_control_unresolved_count": unresolved,
            "semantic_state": "EUM_GOSI_CANONICAL_GET_CONTRACT_QUALIFIED" if qualified_count == len(CONTROLS) else "EUM_GOSI_CANONICAL_GET_CONTRACT_NOT_QUALIFIED",
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
        "technical unknown zero": technical == 0,
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
        raise AssertionError("S168 EUM canonical GET positive control technical validation failed")


if __name__ == "__main__":
    main()
