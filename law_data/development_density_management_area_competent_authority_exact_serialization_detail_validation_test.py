# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-16-S7-S3
Development Density Management Area
Exact Serialization Detail Validation

Uses only S7-S2 recovered full function/form serialization and S6-S1 hardened known-sample
bindings. Builds exact family request contracts from observed code, executes at most one known
sample per family, and validates response reproduction. No UQQ700 target identity evaluation.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set
from urllib.parse import urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
S6S1_PATH = BASE_DIR / "law_data" / "output" / "development_density_management_area_competent_authority_sample_global_binding_cardinality_hardening.json"
S7S2_PATH = BASE_DIR / "law_data" / "output" / "development_density_management_area_competent_authority_full_function_form_serialization_probe.json"
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "development_density_management_area_competent_authority_exact_serialization_detail_validation.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
FAMILY_NOTICE = "CURRENT_MUNICIPAL_OFFICIAL_NOTICE_ARCHIVE"
FAMILY_URBAN = "CURRENT_URBAN_PLANNING_INFORMATION_ARCHIVE"
EXPECTED_FUNCTIONS = {FAMILY_NOTICE: "f_view", FAMILY_URBAN: "fn_move_form"}
MAX_DETAIL_REQUESTS = 2
TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
TAG_RE = re.compile(r"<[^>]+>", re.S)
SCRIPT_STYLE_RE = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>", re.I | re.S)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def uniq(values: Iterable[Any]) -> List[str]:
    out, seen = [], set()
    for v in values:
        t = norm(v)
        if t and t not in seen:
            seen.add(t); out.append(t)
    return out


def host(url: str) -> str:
    try: return (urlparse(url).hostname or "").lower()
    except Exception: return ""


def gov(h: str) -> bool:
    return bool(h) and (h == "go.kr" or h.endswith(".go.kr"))


def plain(raw: str) -> str:
    x = COMMENT_RE.sub(" ", raw or "")
    x = SCRIPT_STYLE_RE.sub(" ", x)
    x = TAG_RE.sub(" ", x)
    return norm(html.unescape(x))


def fetch(session: requests.Session, method: str, url: str, data: Optional[Dict[str, str]] = None, referer: str = "") -> Dict[str, Any]:
    result = {"http_status": None, "final_url": "", "text": "", "bytes": 0, "error": ""}
    try:
        headers = {"Referer": referer} if referer else {}
        with session.request(method, url, data=data, headers=headers, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
            result["http_status"] = r.status_code; result["final_url"] = str(r.url)
            chunks, total = [], 0
            for c in r.iter_content(131072):
                if not c: continue
                total += len(c)
                if total > MAX_RESPONSE_BYTES: raise ValueError("response too large")
                chunks.append(c)
            raw = b"".join(chunks); result["bytes"] = len(raw)
            for enc in uniq([r.encoding, "utf-8", "cp949", "euc-kr"]):
                try: result["text"] = raw.decode(enc); break
                except Exception: pass
            if not result["text"]: result["text"] = raw.decode("utf-8", errors="replace")
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def load_samples(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result = {}
    pool = data.get("next_stage_binding_pool") if isinstance(data.get("next_stage_binding_pool"), list) else []
    for item in pool:
        if not isinstance(item, dict) or item.get("qualified_for_next_stage") is not True: continue
        fam = norm(item.get("source_family"))
        if fam in result: continue
        binds = item.get("row_local_bindings") if isinstance(item.get("row_local_bindings"), list) else []
        if len(binds) != 1: continue
        result[fam] = item
    return result


def load_serialization(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result = {}
    for item in data.get("next_stage_serialization_pool") or []:
        if isinstance(item, dict): result[norm(item.get("source_family"))] = item
    return result


def build_contract(family: str, ser: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    recovered = ser.get("recovered") if isinstance(ser.get("recovered"), list) else []
    if not recovered: return None
    # require all recovered definitions to agree
    contracts = []
    for rec in recovered:
        body = norm(rec.get("function_body"))
        page_url = norm(rec.get("page_url"))
        args = rec.get("function_args") if isinstance(rec.get("function_args"), list) else []
        if family == FAMILY_NOTICE:
            if args != ["notAncmtMgtNo"] or "/pm010301/" not in body or "#searchFrm" not in body or "submit" not in body:
                continue
            contracts.append({"method": "GET", "mode": "PATH_APPEND", "base_path": "/pm010301/", "page_url": page_url})
        elif family == FAMILY_URBAN:
            if args != ["pstSn"] or "/ct-bbs020101/" not in body or "pstSn" not in body or "submit" not in body:
                continue
            # full function proves path append and value assignment; form method/action is observed but final action is overwritten by function
            contracts.append({"method": "POST", "mode": "PATH_APPEND", "base_path": "/ct-bbs020101/", "page_url": page_url})
    if not contracts: return None
    keys = {(c["method"], c["mode"], c["base_path"]) for c in contracts}
    if len(keys) != 1: return None
    c = contracts[0]
    return {"method": c["method"], "mode": c["mode"], "base_path": c["base_path"], "evidence_pages": uniq(x["page_url"] for x in contracts)}


def markers(sample: Dict[str, Any]) -> tuple[List[str], List[str]]:
    tokens = sample.get("sample_tokens") if isinstance(sample.get("sample_tokens"), dict) else {}
    return uniq(tokens.get("notice_numbers") or []), uniq(tokens.get("titles") or [])


def main() -> None:
    print("="*60); print("DEVELOPMENT DENSITY MANAGEMENT AREA"); print("EXACT SERIALIZATION DETAIL VALIDATION"); print("="*60)
    print("Target:", TARGET_NAME); print("Standard code:", STANDARD_CODE); print("Target identity evaluation: DISABLED"); print()
    if not S6S1_PATH.exists() or not S7S2_PATH.exists(): raise FileNotFoundError("required input missing")
    s6 = json.loads(S6S1_PATH.read_text(encoding="utf-8")); s72 = json.loads(S7S2_PATH.read_text(encoding="utf-8"))
    samples = load_samples(s6); serial = load_serialization(s72)
    session = requests.Session(); session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    results = []; validated = []; detail_requests = 0
    for family in [FAMILY_NOTICE, FAMILY_URBAN]:
        sample = samples.get(family); ser = serial.get(family); contract = build_contract(family, ser or {}) if ser else None
        executed = False; response = {}; reproduced = False; mn=[]; mt=[]; target_url=""
        argument = ""
        if sample:
            binds = sample.get("row_local_bindings") or []
            if len(binds)==1: argument = norm(binds[0].get("argument"))
        if contract and argument and detail_requests < MAX_DETAIL_REQUESTS:
            evidence_page = contract["evidence_pages"][0]
            origin = f"{urlparse(evidence_page).scheme}://{urlparse(evidence_page).netloc}"
            target_url = urljoin(origin, contract["base_path"] + argument)
            if gov(host(target_url)):
                response = fetch(session, contract["method"], target_url, referer=evidence_page)
                detail_requests += 1; executed = True
                p = plain(str(response.get("text") or "")); notices, titles = markers(sample)
                mn = [x for x in notices if x and x in p]; mt = [x for x in titles if x and x in p]
                reproduced = bool(mn or mt)
        classification = "VALIDATED_EXACT_SERIALIZATION_DETAIL_CONTRACT" if executed and isinstance(response.get("http_status"), int) and 200 <= response["http_status"] < 300 and reproduced else ("REJECTED_SAMPLE_REPRODUCTION_MISMATCH" if executed else "NO_EXECUTABLE_EXACT_SERIALIZATION_CONTRACT")
        rec = {"source_family": family, "sample_index": sample.get("sample_index") if sample else None, "argument": argument, "contract": contract, "target_url": target_url, "executed": executed, "http_status": response.get("http_status") if executed else None, "final_url": response.get("final_url") if executed else "", "matched_notice_numbers": mn, "matched_titles": mt, "sample_reproduced": reproduced, "classification": classification, "target_identity_evaluated": False, "document_candidate": False, "verified_positive": False, "runtime_registration_allowed": False, "site_positive_allowed": False, "site_negative_allowed": False}
        results.append(rec)
        if classification.startswith("VALIDATED_"): validated.append(rec)
        print("-"*60); print("Family:", family); print("Argument:", argument); print("Contract:", contract); print("Executed:", executed); print("HTTP:", rec["http_status"]); print("Matched notices:", mn); print("Matched titles:", mt); print("Resolution:", classification)
    out = {"step":"STEP 17-21-C-16-8-T-16-S7-S3 Exact Serialization Detail Validation","target":{"name":TARGET_NAME,"standard_code":STANDARD_CODE},"resolution_policy":{"resolution_type":RESOLUTION_TYPE,"negative_evidence_allowed":False,"source_failure_site_status":"UNKNOWN"},"summary":{"family_count":2,"detail_request_count":detail_requests,"validated_family_count":len(validated)},"family_results":results,"next_stage_validated_detail_contract_pool":validated,"resolution":"COMPETENT_AUTHORITY_EXACT_SERIALIZATION_DETAIL_VALIDATION_COMPLETED" if validated else "COMPETENT_AUTHORITY_EXACT_SERIALIZATION_DETAIL_VALIDATION_NO_CONTRACT","verified_positive":False,"runtime_registration_allowed":False,"site_positive_allowed":False,"site_negative_allowed":False}
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    bad = sum(1 for x in validated if not x.get("sample_reproduced")); unsafe = sum(1 for x in results+validated if x.get("target_identity_evaluated") or x.get("document_candidate") or x.get("verified_positive") or x.get("runtime_registration_allowed") or x.get("site_positive_allowed") or x.get("site_negative_allowed"))
    vals={"inputs exist":S6S1_PATH.exists() and S7S2_PATH.exists(),"detail request budget respected":detail_requests<=MAX_DETAIL_REQUESTS,"validated samples reproduced":bad==0,"unsafe promotion leakage zero":unsafe==0,"output written":OUT_PATH.exists() and OUT_PATH.stat().st_size>0}
    print(); print("="*60); print("RESULT"); print("="*60); print("Detail request count:",detail_requests); print("Validated family count:",len(validated)); print("Output:",OUT_PATH); print(); print("VALIDATION")
    for k,v in vals.items(): print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()): raise AssertionError("exact serialization detail validation failed")

if __name__ == "__main__": main()
