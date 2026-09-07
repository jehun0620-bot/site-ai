# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlencode

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
PRIOR_OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_exact_attachment_form_contract_reconstruction.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_attachment_ajax_schema_binary_replay.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE"
LIST_URL = "https://www.seongnam.go.kr/ct-bbs020101"
ATCH_URL = "https://www.seongnam.go.kr/ct-bbs020101/atchFileDetail"
GETFILE_URL = "https://www.seongnam.go.kr/ct-bbs020101/getFile"
BBS_CRT_SN = "19008"
MAX_DETAILS = 10
MAX_REPLAYS = 80

MOVE_RE = re.compile(r"fn_move_form\s*\(\s*['\"]?(\d+)['\"]?\s*\)", re.I)
ID_KEY_HINT_RE = re.compile(r"(?i)(file.*(?:no|sn|seq|id)|atch.*(?:no|sn|seq|id)|(?:no|sn|seq|id)$)")


def curl_request(url: str, *, referer: str | None = None) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"http": None, "final_url": None, "content_type": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "60",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-H", "Accept: application/json,text/plain,*/*",
        "-w", "\n__META__%{http_code}|%{url_effective}|%{content_type}",
    ]
    if referer:
        cmd += ["-e", referer]
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


def decode_text(body: bytes) -> str:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            return body.decode(enc)
        except UnicodeDecodeError:
            pass
    return body.decode("utf-8", errors="replace")


def extract_detail_ids(html: str) -> list[str]:
    out, seen = [], set()
    for m in MOVE_RE.finditer(html or ""):
        v = m.group(1)
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def parse_json_response(resp: dict) -> tuple[object | None, str | None]:
    text = decode_text(resp.get("body") or b"")
    try:
        return json.loads(text), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def extract_items(data: object) -> list[dict]:
    if isinstance(data, dict):
        if isinstance(data.get("atchFileVO"), list):
            return [x for x in data["atchFileVO"] if isinstance(x, dict)]
        for v in data.values():
            if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
                return list(v)
    if isinstance(data, list) and all(isinstance(x, dict) for x in data):
        return list(data)
    return []


def candidate_identifier_fields(item: dict) -> list[tuple[str, str]]:
    rows = []
    for k, v in item.items():
        if v is None:
            continue
        s = str(v)
        if not s:
            continue
        if ID_KEY_HINT_RE.search(k) or k in {"fileNo", "fileSn", "atchFileSn", "atchFileNo", "seq", "id"}:
            rows.append((k, s))
    return rows


def classify_binary(resp: dict) -> dict:
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


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY PLANNING DOCUMENT ATTACHMENT AJAX SCHEMA + BINARY REPLAY - S227A-P4")
    print("=" * 78)
    print("Purpose: read atchFileDetail JSON schema and replay getFile using server-returned identifiers only")
    print("UQQ700 target query: NOT EXECUTED")
    print("Attachment hit != designation notice")
    print("Attachment no-hit != legal absence")
    print("SITE FALSE inference: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    prior_exists = PRIOR_OUT.exists()
    prior = json.loads(PRIOR_OUT.read_text(encoding="utf-8")) if prior_exists else {}
    prior_context_ok = bool(prior.get("exact_context_observed"))

    lr = curl_request(LIST_URL)
    list_html = decode_text(lr.get("body") or b"")
    detail_ids = extract_detail_ids(list_html)[:MAX_DETAILS]

    ajax_rows = []
    replay_candidates = []
    schema_keys = set()
    successful_json = 0

    for pst_sn in detail_ids:
        detail_url = f"{LIST_URL}/{pst_sn}"
        ajax_url = ATCH_URL + "?" + urlencode({"pstSn": pst_sn})
        r = curl_request(ajax_url, referer=detail_url)
        data, err = parse_json_response(r)
        items = extract_items(data) if data is not None else []
        if data is not None:
            successful_json += 1
        item_rows = []
        for idx, item in enumerate(items):
            schema_keys.update(item.keys())
            ids = candidate_identifier_fields(item)
            item_rows.append({
                "index": idx,
                "keys": sorted(item.keys()),
                "item": item,
                "identifier_candidates": [{"key": k, "value": v} for k, v in ids],
            })
            for k, v in ids:
                replay_candidates.append({
                    "pstSn": pst_sn,
                    "detail_url": detail_url,
                    "identifier_key": k,
                    "identifier_value": v,
                    "source_item": item,
                })
        ajax_rows.append({
            "pstSn": pst_sn,
            "url": ajax_url,
            "http": r.get("http"),
            "content_type": r.get("content_type"),
            "json_ok": data is not None,
            "json_error": err,
            "top_type": type(data).__name__ if data is not None else None,
            "top_keys": sorted(data.keys()) if isinstance(data, dict) else None,
            "atch_file_count": len(items),
            "items": item_rows,
        })

    seen = set()
    replay_results = []
    verified = []
    for cand in replay_candidates:
        # The UI form calls the parameter fileNo. Replay only server-returned identifier values.
        params = {
            "bbsCrtSn": BBS_CRT_SN,
            "pstSn": cand["pstSn"],
            "fileNo": cand["identifier_value"],
        }
        url = GETFILE_URL + "?" + urlencode(params)
        key = (cand["pstSn"], cand["identifier_key"], cand["identifier_value"], url)
        if key in seen:
            continue
        seen.add(key)
        if len(replay_results) >= MAX_REPLAYS:
            break
        r = curl_request(url, referer=cand["detail_url"])
        cls = classify_binary(r)
        row = {
            "pstSn": cand["pstSn"],
            "identifier_key": cand["identifier_key"],
            "identifier_value": cand["identifier_value"],
            "url": url,
            "http": r.get("http"),
            "content_type": r.get("content_type"),
            "content_class": cls,
        }
        replay_results.append(row)
        if r.get("http") == "200" and (cls["pdf_magic"] or cls["ole_magic"] or cls["zip_magic"] or cls["binary_content_type"]):
            verified.append(row)

    ajax_contract_verified = successful_json > 0 and any(x["atch_file_count"] > 0 for x in ajax_rows)
    identifier_schema_observed = bool(replay_candidates)
    binary_verified = bool(verified)

    if prior_context_ok and ajax_contract_verified and identifier_schema_observed and binary_verified:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ATTACHMENT_AJAX_SCHEMA_AND_BINARY_CONTRACT_VERIFIED"
        semantic = "ATCHFILEDETAIL_JSON_SCHEMA_AND_SERVER_RETURNED_ATTACHMENT_IDENTIFIER_REPLAY_VERIFIED_REAL_BINARY_DOWNLOAD"
        next_action = "QUALIFY_PLANNING_ARCHIVE_COVERAGE_AND_ENUMERATE_CANONICAL_DOCUMENT_SET_BEFORE_UQQ700_CONTENT_SCAN"
    elif prior_context_ok and ajax_contract_verified and identifier_schema_observed:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ATTACHMENT_AJAX_IDENTIFIER_SCHEMA_VERIFIED_BINARY_TECHNICAL_UNKNOWN"
        semantic = "ATCHFILEDETAIL_JSON_AND_ATTACHMENT_IDENTIFIER_FIELDS_VERIFIED_BUT_GETFILE_BINARY_REPLAY_NOT_YET_VERIFIED"
        next_action = "MAP_THE_EXACT_IDENTIFIER_FIELD_USED_BY_UI_GETFILE_HANDLER_WITHOUT_NEGATIVE_INFERENCE"
    elif prior_context_ok and ajax_contract_verified:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ATTACHMENT_AJAX_SCHEMA_VERIFIED_IDENTIFIER_TECHNICAL_UNKNOWN"
        semantic = "ATCHFILEDETAIL_JSON_VERIFIED_BUT_EXACT_ATTACHMENT_IDENTIFIER_FIELD_NOT_YET_RESOLVED"
        next_action = "INSPECT_COMPLETE_ATCHFILEVO_SCHEMA_AND_INLINE_HANDLER_ARGUMENT_MAPPING_WITHOUT_NEGATIVE_INFERENCE"
    else:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ATTACHMENT_AJAX_CONTRACT_TECHNICAL_UNKNOWN"
        semantic = "ATCHFILEDETAIL_JSON_CONTRACT_NOT_YET_TECHNICALLY_VERIFIED"
        next_action = "HARDEN_AJAX_REQUEST_HEADERS_OR_RESPONSE_DECODING_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-147-S227A-P4",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "prior_input_exists": prior_exists,
        "prior_exact_context_observed": prior_context_ok,
        "target_query_executed": False,
        "list_http": lr.get("http"),
        "detail_ids": detail_ids,
        "ajax_successful_json_count": successful_json,
        "ajax_rows": ajax_rows,
        "schema_keys": sorted(schema_keys),
        "identifier_candidate_count": len(replay_candidates),
        "replay_count": len(replay_results),
        "replay_results": replay_results,
        "verified_binary_count": len(verified),
        "verified_binary_attachments": verified[:20],
        "ajax_contract_verified": ajax_contract_verified,
        "identifier_schema_observed": identifier_schema_observed,
        "binary_attachment_verified": binary_verified,
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

    print("\nATTACHMENT AJAX SCHEMA")
    print("-" * 78)
    print(f"LIST HTTP: {lr.get('http')}")
    print(f"DETAIL COUNT: {len(detail_ids)}")
    print(f"SUCCESSFUL JSON COUNT: {successful_json}")
    print(f"SCHEMA KEYS: {sorted(schema_keys)}")
    print(f"IDENTIFIER CANDIDATE COUNT: {len(replay_candidates)}")
    for row in ajax_rows:
        print(f"PSTSN={row['pstSn']} HTTP={row['http']} JSON={row['json_ok']} FILES={row['atch_file_count']}")
        for item in row["items"][:5]:
            print(f"  KEYS={item['keys']}")
            print(f"  IDS={item['identifier_candidates']}")
            print(f"  ITEM={item['item']}")

    print("\nBINARY REPLAY")
    print("-" * 78)
    print(f"REPLAY COUNT: {len(replay_results)}")
    print(f"VERIFIED BINARY COUNT: {len(verified)}")
    for i, row in enumerate(replay_results[:30], 1):
        c = row["content_class"]
        print(f"[{i:02d}] PSTSN={row['pstSn']} KEY={row['identifier_key']} VALUE={row['identifier_value']} HTTP={row['http']}")
        print(f"     PDF={c['pdf_magic']} OLE={c['ole_magic']} ZIP={c['zip_magic']} BIN_CT={c['binary_content_type']}")
        print(f"     CT={row['content_type']}")
        print(f"     URL={row['url']}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"PRIOR EXACT CONTEXT OBSERVED: {prior_context_ok}")
    print(f"ATTACHMENT AJAX CONTRACT VERIFIED: {ajax_contract_verified}")
    print(f"IDENTIFIER SCHEMA OBSERVED: {identifier_schema_observed}")
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
        "S227A-P3 input exists": prior_exists,
        "target query not executed": out["target_query_executed"] is False,
        "classification emitted": classification in {
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ATTACHMENT_AJAX_SCHEMA_AND_BINARY_CONTRACT_VERIFIED",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ATTACHMENT_AJAX_IDENTIFIER_SCHEMA_VERIFIED_BINARY_TECHNICAL_UNKNOWN",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ATTACHMENT_AJAX_SCHEMA_VERIFIED_IDENTIFIER_TECHNICAL_UNKNOWN",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ATTACHMENT_AJAX_CONTRACT_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S227A-P4 validation failed")


if __name__ == "__main__":
    main()
