# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import shutil
import subprocess
from html import unescape
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlparse

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
S227AR_OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_archive_route_recovery_forensic.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_attachment_parameter_contract_recovery.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE"
LIST_URL = "https://www.seongnam.go.kr/ct-bbs020101"
GETFILE_URL = "https://www.seongnam.go.kr/ct-bbs020101/getFile"
PREVIEW_URL = "https://www.seongnam.go.kr/ct-bbs020101/filePreview"
MAX_DETAIL_FETCH = 20
MAX_FILE_PROBES = 60

MOVE_PATTERNS = [
    re.compile(r"fn_move_form\s*\(\s*['\"]?(\d+)['\"]?\s*\)", re.I),
    re.compile(r"(?:pstSn|idx)\s*[=:]\s*['\"]?(\d+)['\"]?", re.I),
]
CALL_RE = re.compile(r"(?is)(getFile|filePreview)\s*\((.*?)\)")
FORM_RE = re.compile(r"(?is)<form\b([^>]*)>(.*?)</form>")
TITLE_RE = re.compile(r"(?is)<title[^>]*>(.*?)</title>")


def curl_request(url: str, *, method: str = "GET", data: str | None = None) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"http": None, "final_url": None, "content_type": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "60",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}|%{url_effective}|%{content_type}",
    ]
    if method.upper() == "POST":
        cmd += ["-X", "POST", "-H", "Content-Type: application/x-www-form-urlencoded"]
        if data is not None:
            cmd += ["--data", data]
    cmd.append(url)
    p = subprocess.run(cmd, capture_output=True)
    raw = p.stdout or b""
    marker = b"\n__META__"
    if marker in raw:
        body, meta = raw.rsplit(marker, 1)
        parts = meta.decode("utf-8", errors="replace").strip().split("|", 2)
        http = parts[0] if parts else None
        final_url = parts[1] if len(parts) > 1 else None
        content_type = parts[2] if len(parts) > 2 else None
    else:
        body, http, final_url, content_type = raw, None, None, None
    return {
        "http": http,
        "final_url": final_url,
        "content_type": content_type,
        "body": body,
        "stderr": (p.stderr or b"").decode("utf-8", errors="replace").strip(),
    }


def decode_body(body: bytes) -> tuple[str, str]:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            t = body.decode(enc)
            if enc == "utf-8" or "성남" in t:
                return t, enc
        except UnicodeDecodeError:
            pass
    return body.decode("utf-8", errors="replace"), "utf-8-replace"


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def attr_map(attrs: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r'''(?is)([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(["'])(.*?)\2''', attrs or ""):
        out[m.group(1).lower()] = unescape(m.group(3))
    return out


def page_title(html: str) -> str | None:
    m = TITLE_RE.search(html or "")
    return clean_html(m.group(1)) if m else None


def extract_detail_ids(html: str) -> list[str]:
    ids = []
    seen = set()
    for pat in MOVE_PATTERNS:
        for m in pat.finditer(html or ""):
            v = m.group(1)
            if v not in seen:
                seen.add(v)
                ids.append(v)
    return ids


def extract_forms(html: str) -> list[dict]:
    rows = []
    for fm in FORM_RE.finditer(html or ""):
        a = attr_map(fm.group(1))
        inputs = []
        for im in re.finditer(r"(?is)<input\b([^>]*)>", fm.group(2)):
            ia = attr_map(im.group(1))
            if ia.get("name"):
                inputs.append({"name": ia.get("name"), "value": ia.get("value", ""), "type": ia.get("type", "text")})
        rows.append({"id": a.get("id"), "name": a.get("name"), "method": (a.get("method") or "GET").upper(), "action": a.get("action"), "inputs": inputs})
    return rows


def parse_arg_tokens(arg_blob: str) -> list[str]:
    vals = []
    for part in re.split(r",\s*(?![^()]*\))", arg_blob or ""):
        p = part.strip()
        m = re.fullmatch(r"['\"](.*?)['\"]", p)
        if m:
            vals.append(m.group(1))
        elif re.fullmatch(r"\d+", p):
            vals.append(p)
        else:
            vals.append(p)
    return vals


def extract_file_calls(html: str) -> list[dict]:
    rows = []
    seen = set()
    for m in CALL_RE.finditer(html or ""):
        fn = m.group(1)
        args = parse_arg_tokens(m.group(2))
        key = (fn, tuple(args))
        if key in seen:
            continue
        seen.add(key)
        rows.append({"function": fn, "args": args, "raw": m.group(0)[:800]})
    return rows


def classify(resp: dict) -> dict:
    body = resp.get("body") or b""
    ct = (resp.get("content_type") or "").lower()
    return {
        "pdf_magic": body.startswith(b"%PDF-"),
        "ole_magic": body.startswith(bytes.fromhex("D0CF11E0A1B11AE1")),
        "zip_magic": body.startswith(b"PK\x03\x04"),
        "binary_content_type": any(x in ct for x in ("application/pdf", "application/octet-stream", "haansofthwp", "application/zip", "officedocument")),
        "html_content_type": "html" in ct,
        "body_size": len(body),
    }


def make_probe_candidates(call: dict, detail_id: str) -> list[dict]:
    fn = call["function"]
    base_url = GETFILE_URL if fn == "getFile" else PREVIEW_URL
    args = call["args"]
    probes = []

    # Most common Seongnam patterns: pstSn/fileSn, bbsCrtSn/fileSn, idx/fileSn, or positional ids.
    numeric = [x for x in args if re.fullmatch(r"\d+", x or "")]
    if len(numeric) >= 2:
        pairs = [
            {"pstSn": numeric[0], "fileSn": numeric[1]},
            {"bbsCrtSn": numeric[0], "fileSn": numeric[1]},
            {"idx": numeric[0], "fileSn": numeric[1]},
        ]
        for q in pairs:
            probes.append({"url": base_url + "?" + urlencode(q), "mode": "GET_QUERY", "params": q, "source_call": call})
    elif len(numeric) == 1:
        n = numeric[0]
        for q in ({"pstSn": detail_id, "fileSn": n}, {"pstSn": n}, {"fileSn": n}, {"idx": n}):
            probes.append({"url": base_url + "?" + urlencode(q), "mode": "GET_QUERY", "params": q, "source_call": call})

    return probes


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY PLANNING DOCUMENT ATTACHMENT PARAMETER CONTRACT RECOVERY - S227A-P")
    print("=" * 78)
    print("Purpose: recover getFile/filePreview parameter contract and verify one real binary attachment")
    print("UQQ700 target query: NOT EXECUTED")
    print("Attachment hit != designation notice")
    print("Attachment no-hit != legal absence")
    print("SITE FALSE inference: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    prior_exists = S227AR_OUT.exists()
    prior = json.loads(S227AR_OUT.read_text(encoding="utf-8")) if prior_exists else {}
    prior_route_ok = bool(prior.get("route_contract_qualified"))

    list_resp = curl_request(LIST_URL)
    list_html, list_enc = decode_body(list_resp.get("body") or b"")
    detail_ids = extract_detail_ids(list_html)[:MAX_DETAIL_FETCH]

    details = []
    all_calls = []
    probes = []
    for pst_sn in detail_ids:
        detail_url = f"{LIST_URL}/{pst_sn}"
        r = curl_request(detail_url)
        html, enc = decode_body(r.get("body") or b"")
        calls = extract_file_calls(html) if r.get("http") == "200" else []
        forms = extract_forms(html) if r.get("http") == "200" else []
        details.append({
            "pstSn": pst_sn,
            "url": detail_url,
            "http": r.get("http"),
            "title": page_title(html),
            "charset": enc,
            "file_call_count": len(calls),
            "file_calls": calls,
            "forms": forms,
        })
        for c in calls:
            all_calls.append({"pstSn": pst_sn, **c})
            probes.extend(make_probe_candidates(c, pst_sn))

    # De-duplicate probes while preserving order.
    uniq = []
    seen = set()
    for p in probes:
        if p["url"] not in seen:
            seen.add(p["url"])
            uniq.append(p)
    probes = uniq[:MAX_FILE_PROBES]

    probe_results = []
    verified = []
    for p in probes:
        r = curl_request(p["url"])
        cls = classify(r)
        row = {
            "url": p["url"],
            "mode": p["mode"],
            "params": p["params"],
            "source_call": p["source_call"],
            "http": r.get("http"),
            "final_url": r.get("final_url"),
            "content_type": r.get("content_type"),
            "content_class": cls,
        }
        probe_results.append(row)
        if r.get("http") == "200" and (cls["pdf_magic"] or cls["ole_magic"] or cls["zip_magic"] or cls["binary_content_type"]):
            verified.append(row)

    binary_verified = bool(verified)
    detail_contract_observed = bool(all_calls)

    if prior_route_ok and detail_contract_observed and binary_verified:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ATTACHMENT_PARAMETER_CONTRACT_VERIFIED"
        semantic = "VERIFIED_PLANNING_DETAIL_EXPOSED_FILE_CALL_PARAMETERS_AND_AT_LEAST_ONE_REAL_BINARY_ATTACHMENT_DOWNLOADED"
        next_action = "QUALIFY_ARCHIVE_COVERAGE_AND_ENUMERATE_CANONICAL_PLANNING_DOCUMENT_SET_BEFORE_UQQ700_CONTENT_SCAN"
    elif prior_route_ok and detail_contract_observed:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ATTACHMENT_PARAMETER_CONTRACT_OBSERVED_BINARY_TECHNICAL_UNKNOWN"
        semantic = "FILE_CALL_PARAMETER_SHAPE_OBSERVED_ON_VERIFIED_PLANNING_DETAIL_BUT_BINARY_DOWNLOAD_NOT_YET_RECOVERED"
        next_action = "HARDEN_PARAMETER_NAMES_OR_HTTP_METHOD_FROM_OBSERVED_FILE_CALLS_WITHOUT_NEGATIVE_INFERENCE"
    else:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ATTACHMENT_PARAMETER_CONTRACT_TECHNICAL_UNKNOWN"
        semantic = "PLANNING_DETAIL_FILE_CALL_CONTRACT_NOT_YET_OBSERVED_OR_PRIOR_ROUTE_NOT_QUALIFIED"
        next_action = "RECOVER_DETAIL_NAVIGATION_AND_FILE_CALL_CONTRACT_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-144-S227A-P",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "s227ar_input_exists": prior_exists,
        "prior_route_contract_qualified": prior_route_ok,
        "target_query_executed": False,
        "list_http": list_resp.get("http"),
        "list_charset": list_enc,
        "detail_id_count": len(detail_ids),
        "detail_ids": detail_ids,
        "details": details,
        "file_call_count": len(all_calls),
        "file_calls": all_calls,
        "probe_count": len(probe_results),
        "probe_results": probe_results,
        "verified_binary_count": len(verified),
        "verified_binary_attachments": verified[:20],
        "detail_contract_observed": detail_contract_observed,
        "attachment_parameter_contract_verified": binary_verified,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "attachment_hit_equals_designation_notice": False,
            "attachment_hit_equals_current_validity": False,
            "attachment_hit_equals_site_inclusion": False,
            "attachment_no_hit_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "official_designation_identity_verified": False,
            "current_validity_verified": False,
            "site_spatial_inclusion_verified": False,
            "runtime_registration_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nLIST / DETAIL CONTRACT")
    print("-" * 78)
    print(f"LIST HTTP: {list_resp.get('http')}")
    print(f"DETAIL ID COUNT: {len(detail_ids)}")
    print(f"FILE CALL COUNT: {len(all_calls)}")
    for d in details[:10]:
        print(f"PSTSN={d['pstSn']} HTTP={d['http']} FILE_CALLS={d['file_call_count']} TITLE={d['title']}")
        for c in d["file_calls"][:6]:
            print(f"  {c['function']} ARGS={c['args']} RAW={c['raw']}")

    print("\nATTACHMENT PROBES")
    print("-" * 78)
    print(f"PROBE COUNT: {len(probe_results)}")
    print(f"VERIFIED BINARY COUNT: {len(verified)}")
    for i, p in enumerate(probe_results[:30], 1):
        c = p["content_class"]
        print(f"[{i:02d}] HTTP={p['http']} PDF={c['pdf_magic']} OLE={c['ole_magic']} ZIP={c['zip_magic']} BIN_CT={c['binary_content_type']}")
        print(f"     URL={p['url']}")
        print(f"     CT={p['content_type']}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"PRIOR ROUTE CONTRACT QUALIFIED: {prior_route_ok}")
    print(f"DETAIL CONTRACT OBSERVED: {detail_contract_observed}")
    print(f"ATTACHMENT PARAMETER CONTRACT VERIFIED: {binary_verified}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Target query executed: False")
    print("Attachment no-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S227A-R input exists": prior_exists,
        "target query not executed": out["target_query_executed"] is False,
        "classification emitted": classification in {
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ATTACHMENT_PARAMETER_CONTRACT_VERIFIED",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ATTACHMENT_PARAMETER_CONTRACT_OBSERVED_BINARY_TECHNICAL_UNKNOWN",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ATTACHMENT_PARAMETER_CONTRACT_TECHNICAL_UNKNOWN",
        },
        "attachment hit not designation notice": out["summary"]["attachment_hit_equals_designation_notice"] is False,
        "attachment hit not current validity": out["summary"]["attachment_hit_equals_current_validity"] is False,
        "attachment hit not site inclusion": out["summary"]["attachment_hit_equals_site_inclusion"] is False,
        "attachment no-hit not legal absence": out["summary"]["attachment_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for k, v in validation.items():
        print(f"{k}: {v}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT}")

    if not all(validation.values()):
        raise AssertionError("S227A-P validation failed")


if __name__ == "__main__":
    main()
