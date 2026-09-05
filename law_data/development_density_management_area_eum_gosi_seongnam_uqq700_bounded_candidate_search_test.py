# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_eum_gosi_seongnam_uqq700_bounded_candidate_search.json"
URL = "https://www.eum.go.kr/web/gs/gv/gvGosiList.jsp"
HOST = "www.eum.go.kr"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 12 * 1024 * 1024
GYEONGGI = "4100000000"
SEONGNAM = "4113000000"
MAX_PAGES_PER_QUERY = 3

BASE_CONTROLS = [
    ("pageNo", "1"),
    ("mode", ""),
    ("zonenm_t", ""),
    ("area", ""),
    ("chrgorg_t", ""),
    ("selSggCd", SEONGNAM),
    ("mobile_yn", ""),
    ("select2", GYEONGGI),
    ("select3", SEONGNAM),
    ("startdt", ""),
    ("enddt", ""),
    ("chrgorg", ""),
    ("gosichrg", ""),
    ("gosino", ""),
    ("prj_nm", ""),
    ("prj_cat_cd", ""),
    ("listSize", "50"),
]

QUERIES = [
    {"query": "개발밀도관리구역", "class": "DIRECT"},
    {"query": "개발밀도 관리구역", "class": "DIRECT"},
    {"query": "개발밀도", "class": "RELATED"},
    {"query": "UQQ700", "class": "DIRECT"},
]

ROW_RE = re.compile(
    r"<tr[^>]*>\s*"
    r"<td[^>]*>(?P<date>[\s\S]*?)</td>\s*"
    r"<td[^>]*title=[\"'](?P<notice>[^\"']*)[\"'][^>]*>[\s\S]*?</td>\s*"
    r"<td[^>]*>[\s\S]*?<a\s+href=[\"'](?P<href>[^\"']*gvGosiDet\.jsp[^\"']*)[\"'][^>]*title=[\"'](?P<title>[^\"']*)[\"']",
    re.I,
)
SEQ_RE = re.compile(r"(?:\?|&)seq=(\d+)")


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def enc_component(value: str) -> str:
    return quote_plus(value.encode("euc-kr"), safe="")


def encode_form(pairs: list[tuple[str, str]]) -> bytes:
    return "&".join(f"{quote_plus(k, safe='')}={enc_component(v)}" for k, v in pairs).encode("ascii")


def bounded(session: requests.Session, method: str, body: bytes | None = None) -> dict:
    try:
        if method == "get":
            r = session.get(URL, timeout=25, stream=True, allow_redirects=True)
        else:
            r = session.post(
                URL,
                data=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": URL,
                    "Origin": "https://www.eum.go.kr",
                },
                timeout=25,
                stream=True,
                allow_redirects=True,
            )
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
            "error": "RESPONSE_SIZE_LIMIT_EXCEEDED" if overflow else None,
        }
    except requests.RequestException as exc:
        return {"state": "TECHNICAL_REQUEST_UNKNOWN", "http": None, "final_url": URL, "body": b"", "error": f"{type(exc).__name__}: {exc}"}


def decode(raw: bytes) -> str:
    for enc in ("euc-kr", "cp949", "utf-8"):
        try:
            text = raw.decode(enc)
            if "고시정보" in text or "고시제목" in text:
                return text
        except UnicodeDecodeError:
            pass
    return raw.decode("euc-kr", errors="ignore")


def clean(v: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", v or ""))).strip()


def extract_rows(text: str, query: str, qclass: str, page: int) -> list[dict]:
    rows = []
    for m in ROW_RE.finditer(text):
        href = html.unescape(m.group("href"))
        seq_m = SEQ_RE.search(href)
        if not seq_m:
            continue
        title = clean(m.group("title"))
        notice = clean(m.group("notice"))
        date = clean(m.group("date"))
        if "성남시" not in notice:
            continue
        rows.append({
            "query": query,
            "query_class": qclass,
            "page": page,
            "seq": seq_m.group(1),
            "date": date,
            "notice": notice,
            "title": title,
            "href": href,
            "direct_term_in_title": any(t in title for t in ["개발밀도관리구역", "개발밀도 관리구역", "UQQ700"]),
            "related_term_in_title": "개발밀도" in title,
        })
    return rows


def has_next_page(text: str, next_page: int, query: str) -> bool:
    # Search state is reflected in result/pagination HTML when qualified.
    return bool(re.search(r"pageNo=" + str(next_page) + r"(?:&|['\"])", text)) and query in text


def main() -> None:
    print("=" * 60)
    print("EUM GOSI SEONGNAM UQQ700 BOUNDED CANDIDATE SEARCH - S174")
    print("=" * 60)
    print("Search contract: S172 QUALIFIED")
    print("Seongnam region filter: S173 QUALIFIED")
    print(f"Per-query page ceiling: {MAX_PAGES_PER_QUERY}")
    print("Candidate hit => STOP BULK AND REQUIRE DETAIL/CONTEXT DIAGNOSTIC")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    all_requests = []
    candidates = []
    stop_reason = None

    for spec in QUERIES:
        if stop_reason:
            break
        query = spec["query"]
        qclass = spec["class"]
        session = requests.Session()
        session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
        pre = bounded(session, "get")
        if pre["state"] != "HTTP_RESPONSE_CAPTURED" or pre["http"] != 200:
            all_requests.append({"query": query, "page": 0, "state": "TECHNICAL_REQUEST_UNKNOWN", "http": pre["http"], "error": pre["error"]})
            stop_reason = f"TECHNICAL_UNRESOLVED_PREFLIGHT:{query}"
            break

        for page in range(1, MAX_PAGES_PER_QUERY + 1):
            pairs = []
            for k, v in BASE_CONTROLS:
                pairs.append((k, str(page) if k == "pageNo" else v))
            pairs.append(("zonenm", query))
            post = bounded(session, "post", encode_form(pairs))
            text = decode(post["body"])
            query_echo = query in text
            region_echo = SEONGNAM in text and GYEONGGI in text
            rows = extract_rows(text, query, qclass, page)
            technical = not (post["state"] == "HTTP_RESPONSE_CAPTURED" and post["http"] == 200 and host(post["final_url"]) == HOST and query_echo and region_echo)
            state = "TECHNICAL_REQUEST_UNKNOWN" if technical else "SEARCH_PAGE_QUALIFIED"
            record = {
                "query": query,
                "query_class": qclass,
                "page": page,
                "state": state,
                "http": post["http"],
                "query_echo": query_echo,
                "region_echo": region_echo,
                "row_count": len(rows),
                "rows": rows,
                "error": post["error"],
            }
            all_requests.append(record)
            print("QUERY:", query, "| CLASS:", qclass, "| PAGE:", page, "| STATE:", state, "| HTTP:", post["http"], "| QUERY_ECHO:", query_echo, "| REGION_ECHO:", region_echo, "| ROWS:", len(rows))

            if technical:
                stop_reason = f"EXTRACTION_OR_REQUEST_UNKNOWN:{query}:page{page}"
                break

            for row in rows:
                if row["direct_term_in_title"]:
                    row = dict(row)
                    row["candidate_state"] = "DIRECT_CANDIDATE"
                    candidates.append(row)
                elif row["related_term_in_title"] or qclass == "RELATED":
                    row = dict(row)
                    row["candidate_state"] = "RELATED_CANDIDATE"
                    candidates.append(row)

            if candidates:
                stop_reason = "CANDIDATE_FOUND_REQUIRE_DETAIL_CONTEXT_DIAGNOSTIC"
                break

            if not has_next_page(text, page + 1, query):
                break

    # de-duplicate candidate identities while preserving strongest state
    rank = {"DIRECT_CANDIDATE": 2, "RELATED_CANDIDATE": 1}
    dedup = {}
    for c in candidates:
        key = c["seq"]
        if key not in dedup or rank[c["candidate_state"]] > rank[dedup[key]["candidate_state"]]:
            dedup[key] = c
    candidates = list(dedup.values())

    technical_unknown_count = sum(1 for r in all_requests if r["state"] == "TECHNICAL_REQUEST_UNKNOWN")
    direct_count = sum(1 for c in candidates if c["candidate_state"] == "DIRECT_CANDIDATE")
    related_count = sum(1 for c in candidates if c["candidate_state"] == "RELATED_CANDIDATE")

    if candidates:
        semantic_state = "EUM_SEONGNAM_UQQ700_CANDIDATE_FOUND_REQUIRES_DETAIL_CONTEXT_DIAGNOSTIC"
    elif technical_unknown_count:
        semantic_state = "EUM_SEONGNAM_UQQ700_BOUNDED_SEARCH_TECHNICAL_UNKNOWN"
    else:
        semantic_state = "EUM_SEONGNAM_UQQ700_NO_CANDIDATE_IN_BOUNDED_TITLE_SEARCH_SURFACE"

    out = {
        "step": "STEP 17-21-C-16-8-T-70-S174",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "NATIONAL_LAND_USE_PORTAL",
        "search_endpoint": URL,
        "search_field": "zonenm=TITLE",
        "transport": "WARM_SESSION_EUC_KR_FORM_URLENCODED",
        "region_filter": {"select2": GYEONGGI, "select3": SEONGNAM, "selSggCd": SEONGNAM},
        "query_specs": QUERIES,
        "max_pages_per_query": MAX_PAGES_PER_QUERY,
        "requests": all_requests,
        "candidates": candidates,
        "summary": {
            "request_count": len(all_requests),
            "candidate_count": len(candidates),
            "direct_candidate_count": direct_count,
            "related_candidate_count": related_count,
            "technical_unknown_count": technical_unknown_count,
            "stop_reason": stop_reason,
            "semantic_state": semantic_state,
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
    if not candidates:
        print("NONE")
    for c in candidates:
        print(c)
    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    checks = {
        "request count positive": len(all_requests) > 0,
        "technical unknown zero": technical_unknown_count == 0,
        "candidate stop policy respected": (not candidates) or stop_reason == "CANDIDATE_FOUND_REQUIRE_DETAIL_CONTEXT_DIAGNOSTIC",
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
        raise AssertionError("S174 EUM Seongnam UQQ700 bounded candidate search failed")


if __name__ == "__main__":
    main()
