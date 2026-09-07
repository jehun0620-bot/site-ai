# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import shutil
import subprocess
from html import unescape
from pathlib import Path
from urllib.parse import urlencode, urljoin

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
PRIOR_OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_attachment_markup_contract_forensic.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_exact_attachment_form_contract_reconstruction.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE"
LIST_URL = "https://www.seongnam.go.kr/ct-bbs020101"
GETFILE_URL = "https://www.seongnam.go.kr/ct-bbs020101/getFile"
PREVIEW_URL = "https://www.seongnam.go.kr/ct-bbs020101/filePreview"
MAX_DETAILS = 10
MAX_PROBES = 80

MOVE_RE = re.compile(r"fn_move_form\s*\(\s*['\"]?(\d+)['\"]?\s*\)", re.I)
TAG_RE = re.compile(r"(?is)<([A-Za-z0-9:_-]+)\b([^>]*)>")
FORM_RE = re.compile(r"(?is)<form\b([^>]*)>(.*?)</form>")
INPUT_RE = re.compile(r"(?is)<input\b([^>]*)>")
SCRIPT_RE = re.compile(r"(?is)<script\b[^>]*>(.*?)</script>")
FILE_NO_ASSIGN_PATTERNS = [
    re.compile(r"getFileFileNo['\"]?\s*\)\s*\.val\s*\(\s*['\"]?(\d+)['\"]?\s*\)", re.I),
    re.compile(r"getFileFileNo['\"]?\s*\)\s*\.value\s*=\s*['\"]?(\d+)['\"]?", re.I),
    re.compile(r"getElementById\s*\(\s*['\"]getFileFileNo['\"]\s*\)\.value\s*=\s*['\"]?(\d+)['\"]?", re.I),
    re.compile(r"fileNo\s*[=:]\s*['\"]?(\d+)['\"]?", re.I),
]
NUMERIC_ONCLICK_RE = re.compile(r"(?i)(?:getFile|download|filePreview|preview)[A-Za-z0-9_$]*\s*\((.*?)\)")
FILE_LABEL_RE = re.compile(r"(?i)([^<>\n\r]{0,120}\.(?:pdf|hwp|hwpx|xls|xlsx|doc|docx|zip))")


def curl_request(url: str, *, method: str = "GET", data: str | None = None, referer: str | None = None) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"http": None, "final_url": None, "content_type": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "60",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}|%{url_effective}|%{content_type}",
    ]
    if referer:
        cmd += ["-e", referer]
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


def decode_body(body: bytes) -> str:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            t = body.decode(enc)
            if enc == "utf-8" or "성남" in t:
                return t
        except UnicodeDecodeError:
            pass
    return body.decode("utf-8", errors="replace")


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def attrs(s: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r'''(?is)([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(["'])(.*?)\2''', s or ""):
        out[m.group(1).lower()] = unescape(m.group(3))
    return out


def extract_detail_ids(html: str) -> list[str]:
    out, seen = [], set()
    for m in MOVE_RE.finditer(html or ""):
        v = m.group(1)
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def find_exact_contexts(html: str) -> list[str]:
    contexts = []
    for token in ("getFileFileNo", "fileNo", "getFile", "filePreview"):
        for m in re.finditer(re.escape(token), html or "", re.I):
            contexts.append((html or "")[max(0, m.start()-700):m.end()+1400])
            if len(contexts) >= 40:
                return contexts
    return contexts


def extract_file_numbers(html: str) -> list[str]:
    vals, seen = [], set()
    for pat in FILE_NO_ASSIGN_PATTERNS:
        for m in pat.finditer(html or ""):
            v = m.group(1)
            if v not in seen:
                seen.add(v)
                vals.append(v)
    for m in NUMERIC_ONCLICK_RE.finditer(html or ""):
        for n in re.findall(r"\b\d+\b", m.group(1)):
            if n not in seen:
                seen.add(n)
                vals.append(n)
    return vals


def extract_candidate_elements(html: str) -> list[dict]:
    rows = []
    for m in TAG_RE.finditer(html or ""):
        a = attrs(m.group(2))
        blob = " ".join([m.group(1)] + [f"{k}={v}" for k, v in a.items()])
        if re.search(r"(?i)getFileFileNo|fileNo|getFile|filePreview|download|첨부", blob):
            rows.append({"tag": m.group(1), "attrs": a})
    return rows[:100]


def extract_forms(html: str, base_url: str) -> list[dict]:
    rows = []
    for fm in FORM_RE.finditer(html or ""):
        fa = attrs(fm.group(1))
        inputs = []
        relevant = False
        for im in INPUT_RE.finditer(fm.group(2)):
            ia = attrs(im.group(1))
            if ia.get("name"):
                inputs.append({
                    "name": ia.get("name"),
                    "id": ia.get("id"),
                    "type": ia.get("type", "text"),
                    "value": ia.get("value", ""),
                })
                if (ia.get("name") or "") in {"bbsCrtSn", "pstSn", "fileNo"} or ia.get("id") == "getFileFileNo":
                    relevant = True
        if relevant:
            rows.append({
                "id": fa.get("id"),
                "name": fa.get("name"),
                "method": (fa.get("method") or "GET").upper(),
                "action": urljoin(base_url, fa.get("action") or base_url),
                "inputs": inputs,
            })
    return rows


def extract_inline_script_hits(html: str) -> list[dict]:
    rows = []
    for sm in SCRIPT_RE.finditer(html or ""):
        script = sm.group(1)
        if re.search(r"(?i)getFileFileNo|fileNo|getFile|filePreview", script):
            rows.append({
                "file_numbers": extract_file_numbers(script),
                "script": script[:6000],
            })
    return rows[:20]


def classify(resp: dict) -> dict:
    body = resp.get("body") or b""
    ct = (resp.get("content_type") or "").lower()
    return {
        "pdf_magic": body.startswith(b"%PDF-"),
        "ole_magic": body.startswith(bytes.fromhex("D0CF11E0A1B11AE1")),
        "zip_magic": body.startswith(b"PK\x03\x04"),
        "binary_content_type": any(x in ct for x in (
            "application/pdf", "application/octet-stream", "haansofthwp", "application/zip", "officedocument"
        )),
        "html_content_type": "html" in ct,
        "body_size": len(body),
    }


def build_probes(pst_sn: str, file_no: str, referer: str) -> list[dict]:
    base = {"bbsCrtSn": "19008", "pstSn": pst_sn, "fileNo": file_no}
    probes = []
    for endpoint in (GETFILE_URL, PREVIEW_URL):
        probes.append({
            "method": "GET",
            "url": endpoint + "?" + urlencode(base),
            "data": None,
            "params": base,
            "referer": referer,
        })
        probes.append({
            "method": "POST",
            "url": endpoint,
            "data": urlencode(base),
            "params": base,
            "referer": referer,
        })
    return probes


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY PLANNING DOCUMENT EXACT ATTACHMENT FORM CONTRACT RECONSTRUCTION - S227A-P3")
    print("=" * 78)
    print("Purpose: reconstruct exact fileNo injection and submit contract around getFileFileNo")
    print("UQQ700 target query: NOT EXECUTED")
    print("Attachment hit != designation notice")
    print("Attachment no-hit != legal absence")
    print("SITE FALSE inference: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    prior_exists = PRIOR_OUT.exists()
    prior = json.loads(PRIOR_OUT.read_text(encoding="utf-8")) if prior_exists else {}
    prior_markup_observed = bool(prior.get("markup_contract_observed"))

    lr = curl_request(LIST_URL)
    list_html = decode_body(lr.get("body") or b"")
    detail_ids = extract_detail_ids(list_html)[:MAX_DETAILS]

    details = []
    all_numbers: list[tuple[str, str, str]] = []
    exact_context_observed = False
    for pst_sn in detail_ids:
        url = f"{LIST_URL}/{pst_sn}"
        r = curl_request(url)
        html = decode_body(r.get("body") or b"")
        contexts = find_exact_contexts(html) if r.get("http") == "200" else []
        forms = extract_forms(html, url) if r.get("http") == "200" else []
        elements = extract_candidate_elements(html) if r.get("http") == "200" else []
        scripts = extract_inline_script_hits(html) if r.get("http") == "200" else []
        file_numbers = extract_file_numbers("\n".join(contexts) + "\n" + "\n".join(x["script"] for x in scripts))
        labels = [clean_html(x) for x in FILE_LABEL_RE.findall(html or "")]
        if contexts or forms or elements or scripts:
            exact_context_observed = True
        for n in file_numbers:
            all_numbers.append((pst_sn, n, url))
        details.append({
            "pstSn": pst_sn,
            "url": url,
            "http": r.get("http"),
            "context_count": len(contexts),
            "contexts": [clean_html(x)[:2400] for x in contexts[:12]],
            "forms": forms,
            "candidate_elements": elements,
            "inline_script_hits": scripts,
            "file_numbers": file_numbers,
            "file_labels": labels[:30],
        })

    probes = []
    seen_probe = set()
    for pst_sn, file_no, referer in all_numbers:
        for p in build_probes(pst_sn, file_no, referer):
            key = (p["method"], p["url"], p.get("data"))
            if key not in seen_probe:
                seen_probe.add(key)
                probes.append(p)
    probes = probes[:MAX_PROBES]

    probe_results = []
    verified = []
    for p in probes:
        r = curl_request(p["url"], method=p["method"], data=p.get("data"), referer=p.get("referer"))
        cls = classify(r)
        row = {
            "method": p["method"],
            "url": p["url"],
            "data": p.get("data"),
            "params": p["params"],
            "referer": p.get("referer"),
            "http": r.get("http"),
            "final_url": r.get("final_url"),
            "content_type": r.get("content_type"),
            "content_class": cls,
        }
        probe_results.append(row)
        if r.get("http") == "200" and (cls["pdf_magic"] or cls["ole_magic"] or cls["zip_magic"] or cls["binary_content_type"]):
            verified.append(row)

    exact_file_number_observed = bool(all_numbers)
    binary_verified = bool(verified)

    if prior_markup_observed and exact_file_number_observed and binary_verified:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_EXACT_ATTACHMENT_FORM_CONTRACT_VERIFIED"
        semantic = "EXACT_FILENO_AND_BBS_POST_IDENTIFIERS_RECONSTRUCTED_AND_REAL_BINARY_ATTACHMENT_VERIFIED"
        next_action = "QUALIFY_ARCHIVE_COVERAGE_AND_ENUMERATE_CANONICAL_PLANNING_DOCUMENT_SET_BEFORE_UQQ700_CONTENT_SCAN"
    elif prior_markup_observed and exact_context_observed and exact_file_number_observed:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_EXACT_ATTACHMENT_IDENTIFIERS_OBSERVED_BINARY_TECHNICAL_UNKNOWN"
        semantic = "EXACT_ATTACHMENT_IDENTIFIERS_OBSERVED_BUT_BINARY_REQUEST_NOT_YET_VERIFIED"
        next_action = "HARDEN_ONLY_THE_OBSERVED_SUBMIT_METHOD_ACTION_OR_REQUIRED_FORM_STATE_WITHOUT_NEGATIVE_INFERENCE"
    elif prior_markup_observed and exact_context_observed:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_EXACT_ATTACHMENT_FORM_CONTEXT_OBSERVED_FILENO_TECHNICAL_UNKNOWN"
        semantic = "GETFILEFILENO_FORM_CONTEXT_VERIFIED_BUT_ACTUAL_FILENO_VALUE_NOT_YET_RECOVERED"
        next_action = "RECOVER_FILENO_SOURCE_FROM_ATTACHMENT_ROW_EVENT_OR_SERVER_RENDERED_IDENTIFIER_WITHOUT_NEGATIVE_INFERENCE"
    else:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_EXACT_ATTACHMENT_FORM_CONTRACT_TECHNICAL_UNKNOWN"
        semantic = "EXACT_ATTACHMENT_FORM_CONTEXT_NOT_YET_TECHNICALLY_RECONSTRUCTED"
        next_action = "EXPAND_VERIFIED_DETAIL_ATTACHMENT_ROW_FORENSICS_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-146-S227A-P3",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "prior_input_exists": prior_exists,
        "prior_markup_contract_observed": prior_markup_observed,
        "target_query_executed": False,
        "list_http": lr.get("http"),
        "detail_ids": detail_ids,
        "details": details,
        "exact_context_observed": exact_context_observed,
        "observed_file_number_count": len(all_numbers),
        "observed_file_numbers": [
            {"pstSn": pst_sn, "fileNo": file_no, "detail_url": detail_url}
            for pst_sn, file_no, detail_url in all_numbers[:100]
        ],
        "probe_count": len(probe_results),
        "probe_results": probe_results,
        "verified_binary_count": len(verified),
        "verified_binary_attachments": verified[:20],
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

    print("\nEXACT FORM CONTEXT")
    print("-" * 78)
    print(f"LIST HTTP: {lr.get('http')}")
    print(f"DETAIL COUNT: {len(details)}")
    print(f"EXACT CONTEXT OBSERVED: {exact_context_observed}")
    print(f"OBSERVED FILE NUMBER COUNT: {len(all_numbers)}")
    for d in details:
        print(f"PSTSN={d['pstSn']} HTTP={d['http']} CONTEXTS={d['context_count']} FILE_NOS={d['file_numbers']}")
        if d["forms"]:
            print(f"  FORM={d['forms'][0]}")
        if d["candidate_elements"]:
            print(f"  ELEMENT={d['candidate_elements'][0]}")
        if d["contexts"]:
            print(f"  CONTEXT={d['contexts'][0][:1400]}")

    print("\nBINARY PROBES")
    print("-" * 78)
    print(f"PROBE COUNT: {len(probe_results)}")
    print(f"VERIFIED BINARY COUNT: {len(verified)}")
    for i, p in enumerate(probe_results[:30], 1):
        c = p["content_class"]
        print(f"[{i:02d}] {p['method']} HTTP={p['http']} PDF={c['pdf_magic']} OLE={c['ole_magic']} ZIP={c['zip_magic']} BIN_CT={c['binary_content_type']}")
        print(f"     URL={p['url']}")
        if p.get("data"):
            print(f"     DATA={p['data']}")
        print(f"     CT={p['content_type']}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"PRIOR MARKUP CONTRACT OBSERVED: {prior_markup_observed}")
    print(f"EXACT CONTEXT OBSERVED: {exact_context_observed}")
    print(f"EXACT FILE NUMBER OBSERVED: {exact_file_number_observed}")
    print(f"BINARY ATTACHMENT VERIFIED: {binary_verified}")
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
        "S227A-P2 input exists": prior_exists,
        "target query not executed": out["target_query_executed"] is False,
        "classification emitted": classification in {
            "SEONGNAM_CITY_PLANNING_DOCUMENT_EXACT_ATTACHMENT_FORM_CONTRACT_VERIFIED",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_EXACT_ATTACHMENT_IDENTIFIERS_OBSERVED_BINARY_TECHNICAL_UNKNOWN",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_EXACT_ATTACHMENT_FORM_CONTEXT_OBSERVED_FILENO_TECHNICAL_UNKNOWN",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_EXACT_ATTACHMENT_FORM_CONTRACT_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S227A-P3 validation failed")


if __name__ == "__main__":
    main()
