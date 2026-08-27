# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-21
Development Density Management Area
Municipal Gazette Bounded Detail Validation

Execute exactly one known gazette detail request using the recovered fn_move_form
serialization contract. Validate reproduction of the known gazette identity only.
UQQ700 target identity evaluation remains disabled.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)
T19 = OUT_DIR / "development_density_management_area_municipal_gazette_interaction_contract_recovery.json"
T20 = OUT_DIR / "development_density_management_area_municipal_gazette_exact_serialization_contract_recovery.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_bounded_detail_validation.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
KNOWN_GAZETTE_NUMBER = 2087
KNOWN_ARGUMENT = "404960"
TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

TAG_RE = re.compile(r"<[^>]+>", re.S)
TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.I | re.S)
GAZETTE_RE = re.compile(r"성남시보\s*제\s*(\d+)\s*호", re.I)
DATE_RE = re.compile(r"(?:19|20)\d{2}년\s*\d{1,2}월\s*\d{1,2}일")


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def gov(h: str) -> bool:
    return bool(h) and (h == "go.kr" or h.endswith(".go.kr"))


def fetch(session: requests.Session, method: str, url: str, data: Dict[str, str] | None = None) -> Dict[str, Any]:
    out = {"http_status": None, "final_url": "", "text": "", "error": "", "response_bytes": 0}
    try:
        request = session.post if method == "POST" else session.get
        kwargs = {"timeout": TIMEOUT, "allow_redirects": True, "stream": True}
        if method == "POST":
            kwargs["data"] = data or {}
        with request(url, **kwargs) as response:
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


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE BOUNDED DETAIL VALIDATION")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Known-sample detail execution: ENABLED / ONE REQUEST")
    print("UQQ700 target identity evaluation: DISABLED")
    print()

    if not T19.exists() or not T20.exists():
        raise FileNotFoundError("T-19/T-20 input missing")

    t19 = json.loads(T19.read_text(encoding="utf-8"))
    t20 = json.loads(T20.read_text(encoding="utf-8"))

    row = None
    for item in t19.get("gazette_row_interactions") or []:
        if int(item.get("gazette_number") or 0) == KNOWN_GAZETTE_NUMBER:
            calls = item.get("function_calls") or []
            if any(c.get("function") == "fn_move_form" and str(c.get("argument")) == KNOWN_ARGUMENT for c in calls):
                row = item
                break
    if row is None:
        raise AssertionError("known T-19 gazette row not found")

    contracts = t20.get("next_stage_contract_pool") or []
    if len(contracts) != 1:
        raise AssertionError("T-20 contract cardinality must be exactly one")
    contract = contracts[0]

    source_url = norm(t20.get("source_url"))
    source_host = host(source_url)
    detail_url = urljoin(source_url, norm(contract.get("base_path")) + KNOWN_ARGUMENT)

    # Recover searchVO form method and hidden values from T-20 structural output.
    search_form = None
    for form in t20.get("forms") or []:
        if norm(form.get("id")) == "searchVO" or norm(form.get("name")) == "searchVO":
            search_form = form
            break
    if search_form is None:
        raise AssertionError("searchVO form not recovered")

    method = norm(search_form.get("method") or "GET").upper()
    if method not in {"GET", "POST"}:
        raise AssertionError(f"unsupported form method: {method}")

    hidden: Dict[str, str] = {}
    for item in search_form.get("inputs") or []:
        name = norm(item.get("name"))
        input_type = norm(item.get("type")).lower()
        if name and input_type == "hidden":
            hidden[name] = str(item.get("value") or "")
    if "pstSn" in {norm(x.get("name")) for x in search_form.get("inputs") or []}:
        hidden["pstSn"] = KNOWN_ARGUMENT

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})

    # Exactly one detail request.
    response = fetch(session, method, detail_url, hidden if method == "POST" else None)
    raw = response.get("text") or ""
    plain = norm(html.unescape(TAG_RE.sub(" ", raw)))
    title_match = TITLE_RE.search(raw)
    page_title = norm(html.unescape(TAG_RE.sub(" ", title_match.group(1)))) if title_match else ""
    gazette_numbers = sorted({int(x.group(1)) for x in GAZETTE_RE.finditer(plain)})
    dates = sorted({norm(x.group(0)) for x in DATE_RE.finditer(plain)})
    reproduced = KNOWN_GAZETTE_NUMBER in gazette_numbers

    resolution = (
        "MUNICIPAL_GAZETTE_BOUNDED_DETAIL_CONTRACT_VALIDATED"
        if reproduced
        else "MUNICIPAL_GAZETTE_BOUNDED_DETAIL_CONTRACT_REPRODUCTION_FAILED"
    )

    next_pool = []
    if reproduced:
        next_pool.append({
            "source_family": "CURRENT_MUNICIPAL_GAZETTE_ARCHIVE",
            "source_url": source_url,
            "detail_contract": {
                "method": method,
                "mode": "PATH_APPEND",
                "base_path": contract.get("base_path"),
                "argument_name": contract.get("argument_name"),
                "form_id": "searchVO",
            },
            "known_sample": {
                "gazette_number": KNOWN_GAZETTE_NUMBER,
                "argument": KNOWN_ARGUMENT,
                "detail_url": detail_url,
            },
            "requires_historical_pagination_boundary_recovery": True,
            "target_identity_evaluation_allowed": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
        })

    output = {
        "step": "STEP 17-21-C-16-8-T-21 Municipal Gazette Bounded Detail Validation",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {"resolution_type": RESOLUTION_TYPE, "negative_evidence_allowed": False, "source_failure_site_status": "UNKNOWN"},
        "request": {
            "method": method,
            "detail_url": detail_url,
            "hidden_params": hidden,
            "request_count": 1,
        },
        "response": {
            "http_status": response.get("http_status"),
            "final_url": response.get("final_url"),
            "response_bytes": response.get("response_bytes"),
            "page_title": page_title,
            "gazette_numbers": gazette_numbers,
            "dates": dates[:20],
            "known_sample_reproduced": reproduced,
        },
        "next_stage_contract_pool": next_pool,
        "resolution": resolution,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    unsafe = int(any([
        output["verified_positive"],
        output["runtime_registration_allowed"],
        output["site_positive_allowed"],
        output["site_negative_allowed"],
        output["final_positive_promotion_allowed"],
    ]))

    validations = {
        "T-19 input exists": T19.exists(),
        "T-20 input exists": T20.exists(),
        "known gazette row recovered": row is not None,
        "single serialization contract loaded": len(contracts) == 1,
        "searchVO form recovered": search_form is not None,
        "detail request count exactly one": True,
        "detail URL same official host": gov(host(detail_url)) and host(detail_url) == source_host,
        "HTTP 200": response.get("http_status") == 200,
        "known gazette identity reproduced": reproduced,
        "UQQ700 target identity evaluation disabled": True,
        "unsafe promotion leakage zero": unsafe == 0,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("Method:", method)
    print("Detail URL:", detail_url)
    print("Hidden params:", hidden)
    print("HTTP:", response.get("http_status"))
    print("Final URL:", response.get("final_url"))
    print("Page title:", page_title)
    print("Gazette numbers:", gazette_numbers)
    print("Dates:", dates[:10])
    print("Known sample reproduced:", reproduced)
    print("Resolution:", resolution)
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print("Unsafe promotion leakage:", unsafe)
    print("all_pass:", all(validations.values()))

    if not all(validations.values()):
        raise AssertionError("municipal gazette bounded detail validation failed")


if __name__ == "__main__":
    main()
