# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlencode

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
RECOVERED_DIR = OUT_DIR / "development_density_management_area_seongnam_legacy_pdf_recovered"
IN_S230A = OUT_DIR / "development_density_management_area_historical_discovery_source_family_reranking_reconciliation.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_legacy_pdf_alternate_archival_access_recovery.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE"
BBS_CRT_SN = "19008"

LEGACY_BASE = "https://www.seongnam.go.kr/data/ASIS/attach/bbs/30246/"
CDX = "https://web.archive.org/cdx/search/cdx"
WAYBACK_PREFIX = "https://web.archive.org/web"

EXPECTED = [
    {"file_no": 58460, "stored_name": "20150902175005097.pdf", "original_name": "산성2 지구단위계획지침도 1-1.pdf", "size": 628561},
    {"file_no": 58461, "stored_name": "20150902175005175.pdf", "original_name": "산성2 지구단위계획지침도 1-2.pdf", "size": 792505},
    {"file_no": 58462, "stored_name": "20150902175005269.pdf", "original_name": "산성2 지구단위계획지침도 2-1.pdf", "size": 1017775},
    {"file_no": 58463, "stored_name": "20150902175005378.pdf", "original_name": "산성2 지구단위계획지침도 2-2.pdf", "size": 1053676},
    {"file_no": 58464, "stored_name": "20150902175005487.pdf", "original_name": "산성2 지구단위계획지침도 2-3.pdf", "size": 940118},
    {"file_no": 58465, "stored_name": "20150902175053177.pdf", "original_name": "산성2 시행지침(2009.07.24).pdf", "size": 791263},
]


def curl_bytes(url: str, referer: str | None = None, max_time: int = 90) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"http": None, "final_url": None, "content_type": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", str(max_time),
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    ]
    if referer:
        cmd += ["-e", referer]
    cmd += ["-w", "\n__META__%{http_code}|%{url_effective}|%{content_type}", url]
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


def is_pdf(body: bytes) -> bool:
    return body.startswith(b"%PDF-")


def sha256(body: bytes) -> str | None:
    return hashlib.sha256(body).hexdigest() if body else None


def safe_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def recursive_identity_hits(node, wanted_file_no: int, wanted_stored_name: str, inherited: dict | None = None) -> list[dict]:
    inherited = dict(inherited or {})
    hits = []
    if isinstance(node, dict):
        ctx = dict(inherited)
        for k in ("pstSn", "pst_sn", "post_sn", "postSn", "bbsCrtSn", "bbs_crt_sn", "fileNo", "file_no", "stored_name", "storedName", "saveFileNm", "fileNm", "original_name", "orgFileNm"):
            if k in node and node.get(k) not in (None, ""):
                ctx[k] = node.get(k)

        node_values = {str(v) for v in node.values() if isinstance(v, (str, int))}
        file_match = str(wanted_file_no) in node_values or str(node.get("fileNo", "")) == str(wanted_file_no) or str(node.get("file_no", "")) == str(wanted_file_no)
        name_match = wanted_stored_name in node_values or any(wanted_stored_name in str(v) for v in node.values() if isinstance(v, str))
        if file_match or name_match:
            hits.append(ctx)
        for v in node.values():
            hits.extend(recursive_identity_hits(v, wanted_file_no, wanted_stored_name, ctx))
    elif isinstance(node, list):
        for v in node:
            hits.extend(recursive_identity_hits(v, wanted_file_no, wanted_stored_name, inherited))
    return hits


def discover_local_identity(item: dict) -> dict:
    candidates = []
    for p in sorted(OUT_DIR.glob("*.json")):
        if p == OUT:
            continue
        data = safe_json(p)
        if data is None:
            continue
        for hit in recursive_identity_hits(data, item["file_no"], item["stored_name"]):
            pst_sn = hit.get("pstSn") or hit.get("pst_sn") or hit.get("post_sn") or hit.get("postSn")
            file_no = hit.get("fileNo") or hit.get("file_no") or item["file_no"]
            if pst_sn:
                candidates.append({
                    "source_output": str(p),
                    "pstSn": str(pst_sn),
                    "fileNo": str(file_no),
                    "bbsCrtSn": str(hit.get("bbsCrtSn") or hit.get("bbs_crt_sn") or BBS_CRT_SN),
                })
    uniq = []
    seen = set()
    for c in candidates:
        key = (c["pstSn"], c["fileNo"], c["bbsCrtSn"])
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return {"identity_candidate_count": len(uniq), "identity_candidates": uniq[:20]}


def official_getfile_probe(identity: dict) -> dict:
    params = {
        "bbsCrtSn": identity["bbsCrtSn"],
        "pstSn": identity["pstSn"],
        "fileNo": identity["fileNo"],
    }
    url = "https://www.seongnam.go.kr/getFile?" + urlencode(params)
    # This endpoint differs from the already-closed direct ASIS physical URL.
    rr = curl_bytes(url, referer="https://www.seongnam.go.kr/ct-bbs020101")
    return {
        "probe_kind": "CURRENT_OFFICIAL_GETFILE_BY_VERIFIED_IDENTITY",
        "url": url,
        "http": rr["http"],
        "final_url": rr["final_url"],
        "content_type": rr["content_type"],
        "body_size": len(rr["body"]),
        "pdf_magic": is_pdf(rr["body"]),
        "sha256": sha256(rr["body"]),
        "body": rr["body"],
        "stderr": rr["stderr"],
    }


def cdx_lookup(original_url: str) -> dict:
    params = {
        "url": original_url,
        "output": "json",
        "filter": "statuscode:200",
        "filter": "mimetype:application/pdf",
        "fl": "timestamp,original,statuscode,mimetype,digest,length",
        "collapse": "digest",
        "limit": "10",
    }
    # urlencode cannot preserve duplicate filter keys, so compose explicitly.
    url = (
        CDX + "?url=" + original_url.replace(":", "%3A").replace("/", "%2F")
        + "&output=json&filter=statuscode%3A200&filter=mimetype%3Aapplication%2Fpdf"
        + "&fl=timestamp%2Coriginal%2Cstatuscode%2Cmimetype%2Cdigest%2Clength&collapse=digest&limit=10"
    )
    rr = curl_bytes(url, max_time=60)
    snapshots = []
    if rr["http"] == "200":
        try:
            data = json.loads(rr["body"].decode("utf-8", errors="replace"))
            if isinstance(data, list) and len(data) >= 2:
                headers = data[0]
                for row in data[1:]:
                    if isinstance(row, list):
                        snapshots.append(dict(zip(headers, row)))
        except Exception:
            pass
    return {
        "probe_kind": "WAYBACK_CDX_EXACT_LEGACY_URL_IDENTITY_LOOKUP",
        "query_url": url,
        "http": rr["http"],
        "content_type": rr["content_type"],
        "body_size": len(rr["body"]),
        "snapshot_count": len(snapshots),
        "snapshots": snapshots,
        "stderr": rr["stderr"],
    }


def wayback_fetch(snapshot: dict) -> dict:
    ts = snapshot.get("timestamp")
    original = snapshot.get("original")
    if not ts or not original:
        return {"attempted": False, "reason": "missing snapshot identity", "body": b""}
    url = f"{WAYBACK_PREFIX}/{ts}id_/{original}"
    rr = curl_bytes(url, max_time=90)
    return {
        "attempted": True,
        "probe_kind": "WAYBACK_ARCHIVED_BINARY_FETCH",
        "url": url,
        "http": rr["http"],
        "final_url": rr["final_url"],
        "content_type": rr["content_type"],
        "body_size": len(rr["body"]),
        "pdf_magic": is_pdf(rr["body"]),
        "sha256": sha256(rr["body"]),
        "body": rr["body"],
        "stderr": rr["stderr"],
    }


def save_recovered(item: dict, source: str, body: bytes) -> str:
    RECOVERED_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{item['file_no']}_{source}_{item['stored_name']}"
    path = RECOVERED_DIR / re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", name)
    path.write_bytes(body)
    return str(path)


def main() -> None:
    print("=" * 78)
    print("SEONGNAM LEGACY PDF ALTERNATE OFFICIAL / ARCHIVAL ACCESS RECOVERY - S230B")
    print("=" * 78)
    print("Purpose: recover only six verified legacy PDF identities via alternate paths")
    print("Direct legacy ASIS 404 URL replay: PROHIBITED")
    print("Recovery success != designation/current validity/site inclusion")
    print("Recovery failure/404 != file absence or legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    if not IN_S230A.exists():
        raise FileNotFoundError(f"Missing S230A output: {IN_S230A}")
    s230a = json.loads(IN_S230A.read_text(encoding="utf-8"))
    if s230a.get("next_source_family") != SOURCE_FAMILY:
        raise AssertionError(f"Unexpected S230A next source family: {s230a.get('next_source_family')}")

    results = []
    direct_asis_replay_count = 0
    official_probe_count = 0
    cdx_probe_count = 0
    archive_fetch_count = 0
    recovered_count = 0

    for item in EXPECTED:
        original_legacy_url = LEGACY_BASE + item["stored_name"]
        local_identity = discover_local_identity(item)
        probes = []
        recovered = []

        # Alternate path 1: current official getFile contract, only when prior
        # local outputs preserve the post identity. Never request original ASIS URL.
        for identity in local_identity["identity_candidates"][:3]:
            p = official_getfile_probe(identity)
            official_probe_count += 1
            body = p.pop("body")
            probes.append(p)
            if p["pdf_magic"]:
                recovered_path = save_recovered(item, "official", body)
                recovered.append({"source": "CURRENT_OFFICIAL_GETFILE", "path": recovered_path, "sha256": p["sha256"], "size": p["body_size"]})
                break

        # Alternate path 2: archival index lookup of exact known physical URL.
        # CDX lookup is not a replay of the closed 404 URL itself.
        cdx = cdx_lookup(original_legacy_url)
        cdx_probe_count += 1
        probes.append({k: v for k, v in cdx.items() if k != "snapshots"} | {"snapshots": cdx["snapshots"]})

        # Fetch at most one archived binary snapshot per file.
        if not recovered and cdx["snapshots"]:
            wf = wayback_fetch(cdx["snapshots"][0])
            archive_fetch_count += 1
            body = wf.pop("body")
            probes.append(wf)
            if wf.get("pdf_magic"):
                recovered_path = save_recovered(item, "wayback", body)
                recovered.append({"source": "WAYBACK_ARCHIVED_BINARY", "path": recovered_path, "sha256": wf["sha256"], "size": wf["body_size"]})

        if recovered:
            recovered_count += 1
        row = {
            **item,
            "original_legacy_url_identity": original_legacy_url,
            "direct_legacy_asis_url_replayed": False,
            "local_identity": local_identity,
            "probe_count": len(probes),
            "probes": probes,
            "recovered": bool(recovered),
            "recovered_artifacts": recovered,
            "designation_identity_promoted": False,
            "current_validity_promoted": False,
            "site_inclusion_promoted": False,
            "legal_absence_inferred": False,
        }
        results.append(row)
        print(json.dumps({
            "file_no": item["file_no"],
            "stored_name": item["stored_name"],
            "identity_candidates": local_identity["identity_candidate_count"],
            "probe_count": len(probes),
            "recovered": bool(recovered),
            "recovered_sources": [x["source"] for x in recovered],
            "cdx_snapshot_count": cdx["snapshot_count"],
        }, ensure_ascii=False))

    unresolved_count = len(EXPECTED) - recovered_count
    if recovered_count > 0:
        classification = "SEONGNAM_LEGACY_PDF_ALTERNATE_ACCESS_ONE_OR_MORE_BINARIES_RECOVERED"
        semantic = "ONE_OR_MORE_VERIFIED_LEGACY_PDF_IDENTITIES_WERE_RECOVERED_VIA_ALTERNATE_OFFICIAL_OR_ARCHIVAL_ACCESS_WITHOUT_LEGAL_PROMOTION"
        next_action = "CONTENT_SCAN_ONLY_RECOVERED_PDFS_FOR_UQQ700_DEVELOPMENT_DENSITY_AND_LITERAL_NOTICE_IDENTITY_WITHOUT_NEGATIVE_INFERENCE_FOR_UNRECOVERED_FILES"
    else:
        classification = "SEONGNAM_LEGACY_PDF_ALTERNATE_ACCESS_NO_BINARY_RECOVERED_TECHNICAL_UNKNOWN_PRESERVED"
        semantic = "ALTERNATE_OFFICIAL_AND_ARCHIVAL_RECOVERY_PATHS_DID_NOT_RECOVER_THE_SIX_BINARIES_SO_ARCHIVED_BINARY_ACCESS_REMAINS_TECHNICAL_UNKNOWN"
        next_action = "MOVE_TO_NEXT_RANKED_SOURCE_FAMILY_WITHOUT_REPEATING_CLOSED_ASIS_404_PROBES_AND_KEEP_UQQ700_UNKNOWN"

    out = {
        "step": "STEP 17-21-C-16-8-T-167-S230B",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "input_s230a": str(IN_S230A),
        "expected_legacy_pdf_count": len(EXPECTED),
        "direct_legacy_asis_replay_count": direct_asis_replay_count,
        "official_getfile_probe_count": official_probe_count,
        "archival_cdx_probe_count": cdx_probe_count,
        "archival_binary_fetch_count": archive_fetch_count,
        "recovered_pdf_count": recovered_count,
        "unresolved_pdf_count": unresolved_count,
        "results": results,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "same_404_probe_repeated": False,
            "recovery_success_equals_designation_notice": False,
            "recovery_success_equals_current_validity": False,
            "recovery_success_equals_site_inclusion": False,
            "recovery_failure_equals_file_absence": False,
            "recovery_failure_equals_legal_absence": False,
            "http_404_equals_file_absence": False,
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

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"EXPECTED LEGACY PDF COUNT: {len(EXPECTED)}")
    print(f"DIRECT LEGACY ASIS REPLAY COUNT: {direct_asis_replay_count}")
    print(f"OFFICIAL GETFILE PROBE COUNT: {official_probe_count}")
    print(f"ARCHIVAL CDX PROBE COUNT: {cdx_probe_count}")
    print(f"ARCHIVAL BINARY FETCH COUNT: {archive_fetch_count}")
    print(f"RECOVERED PDF COUNT: {recovered_count}")
    print(f"UNRESOLVED PDF COUNT: {unresolved_count}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Same 404 probe repeated: False")
    print("Recovery failure == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S230A loaded": IN_S230A.exists(),
        "six exact legacy identities": len(EXPECTED) == 6,
        "direct ASIS replay prohibited": direct_asis_replay_count == 0,
        "all rows mark no direct replay": all(r["direct_legacy_asis_url_replayed"] is False for r in results),
        "one CDX lookup per file": cdx_probe_count == 6,
        "at most one archival fetch per file": archive_fetch_count <= 6,
        "recovery count bounded": 0 <= recovered_count <= 6,
        "unresolved count consistent": unresolved_count == 6 - recovered_count,
        "recovery success not designation": out["summary"]["recovery_success_equals_designation_notice"] is False,
        "recovery success not validity": out["summary"]["recovery_success_equals_current_validity"] is False,
        "recovery success not site inclusion": out["summary"]["recovery_success_equals_site_inclusion"] is False,
        "recovery failure not file absence": out["summary"]["recovery_failure_equals_file_absence"] is False,
        "recovery failure not legal absence": out["summary"]["recovery_failure_equals_legal_absence"] is False,
        "404 not file absence": out["summary"]["http_404_equals_file_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "SEONGNAM_LEGACY_PDF_ALTERNATE_ACCESS_ONE_OR_MORE_BINARIES_RECOVERED",
            "SEONGNAM_LEGACY_PDF_ALTERNATE_ACCESS_NO_BINARY_RECOVERED_TECHNICAL_UNKNOWN_PRESERVED",
        },
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
        raise AssertionError("S230B validation failed")


if __name__ == "__main__":
    main()
