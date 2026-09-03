# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_eum_gosi_detail_contract_qualification.json"
HOST = "www.eum.go.kr"
URL = "https://www.eum.go.kr/web/gs/gv/gvGosiDet.jsp"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 12 * 1024 * 1024

CONTROLS = [
    {"seq": "638968", "notice": "2026-121", "term": "분당지구단위계획"},
    {"seq": "632588", "notice": "2026-87", "term": "모란생태공원"},
]


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def bounded_get(session: requests.Session, seq: str) -> dict:
    try:
        r = session.get(URL, params={"seq": seq}, timeout=25, stream=True, allow_redirects=True)
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
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            text = raw.decode(enc)
            if "고시" in text or "도시관리계획" in text:
                return text, enc
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="ignore"), "utf-8-ignore"


def main() -> None:
    print("=" * 60)
    print("EUM GOSI DETAIL CONTRACT QUALIFICATION - S160")
    print("=" * 60)
    print("UQQ700 target search: DISABLED")
    print("Negative evidence: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    rows = []

    for c in CONTROLS:
        res = bounded_get(session, c["seq"])
        text, encoding = decode(res["body"])
        official = host(res["final_url"]) == HOST
        year, num = c["notice"].split("-")
        notice_ok = bool(re.search(r"성남시\s*고시\s*제?\s*" + re.escape(year) + r"\s*[-－]\s*" + re.escape(num) + r"\s*호", text))
        term_ok = c["term"] in text
        seq_ok = f"seq={c['seq']}" in res["final_url"]
        qualified = res["state"] == "HTTP_RESPONSE_CAPTURED" and res["http"] == 200 and official and notice_ok and term_ok and seq_ok
        row = {
            "seq": c["seq"], "expected_notice": c["notice"], "expected_term": c["term"],
            "state": "EUM_GOSI_DETAIL_CONTRACT_QUALIFIED" if qualified else ("TECHNICAL_REQUEST_UNKNOWN" if res["state"] == "TECHNICAL_REQUEST_UNKNOWN" else "EUM_GOSI_DETAIL_CONTRACT_NOT_RESOLVED"),
            "http": res["http"], "official_host": official, "encoding": encoding,
            "notice_ok": notice_ok, "term_ok": term_ok, "seq_ok": seq_ok,
            "overflow": res["overflow"], "error": res["error"],
        }
        rows.append(row)
        print("SEQ:", row["seq"], "| STATE:", row["state"], "| HTTP:", row["http"], "| NOTICE_OK:", notice_ok, "| TERM_OK:", term_ok, "| SEQ_OK:", seq_ok)

    qualified_count = sum(1 for r in rows if r["state"] == "EUM_GOSI_DETAIL_CONTRACT_QUALIFIED")
    technical = sum(1 for r in rows if r["state"] == "TECHNICAL_REQUEST_UNKNOWN")
    unresolved = sum(1 for r in rows if r["state"] == "EUM_GOSI_DETAIL_CONTRACT_NOT_RESOLVED")

    out = {
        "step": "STEP 17-21-C-16-8-T-56-S160",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "NATIONAL_LAND_USE_PORTAL",
        "detail_endpoint": URL,
        "detail_identity_key": "seq",
        "results": rows,
        "summary": {
            "sample_count": len(rows),
            "detail_contract_qualified_count": qualified_count,
            "technical_unknown_count": technical,
            "identity_or_content_mismatch_count": unresolved,
            "semantic_state": "EUM_GOSI_DETAIL_CONTRACT_QUALIFIED" if qualified_count == len(CONTROLS) else "EUM_GOSI_DETAIL_CONTRACT_NOT_YET_QUALIFIED",
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
        "sample request exact": len(rows) == len(CONTROLS),
        "all detail contracts qualified": qualified_count == len(CONTROLS),
        "technical unknown zero": technical == 0,
        "identity/content mismatch zero": unresolved == 0,
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
        raise AssertionError("S160 EUM gosi detail contract qualification failed")


if __name__ == "__main__":
    main()
