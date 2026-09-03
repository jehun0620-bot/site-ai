# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_eum_gosi_canonical_list_state_forensic.json"
LIST_URL = "https://www.eum.go.kr/web/gs/gv/gvGosiList.jsp"
DETAIL_URL = "https://www.eum.go.kr/web/gs/gv/gvGosiDet.jsp"
HOST = "www.eum.go.kr"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 12 * 1024 * 1024

DETAIL_CONTROLS = ["638968", "632588"]
HREF_RE = re.compile(r'<a\b[^>]*\bhref\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
TAG_RE = re.compile(r'<[^>]+>')
DETAIL_ROW_RE = re.compile(r'href\s*=\s*["\']([^"\']*gvGosiDet\.jsp[^"\']*)["\']', re.I)


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def strip_tags(v: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", v or ""))).strip()


def bounded_get(session: requests.Session, url: str, params: dict[str, str] | None = None) -> dict:
    try:
        r = session.get(url, params=params, timeout=25, stream=True, allow_redirects=True)
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
        return {"state": "TECHNICAL_REQUEST_UNKNOWN", "http": None, "final_url": url, "body": b"", "overflow": False, "error": f"{type(exc).__name__}: {exc}"}


def decode(raw: bytes) -> tuple[str, str]:
    for enc in ("euc-kr", "utf-8", "cp949"):
        try:
            text = raw.decode(enc)
            if "고시정보" in text or "고시제목" in text:
                return text, enc
        except UnicodeDecodeError:
            pass
    return raw.decode("euc-kr", errors="ignore"), "euc-kr-ignore"


def query_map(url: str) -> dict[str, list[str]]:
    return {k: v for k, v in parse_qs(urlparse(url).query, keep_blank_values=True).items()}


def main() -> None:
    print("=" * 60)
    print("EUM GOSI CANONICAL LIST-STATE FORENSIC - S166")
    print("=" * 60)
    print("Search execution: DISABLED")
    print("UQQ700 target search: DISABLED")
    print("Negative evidence: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})

    detail_results = []
    canonical_keys: set[str] = set()

    for seq in DETAIL_CONTROLS:
        res = bounded_get(session, DETAIL_URL, {"seq": seq})
        text, enc = decode(res["body"])
        back_links = []
        if res["state"] == "HTTP_RESPONSE_CAPTURED" and res["http"] == 200 and host(res["final_url"]) == HOST:
            for href, body in HREF_RE.findall(text):
                label = strip_tags(body)
                if "목록" not in label:
                    continue
                u = urljoin(res["final_url"], html.unescape(href))
                qm = query_map(u)
                canonical_keys.update(qm.keys())
                back_links.append({"label": label, "url": u, "query": qm})
        row = {
            "seq": seq,
            "state": res["state"],
            "http": res["http"],
            "encoding": enc,
            "back_links": back_links,
            "error": res["error"],
        }
        detail_results.append(row)
        print("DETAIL:", seq, "| STATE:", row["state"], "| HTTP:", row["http"], "| BACK_LINKS:", len(back_links))
        for x in back_links:
            print("  BACK:", x)

    list_res = bounded_get(session, LIST_URL)
    list_text, list_enc = decode(list_res["body"])
    row_links = []
    if list_res["state"] == "HTTP_RESPONSE_CAPTURED" and list_res["http"] == 200 and host(list_res["final_url"]) == HOST:
        for raw in DETAIL_ROW_RE.findall(list_text):
            u = urljoin(list_res["final_url"], html.unescape(raw))
            qm = query_map(u)
            canonical_keys.update(qm.keys())
            row_links.append({"url": u, "query": qm})
            if len(row_links) >= 20:
                break

    print("\nCURRENT LIST DETAIL LINKS")
    for x in row_links:
        print(x)

    out = {
        "step": "STEP 17-21-C-16-8-T-62-S166",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "NATIONAL_LAND_USE_PORTAL",
        "detail_controls": detail_results,
        "current_list": {
            "state": list_res["state"],
            "http": list_res["http"],
            "encoding": list_enc,
            "detail_links": row_links,
            "error": list_res["error"],
        },
        "canonical_query_keys": sorted(canonical_keys),
        "summary": {
            "detail_control_count": len(detail_results),
            "detail_back_link_count": sum(len(x["back_links"]) for x in detail_results),
            "current_list_detail_link_count": len(row_links),
            "canonical_query_key_count": len(canonical_keys),
            "technical_unknown_count": sum(1 for x in detail_results if x["state"] == "TECHNICAL_REQUEST_UNKNOWN") + (1 if list_res["state"] == "TECHNICAL_REQUEST_UNKNOWN" else 0),
            "semantic_state": "EUM_GOSI_CANONICAL_LIST_STATE_FORENSIC_CAPTURED",
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "search_request_executed": False,
        "uqq700_target_search_executed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nCANONICAL QUERY KEYS")
    for k in sorted(canonical_keys):
        print(k)
    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    checks = {
        "detail controls reachable": all(x["state"] == "HTTP_RESPONSE_CAPTURED" and x["http"] == 200 for x in detail_results),
        "current list reachable": list_res["state"] == "HTTP_RESPONSE_CAPTURED" and list_res["http"] == 200,
        "search request disabled": not out["search_request_executed"],
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
        raise AssertionError("S166 EUM canonical list-state forensic failed")


if __name__ == "__main__":
    main()
