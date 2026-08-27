# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-19
Development Density Management Area
Municipal Gazette Interaction / Pagination Contract Recovery

Recover actual interaction evidence from the qualified Seongnam municipal gazette archive.
No UQQ700 target query, detail execution, or document promotion is allowed in this stage.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set
from urllib.parse import parse_qsl, urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)
T18_PATH = OUT_DIR / "development_density_management_area_municipal_gazette_archive_source_qualification.json"
OUT_PATH = OUT_DIR / "development_density_management_area_municipal_gazette_interaction_contract_recovery.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
FAMILY = "CURRENT_MUNICIPAL_GAZETTE_ARCHIVE"
TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

FORM_RE = re.compile(r"<form\b([^>]*)>(.*?)</form>", re.I | re.S)
INPUT_RE = re.compile(r"<input\b([^>]*)>", re.I | re.S)
ANCHOR_RE = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.I | re.S)
SCRIPT_RE = re.compile(r"<script\b[^>]*>(.*?)</script>", re.I | re.S)
ATTR_RE = re.compile(r'''([:\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))''', re.I)
TAG_RE = re.compile(r"<[^>]+>", re.S)
GAZETTE_RE = re.compile(r"성남시보\s*제\s*(\d+)\s*호", re.I)
FUNCTION_DEF_RE = re.compile(r"function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{(.*?)\}", re.S)
FUNCTION_CALL_RE = re.compile(r"([A-Za-z_$][\w$]*)\s*\(\s*['\"]?([0-9]+)['\"]?\s*\)")


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def attrs(raw: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for m in ATTR_RE.finditer(raw or ""):
        out[m.group(1).lower()] = html.unescape(m.group(2) or m.group(3) or m.group(4) or "")
    return out


def strip_tags(raw: str) -> str:
    return norm(html.unescape(TAG_RE.sub(" ", raw or "")))


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def gov(host: str) -> bool:
    return bool(host) and (host == "go.kr" or host.endswith(".go.kr"))


def fetch(session: requests.Session, url: str) -> Dict[str, Any]:
    out = {"http_status": None, "final_url": "", "text": "", "error": "", "response_bytes": 0}
    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
            out["http_status"] = response.status_code
            out["final_url"] = str(response.url)
            chunks: List[bytes] = []
            total = 0
            for chunk in response.iter_content(128 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise ValueError("response too large")
                chunks.append(chunk)
            raw = b"".join(chunks)
            out["response_bytes"] = len(raw)
            for enc in [response.encoding, "utf-8", "cp949", "euc-kr"]:
                if not enc:
                    continue
                try:
                    out["text"] = raw.decode(enc)
                    break
                except Exception:
                    continue
            if not out["text"]:
                out["text"] = raw.decode("utf-8", errors="replace")
    except Exception as exc:
        out["error"] = repr(exc)
    return out


def unique_dicts(items: Iterable[Dict[str, Any]], key_fields: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: Set[tuple] = set()
    for item in items:
        key = tuple(norm(item.get(field)) for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE INTERACTION CONTRACT RECOVERY")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Target query execution: DISABLED")
    print("Detail request execution: DISABLED")
    print("Document candidate promotion: DISABLED")
    print()

    if not T18_PATH.exists():
        raise FileNotFoundError(T18_PATH)
    t18 = json.loads(T18_PATH.read_text(encoding="utf-8"))
    pool = t18.get("next_stage_source_pool") or []
    if not pool:
        raise AssertionError("T-18 qualified municipal gazette source missing")
    source = pool[0]
    source_url = norm(source.get("url"))

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    response = fetch(session, source_url)
    raw = response.get("text") or ""
    final_url = response.get("final_url") or source_url

    forms: List[Dict[str, Any]] = []
    for m in FORM_RE.finditer(raw):
        a = attrs(m.group(1))
        body = m.group(2)
        inputs = []
        for im in INPUT_RE.finditer(body):
            ia = attrs(im.group(1))
            inputs.append({k: ia.get(k, "") for k in ("type", "name", "id", "value")})
        forms.append({
            "id": a.get("id", ""),
            "name": a.get("name", ""),
            "method": norm(a.get("method") or "GET").upper(),
            "action": urljoin(final_url, a.get("action") or final_url),
            "inputs": inputs,
        })

    row_interactions: List[Dict[str, Any]] = []
    pagination: List[Dict[str, Any]] = []
    static_detail_links: List[Dict[str, Any]] = []

    for m in ANCHOR_RE.finditer(raw):
        a = attrs(m.group(1))
        text = strip_tags(m.group(2))
        href = norm(a.get("href"))
        onclick = norm(a.get("onclick"))
        absolute = urljoin(final_url, href) if href and not href.lower().startswith("javascript:") else ""
        gazette_match = GAZETTE_RE.search(text)

        if gazette_match:
            calls = []
            for call in FUNCTION_CALL_RE.finditer(" ".join([href, onclick])):
                calls.append({"function": call.group(1), "argument": call.group(2)})
            row_interactions.append({
                "gazette_number": int(gazette_match.group(1)),
                "text": text,
                "href": href,
                "absolute_url": absolute,
                "onclick": onclick,
                "function_calls": calls,
            })
            if absolute and gov(hostname(absolute)):
                static_detail_links.append({"gazette_number": int(gazette_match.group(1)), "url": absolute, "text": text})

        if absolute:
            parsed = urlparse(absolute)
            params = dict(parse_qsl(parsed.query, keep_blank_values=True))
            if "curPage" in params:
                try:
                    page = int(params["curPage"])
                except Exception:
                    page = None
                if page is not None:
                    pagination.append({"url": absolute, "page": page, "key": "curPage", "text": text})

    functions: List[Dict[str, Any]] = []
    for script_match in SCRIPT_RE.finditer(raw):
        script = script_match.group(1)
        for m in FUNCTION_DEF_RE.finditer(script):
            name = m.group(1)
            body = norm(m.group(3))[:5000]
            if any(name == c.get("function") for row in row_interactions for c in row.get("function_calls") or []):
                functions.append({"name": name, "args": [norm(x) for x in m.group(2).split(",") if norm(x)], "body": body})

    row_interactions = unique_dicts(row_interactions, ["gazette_number", "href", "onclick"])
    pagination = unique_dicts(pagination, ["url"])
    static_detail_links = unique_dicts(static_detail_links, ["url"])
    functions = unique_dicts(functions, ["name", "body"])

    interaction_count = sum(len(row.get("function_calls") or []) for row in row_interactions)
    page_numbers = sorted({item["page"] for item in pagination})

    next_pool = []
    if row_interactions:
        next_pool.append({
            "source_family": FAMILY,
            "source_url": final_url,
            "forms": forms,
            "row_interactions": row_interactions,
            "static_detail_links": static_detail_links,
            "function_definitions": functions,
            "pagination_key": "curPage" if pagination else "",
            "observed_pagination_pages": page_numbers,
            "requires_exact_detail_contract_recovery": True,
            "target_query_executed": False,
            "detail_request_executed": False,
            "document_candidate_generated": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
        })

    resolution = (
        "MUNICIPAL_GAZETTE_INTERACTION_CONTRACT_RECOVERY_COMPLETED"
        if row_interactions
        else "MUNICIPAL_GAZETTE_INTERACTION_CONTRACT_RECOVERY_NO_ROW_INTERACTION"
    )

    output = {
        "step": "STEP 17-21-C-16-8-T-19 Municipal Gazette Interaction Contract Recovery",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {"resolution_type": RESOLUTION_TYPE, "negative_evidence_allowed": False, "source_failure_site_status": "UNKNOWN"},
        "summary": {
            "http_status": response.get("http_status"),
            "response_bytes": response.get("response_bytes"),
            "form_count": len(forms),
            "gazette_row_count": len(row_interactions),
            "row_function_call_count": interaction_count,
            "static_detail_link_count": len(static_detail_links),
            "function_definition_count": len(functions),
            "pagination_link_count": len(pagination),
            "observed_pagination_pages": page_numbers,
        },
        "forms": forms,
        "gazette_row_interactions": row_interactions,
        "static_detail_links": static_detail_links,
        "function_definitions": functions,
        "pagination_links": pagination,
        "next_stage_contract_pool": next_pool,
        "resolution": resolution,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    cross_host_static = sum(1 for x in static_detail_links if hostname(x["url"]) != hostname(final_url))
    unsafe = sum(1 for x in next_pool if x.get("target_query_executed") or x.get("detail_request_executed") or x.get("document_candidate_generated") or x.get("verified_positive") or x.get("runtime_registration_allowed") or x.get("site_positive_allowed") or x.get("site_negative_allowed"))
    validations = {
        "T-18 input exists": T18_PATH.exists(),
        "T-18 qualified source loaded": bool(pool),
        "HTTP 200": response.get("http_status") == 200,
        "official source host": gov(hostname(final_url)),
        "gazette rows recovered": len(row_interactions) > 0,
        "pagination contract observed": bool(pagination),
        "guessed detail URL generation disabled": True,
        "target query execution disabled": True,
        "detail request execution disabled": True,
        "document candidate promotion disabled": True,
        "cross-host static detail leakage zero": cross_host_static == 0,
        "unsafe promotion leakage zero": unsafe == 0,
        "output written": OUT_PATH.exists() and OUT_PATH.stat().st_size > 0,
    }

    print("HTTP:", response.get("http_status"))
    print("Final URL:", final_url)
    print("Forms:", len(forms))
    print("Gazette rows:", len(row_interactions))
    print("Row function calls:", interaction_count)
    print("Static detail links:", len(static_detail_links))
    print("Function definitions:", len(functions))
    print("Pagination links:", len(pagination))
    print("Observed pages:", page_numbers)
    print()
    for index, row in enumerate(row_interactions[:5], start=1):
        print(f"ROW {index}")
        print("Gazette:", row["gazette_number"])
        print("Text:", row["text"])
        print("Href:", row["href"])
        print("Onclick:", row["onclick"])
        print("Function calls:", row["function_calls"])
        print()
    print("Resolution:", resolution)
    print("Output:", OUT_PATH)
    print()
    print("VALIDATION")
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print("Cross-host static detail leakage:", cross_host_static)
    print("Unsafe promotion leakage:", unsafe)
    print("all_pass:", all(validations.values()))
    if not all(validations.values()):
        raise AssertionError("municipal gazette interaction contract recovery failed")


if __name__ == "__main__":
    main()
