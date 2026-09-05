# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote_plus

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data/output/development_density_management_area_eum_gosi_seongnam_coverage_boundary_probe.json"
URL = "https://www.eum.go.kr/web/gs/gv/gvGosiList.jsp"
GYEONGGI = "4100000000"
SEONGNAM = "4113000000"
UA = "Mozilla/5.0"
MAX_BYTES = 8 * 1024 * 1024

BASE_FORM = {
    "pageNo": "1", "mode": "", "zonenm_t": "", "area": "", "chrgorg_t": "",
    "selSggCd": SEONGNAM, "mobile_yn": "", "select2": GYEONGGI, "select3": SEONGNAM,
    "startdt": "", "enddt": "", "chrgorg": "", "gosichrg": "", "gosino": "",
    "prj_nm": "", "prj_cat_cd": "", "listSize": "50", "zonenm": "",
}

LAST_PAGE_RE = re.compile(r'pageNo=(\d+)[^>]+title=["\']마지막 페이지로 이동["\']', re.I)
DATE_RE = re.compile(r'<td[^>]*>\s*(\d{4}-\d{2}-\d{2})\s*</td>', re.I)
SEQ_RE = re.compile(r'gvGosiDet\.jsp\?seq=(\d+)')


def enc(v: str) -> str:
    return quote_plus(v.encode("euc-kr"), safe="")


def body_for(page: int) -> bytes:
    data = dict(BASE_FORM)
    data["pageNo"] = str(page)
    return "&".join(f"{k}={enc(v)}" for k, v in data.items()).encode("ascii")


def bounded(session: requests.Session, method: str, body: bytes | None = None):
    try:
        if method == "GET":
            r = session.get(URL, timeout=25, stream=True)
        else:
            r = session.post(URL, data=body, headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": URL, "Origin": "https://www.eum.go.kr"}, timeout=25, stream=True)
        buf = bytearray()
        try:
            for chunk in r.iter_content(65536):
                if not chunk:
                    continue
                if len(buf) + len(chunk) > MAX_BYTES:
                    return {"ok": False, "http": r.status_code, "body": b"", "error": "RESPONSE_SIZE_LIMIT_EXCEEDED"}
                buf.extend(chunk)
        finally:
            r.close()
        return {"ok": r.status_code == 200, "http": r.status_code, "body": bytes(buf), "error": None}
    except requests.RequestException as exc:
        return {"ok": False, "http": None, "body": b"", "error": f"{type(exc).__name__}: {exc}"}


def decode(raw: bytes) -> str:
    for e in ("euc-kr", "cp949", "utf-8"):
        try:
            return raw.decode(e)
        except UnicodeDecodeError:
            pass
    return raw.decode("euc-kr", errors="ignore")


def inspect_page(text: str) -> dict:
    dates = DATE_RE.findall(text)
    seqs = SEQ_RE.findall(text)
    return {
        "row_count": len(seqs),
        "seq_sample": seqs[:3] + (seqs[-3:] if len(seqs) > 3 else []),
        "newest_date": max(dates) if dates else None,
        "oldest_date": min(dates) if dates else None,
        "region_echo": GYEONGGI in text and SEONGNAM in text,
    }


def main() -> None:
    print("=" * 60)
    print("EUM GOSI SEONGNAM COVERAGE BOUNDARY PROBE - S175")
    print("=" * 60)
    print("Search query: NONE")
    print("Region filter: S173 QUALIFIED")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})

    pre = bounded(s, "GET")
    first = bounded(s, "POST", body_for(1)) if pre["ok"] else {"ok": False, "http": None, "body": b"", "error": "PREFLIGHT_FAILED"}
    first_text = decode(first["body"])
    first_info = inspect_page(first_text)

    m = LAST_PAGE_RE.search(first_text)
    last_page = int(m.group(1)) if m else None

    last = None
    last_info = None
    if first["ok"] and last_page and last_page > 1:
        last = bounded(s, "POST", body_for(last_page))
        last_info = inspect_page(decode(last["body"]))

    technical_unknown = (not pre["ok"]) or (not first["ok"]) or (last is not None and not last["ok"])
    semantic = "EUM_SEONGNAM_COVERAGE_BOUNDARY_QUALIFIED" if (not technical_unknown and last_page) else "EUM_SEONGNAM_COVERAGE_BOUNDARY_NOT_YET_QUALIFIED"

    out = {
        "step": "STEP 17-21-C-16-8-T-71-S175",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "NATIONAL_LAND_USE_PORTAL",
        "region_filter": {"select2": GYEONGGI, "select3": SEONGNAM, "selSggCd": SEONGNAM},
        "first_page": first_info,
        "last_page_number": last_page,
        "last_page": last_info,
        "summary": {
            "technical_unknown_count": 1 if technical_unknown else 0,
            "semantic_state": semantic,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("FIRST_PAGE:", first_info)
    print("LAST_PAGE_NUMBER:", last_page)
    print("LAST_PAGE:", last_info)
    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    checks = {
        "preflight qualified": pre["ok"],
        "first page qualified": first["ok"] and first_info["region_echo"],
        "coverage boundary inferred": last_page is not None and last_page >= 1,
        "last page qualified": last_page == 1 or (last is not None and last["ok"] and bool(last_info and last_info["region_echo"])),
        "technical unknown zero": not technical_unknown,
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
        raise AssertionError("S175 EUM Seongnam coverage boundary probe failed")


if __name__ == "__main__":
    main()
