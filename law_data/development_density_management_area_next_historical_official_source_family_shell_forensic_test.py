# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_next_historical_official_source_family_shell_forensic.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 8 * 1024 * 1024
TIMEOUT = 25

SEEDS = [
    {"family": "NATIONAL_LAND_USE_PORTAL", "url": "https://www.eum.go.kr/"},
    {"family": "GG_URBAN_PLANNING_PORTAL", "url": "https://gris.gg.go.kr/"},
    {"family": "NATIONAL_LAW_NOTICE_AUXILIARY", "url": "https://www.law.go.kr/"},
]

SCRIPT_SRC_RE = re.compile(r'<script\b[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']', re.I)
FRAME_SRC_RE = re.compile(r'<(?:iframe|frame)\b[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']', re.I)
META_REFRESH_RE = re.compile(r'<meta\b[^>]*http-equiv\s*=\s*["\']?refresh["\']?[^>]*content\s*=\s*["\'][^"\']*url\s*=\s*([^"\'>; ]+)', re.I)
INLINE_URL_RE = re.compile(r'["\']((?:https?:)?//[^"\']+|/[^"\']*(?:api|ajax|search|list|notice|gosi|gonggo|urban|plan|bbs|board|archive|history)[^"\']*)["\']', re.I)
XHR_HINT_RE = re.compile(r'(?i)(?:fetch\s*\(|axios\.|\.ajax\s*\(|XMLHttpRequest|open\s*\(\s*["\'](?:GET|POST)["\'])')
KEYWORDS = ("도시계획", "도시관리계획", "고시", "공고", "지형도면", "토지이용", "notice", "gosi", "gonggo", "urban", "plan", "archive", "history", "search", "bbs", "board", "api", "ajax")


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def official_host(h: str) -> bool:
    return h.endswith("go.kr")


def bounded_get(session: requests.Session, url: str) -> dict:
    try:
        r = session.get(url, timeout=TIMEOUT, stream=True, allow_redirects=True)
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
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="ignore"), "utf-8-ignore"


def normalize_child(base_url: str, raw: str) -> str:
    return urljoin(base_url, html.unescape(raw.strip()))


def main() -> None:
    print("=" * 60)
    print("NEXT HISTORICAL OFFICIAL SOURCE FAMILY SHELL FORENSIC - S159")
    print("=" * 60)
    print("Child URL requests: DISABLED")
    print("UQQ700 target search: DISABLED")
    print("Negative evidence: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    seed_results = []
    child_map = {}
    xhr_snippets = []

    for seed in SEEDS:
        res = bounded_get(session, seed["url"])
        text, encoding = decode(res["body"])
        h = host(res["final_url"])
        ok = res["state"] == "HTTP_RESPONSE_CAPTURED" and res["http"] == 200 and official_host(h)
        rec = {
            "family": seed["family"], "state": res["state"], "http": res["http"],
            "final_url": res["final_url"], "official_host": official_host(h), "encoding": encoding,
            "overflow": res["overflow"], "error": res["error"],
        }
        seed_results.append(rec)
        print("SEED:", seed["family"], "| STATE:", rec["state"], "| HTTP:", rec["http"], "| FINAL:", rec["final_url"])
        if not ok:
            continue

        buckets = [
            ("SCRIPT_SRC", SCRIPT_SRC_RE.findall(text)),
            ("FRAME_SRC", FRAME_SRC_RE.findall(text)),
            ("META_REFRESH", META_REFRESH_RE.findall(text)),
            ("INLINE_URL_LITERAL", INLINE_URL_RE.findall(text)),
        ]
        for kind, raws in buckets:
            for raw in raws:
                url = normalize_child(res["final_url"], raw)
                ch = host(url)
                if not official_host(ch):
                    continue
                hay = url.lower()
                hits = [k for k in KEYWORDS if k.lower() in hay]
                key = (seed["family"], url)
                prev = child_map.get(key)
                item = {"family": seed["family"], "kind": kind, "url": url, "keyword_hits": hits}
                if prev is None or (not prev["keyword_hits"] and hits):
                    child_map[key] = item

        if XHR_HINT_RE.search(text):
            compact = re.sub(r"\s+", " ", text)
            for m in XHR_HINT_RE.finditer(compact):
                s = max(0, m.start() - 500)
                e = min(len(compact), m.end() + 1200)
                snippet = compact[s:e]
                if any(k.lower() in snippet.lower() for k in KEYWORDS):
                    xhr_snippets.append({"family": seed["family"], "snippet": snippet[:1800]})
                    if len(xhr_snippets) >= 50:
                        break

    children = sorted(child_map.values(), key=lambda x: (x["family"], 0 if x["keyword_hits"] else 1, x["url"]))
    relevant_children = [x for x in children if x["keyword_hits"]]
    successful = sum(1 for r in seed_results if r["state"] == "HTTP_RESPONSE_CAPTURED" and r["http"] == 200 and r["official_host"])
    technical = sum(1 for r in seed_results if r["state"] == "TECHNICAL_REQUEST_UNKNOWN")

    out = {
        "step": "STEP 17-21-C-16-8-T-55-S159",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "purpose": "FORENSICALLY_RECOVER_CHILD_ENDPOINTS_FROM_OFFICIAL_SOURCE_SHELLS",
        "seed_results": seed_results,
        "child_urls": children,
        "relevant_child_urls": relevant_children,
        "xhr_snippets": xhr_snippets,
        "summary": {
            "successful_seed_count": successful,
            "technical_seed_unknown_count": technical,
            "child_url_count": len(children),
            "relevant_child_url_count": len(relevant_children),
            "xhr_snippet_count": len(xhr_snippets),
            "semantic_state": "NEXT_HISTORICAL_OFFICIAL_SOURCE_FAMILY_SHELL_FORENSIC_CAPTURED",
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "child_url_requests_executed": False,
        "uqq700_target_search_executed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nRELEVANT CHILD URLS")
    for x in relevant_children[:100]:
        print(x)
    print("\nXHR/API SNIPPETS")
    for x in xhr_snippets[:30]:
        print(x)
    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    checks = {
        "at least one official seed reachable": successful >= 1,
        "child URL requests disabled": not out["child_url_requests_executed"],
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
        raise AssertionError("S159 source family shell forensic failed")


if __name__ == "__main__":
    main()
