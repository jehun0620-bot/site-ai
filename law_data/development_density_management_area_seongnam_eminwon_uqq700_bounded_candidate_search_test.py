# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_seongnam_eminwon_uqq700_bounded_candidate_search.json"
URL = "http://eminwon.seongnam.go.kr/emwp/gov/mogaha/ntis/web/ofr/action/OfrAction.do"
HOST = "eminwon.seongnam.go.kr"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 8 * 1024 * 1024
MAX_PAGES_PER_QUERY = 5
PAGE_SIZE = 10

BASE_FORM = {
    "jndinm": "OfrNotAncmtEJB",
    "context": "NTIS",
    "method": "selectListOfrNotAncmt",
    "methodnm": "selectListOfrNotAncmtHomepage",
    "not_ancmt_sj": "",
    "pageIndex": "1",
    "ofr_pageSize": str(PAGE_SIZE),
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

QUERIES = [
    {"key": "B_Subject", "field": "title", "query": "개발밀도관리구역"},
    {"key": "B_Content", "field": "content", "query": "개발밀도관리구역"},
    {"key": "B_Subject", "field": "title", "query": "개발밀도 관리구역"},
    {"key": "B_Content", "field": "content", "query": "개발밀도 관리구역"},
    {"key": "B_Subject", "field": "title", "query": "개발밀도"},
    {"key": "B_Content", "field": "content", "query": "개발밀도"},
]

DIRECT_TERMS = ("개발밀도관리구역", "개발밀도 관리구역", "UQQ700")
RELATED_TERMS = ("개발밀도",)
MGT_RE = re.compile(r"not_ancmt_mgt_no\s*=\s*['\"]?(\d+)", re.I)
MGT_QUERY_RE = re.compile(r"not_ancmt_mgt_no=(\d+)", re.I)
TAG_RE = re.compile(r"<[^>]+>")
ROWISH_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def strip_tags(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", value or ""))).strip()


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


def make_form(spec: dict, page: int) -> dict[str, str]:
    data = dict(BASE_FORM)
    data["Key"] = spec["key"]
    data["temp"] = spec["query"]
    data["pageIndex"] = str(page)
    if spec["key"] == "B_Subject":
        data["not_ancmt_sj"] = spec["query"]
        data["not_ancmt_cn"] = ""
        data["dept_nm"] = ""
    elif spec["key"] == "B_Content":
        data["not_ancmt_sj"] = ""
        data["not_ancmt_cn"] = spec["query"]
        data["dept_nm"] = ""
    return data


def extract_candidates(text: str, spec: dict, page: int) -> list[dict]:
    candidates = []
    seen = set()
    chunks = ROWISH_RE.findall(text)
    if not chunks:
        chunks = [text]
    for chunk in chunks:
        ids = set(MGT_RE.findall(chunk)) | set(MGT_QUERY_RE.findall(chunk))
        if not ids:
            continue
        plain = strip_tags(chunk)
        direct_hits = [t for t in DIRECT_TERMS if t in plain]
        related_hits = [t for t in RELATED_TERMS if t in plain]
        for mgt_no in sorted(ids):
            key = (mgt_no, page, spec["field"], spec["query"])
            if key in seen:
                continue
            seen.add(key)
            status = "DIRECT_CANDIDATE" if direct_hits else ("RELATED_CANDIDATE" if related_hits else "SEARCH_RESULT_CANDIDATE")
            candidates.append({
                "not_ancmt_mgt_no": mgt_no,
                "page": page,
                "search_field": spec["field"],
                "query": spec["query"],
                "status": status,
                "direct_hits": direct_hits,
                "related_hits": related_hits,
                "row_text": plain[:1200],
            })
    return candidates


def main() -> None:
    print("=" * 60)
    print("SEONGNAM EMINWON UQQ700 BOUNDED CANDIDATE SEARCH - S152")
    print("=" * 60)
    print("Search contract: QUALIFIED BY S151")
    print("Max pages/query:", MAX_PAGES_PER_QUERY)
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})

    requests_log = []
    all_candidates = []
    stop_reason = None

    for spec in QUERIES:
        print("\nQUERY:", spec["field"], "|", spec["query"])
        for page in range(1, MAX_PAGES_PER_QUERY + 1):
            data = make_form(spec, page)
            res = bounded_post(session, data)
            text, encoding = decode_body(res["body"])
            official = host(res["final_url"]) == HOST
            query_echo = spec["query"] in text
            page_candidates = extract_candidates(text, spec, page) if res["state"] == "HTTP_RESPONSE_CAPTURED" else []
            rec = {
                "field": spec["field"],
                "query": spec["query"],
                "page": page,
                "state": res["state"],
                "http": res["http"],
                "official_host": official,
                "encoding": encoding,
                "query_echo": query_echo,
                "candidate_count": len(page_candidates),
                "overflow": res["overflow"],
                "error": res["error"],
            }
            requests_log.append(rec)
            all_candidates.extend(page_candidates)
            print("  PAGE:", page, "| STATE:", rec["state"], "| HTTP:", rec["http"], "| ECHO:", query_echo, "| CANDIDATES:", len(page_candidates))

            if res["state"] == "TECHNICAL_REQUEST_UNKNOWN":
                stop_reason = "TECHNICAL_REQUEST_UNKNOWN"
                break

            high_signal = [c for c in page_candidates if c["status"] in ("DIRECT_CANDIDATE", "RELATED_CANDIDATE")]
            if high_signal:
                stop_reason = "HIGH_SIGNAL_CANDIDATE_FOUND"
                break

            if not query_echo and page > 1:
                break
            if len(page_candidates) == 0 and page > 1:
                break

        if stop_reason:
            break

    dedup = {}
    for c in all_candidates:
        k = c["not_ancmt_mgt_no"]
        if k not in dedup:
            dedup[k] = c
        else:
            prev = dedup[k]
            if prev["status"] == "SEARCH_RESULT_CANDIDATE" and c["status"] != "SEARCH_RESULT_CANDIDATE":
                dedup[k] = c
    candidates = sorted(dedup.values(), key=lambda x: int(x["not_ancmt_mgt_no"]))

    direct = [c for c in candidates if c["status"] == "DIRECT_CANDIDATE"]
    related = [c for c in candidates if c["status"] == "RELATED_CANDIDATE"]
    generic = [c for c in candidates if c["status"] == "SEARCH_RESULT_CANDIDATE"]
    technical = sum(1 for r in requests_log if r["state"] == "TECHNICAL_REQUEST_UNKNOWN")

    if technical:
        semantic = "SEONGNAM_EMINWON_UQQ700_SEARCH_TECHNICAL_UNKNOWN"
    elif direct or related:
        semantic = "SEONGNAM_EMINWON_UQQ700_HIGH_SIGNAL_CANDIDATE_FOUND"
    elif candidates:
        semantic = "SEONGNAM_EMINWON_UQQ700_SEARCH_RESULT_CANDIDATES_FOUND"
    else:
        semantic = "SEONGNAM_EMINWON_UQQ700_NO_CANDIDATE_IN_BOUNDED_SEARCH_SURFACE"

    out = {
        "step": "STEP 17-21-C-16-8-T-48-S152",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "SEONGNAM_EMINWON_HISTORICAL_NOTICE",
        "search_endpoint": URL,
        "search_contract": {
            "method": "selectListOfrNotAncmt",
            "methodnm": "selectListOfrNotAncmtHomepage",
            "page_size": PAGE_SIZE,
            "max_pages_per_query": MAX_PAGES_PER_QUERY,
        },
        "queries": QUERIES,
        "request_log": requests_log,
        "candidates": candidates,
        "summary": {
            "request_count": len(requests_log),
            "candidate_count": len(candidates),
            "direct_candidate_count": len(direct),
            "related_candidate_count": len(related),
            "generic_search_result_candidate_count": len(generic),
            "technical_unknown_count": technical,
            "stop_reason": stop_reason,
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

    print("\nCANDIDATES")
    for c in candidates:
        print(c)
    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    checks = {
        "bounded request ceiling respected": len(requests_log) <= len(QUERIES) * MAX_PAGES_PER_QUERY,
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
        raise AssertionError("S152 bounded UQQ700 candidate search failed")


if __name__ == "__main__":
    main()
