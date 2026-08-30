# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S35
Probe a bounded neighborhood around Gazette 938 to distinguish:
- era-wide legacy preview failure, vs
- Gazette-938-specific attachment/conversion unavailability.

A neighboring row is considered a verified preview control only when:
metadata -> filePreview redirect -> module info XML HTTP 200.

No OCR, no state mutation, no legal promotion, no negative legal evidence.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
REGISTRY = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_historical_row_registry_recovery.json"
OUT = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_preview_legacy_neighborhood_control_probe.json"
BASE = "https://www.seongnam.go.kr"
BBS = "16002"
TIMEOUT = 20
TARGET_PST = "29098"
TARGET_GAZETTE = 938
NEIGHBOR_RADIUS = 4
MAX_ROWS = 1 + 2 * NEIGHBOR_RADIUS
MAX_REQUESTS = MAX_ROWS * 3
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


def js_params(url: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in urlsplit(url).query.split("&"):
        if not pair:
            continue
        k, _, v = pair.partition("=")
        out[k] = unquote(v)
    return out


def choose_attachment(text: str):
    found = []
    for m in re.finditer(r"fileNo[^0-9]{0,100}(\d+)", text or "", re.I):
        no = m.group(1)
        a = max(0, m.start() - 1200)
        b = min(len(text), m.end() + 1800)
        ctx = html.unescape(text[a:b])
        names = re.findall(r"([\w가-힣()\[\].,+\- _]+\.(?:hwpx|hwp))", ctx, re.I)
        name = names[-1].strip() if names else ""
        found.append({"fileNo": no, "name": name})
    for ext in (".hwp", ".hwpx"):
        for x in found:
            if x["name"].lower().endswith(ext):
                return x
    return found[0] if found else None


def main():
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("LEGACY PREVIEW NEIGHBORHOOD CONTROL PROBE")
    print("=" * 60)
    print("Target Gazette:", TARGET_GAZETTE, "pstSn", TARGET_PST)
    print("Neighborhood radius:", NEIGHBOR_RADIUS)
    print("OCR: DISABLED")
    print("State mutation: DISABLED")

    if not REGISTRY.exists():
        raise FileNotFoundError(REGISTRY)
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    rows = data.get("canonical_gazette_rows") or []
    if not rows:
        raise AssertionError("T-23 canonical_gazette_rows missing")

    idx = next((i for i, r in enumerate(rows) if str(r.get("pstSn") or "") == TARGET_PST), None)
    if idx is None:
        raise AssertionError("Gazette 938 pstSn not found in T-23 registry")

    lo = max(0, idx - NEIGHBOR_RADIUS)
    hi = min(len(rows), idx + NEIGHBOR_RADIUS + 1)
    sample = rows[lo:hi]

    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    reqs = 0
    results = []

    for row in sample:
        pst = str(row.get("pstSn") or "")
        gazette = row.get("gazette_number")
        date = row.get("date")
        is_target = pst == TARGET_PST
        print("\n--", "TARGET" if is_target else "NEIGHBOR", "Gazette", gazette, date, "pstSn", pst, "--")

        meta = s.get(
            f"{BASE}/bbs010308/atchFileDetail",
            params={"pstSn": pst},
            headers={"X-Requested-With": "XMLHttpRequest", "Referer": f"{BASE}/bbs010308/{pst}"},
            timeout=TIMEOUT,
        )
        reqs += 1
        att = choose_attachment(meta.text) if meta.status_code == 200 else None
        print("Metadata:", meta.status_code, "attachment:", att)
        item = {
            "gazette_number": gazette,
            "date": date,
            "pstSn": pst,
            "is_target_938": is_target,
            "metadata_status": meta.status_code,
            "attachment": att,
        }
        if not att:
            item["result"] = "NO_HWP_ATTACHMENT_RECOVERED"
            results.append(item)
            continue

        fp = s.get(
            f"{BASE}/bbs010308/filePreview",
            params={"bbsCrtSn": BBS, "pstSn": pst, "fileNo": att["fileNo"]},
            headers={"Referer": f"{BASE}/bbs010308/{pst}"},
            allow_redirects=False,
            timeout=TIMEOUT,
        )
        reqs += 1
        loc = fp.headers.get("Location", "")
        preview_url = urljoin(fp.url, loc) if loc else ""
        item["filePreview_status"] = fp.status_code
        item["preview_url"] = preview_url
        print("filePreview:", fp.status_code, "Location:", preview_url)
        if fp.status_code not in (301, 302, 303, 307, 308) or not preview_url:
            item["result"] = "NO_PREVIEW_REDIRECT"
            results.append(item)
            continue

        p = js_params(preview_url)
        fn = p.get("fn")
        rs = p.get("rs")
        info_url = urljoin(preview_url, rs.rstrip("/") + "/" + fn + ".xml") if fn and rs else ""
        item["runtime_fn"] = fn
        item["runtime_rs"] = rs
        item["info_url"] = info_url
        if not info_url:
            item["result"] = "NO_INFO_URL"
            results.append(item)
            continue

        info = s.get(
            info_url,
            headers={
                "Referer": preview_url,
                "Accept": "*/*",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
            },
            timeout=TIMEOUT,
        )
        reqs += 1
        ct = info.headers.get("Content-Type", "")
        looks_xml = "xml" in ct.lower() or info.text.lstrip().startswith("<")
        has_index = bool(re.search(r"<index\b|\"index\"\s*:", info.text[:200000], re.I))
        item.update({
            "info_status": info.status_code,
            "info_content_type": ct,
            "info_bytes": len(info.content),
            "looks_xml": looks_xml,
            "has_index_like_payload": has_index,
            "result": "VERIFIED_PREVIEW_CONTROL" if (not is_target and info.status_code == 200 and looks_xml) else ("TARGET_INFO_200" if is_target and info.status_code == 200 and looks_xml else "NOT_VERIFIED_CONTROL"),
        })
        print("Info XML:", info.status_code, "bytes:", len(info.content), "content-type:", ct, "index-like:", has_index)
        results.append(item)

        if reqs >= MAX_REQUESTS:
            break

    neighbors = [r for r in results if not r.get("is_target_938")]
    verified_neighbors = [r for r in neighbors if r.get("result") == "VERIFIED_PREVIEW_CONTROL"]
    target = next((r for r in results if r.get("is_target_938")), None)

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S35",
        "target": {"gazette_number": TARGET_GAZETTE, "pstSn": TARGET_PST},
        "sample_registry_index": idx,
        "sample_range": [lo, hi],
        "network_request_count": reqs,
        "results": results,
        "verified_neighbor_control_count": len(verified_neighbors),
        "target_result": target,
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "target located in registry": idx is not None,
        "bounded neighborhood respected": len(sample) <= MAX_ROWS,
        "request budget respected": reqs <= MAX_REQUESTS,
        "target evaluated": target is not None,
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nSUMMARY")
    print("Rows evaluated:", len(results))
    print("Requests:", reqs)
    print("Verified neighbor controls:", len(verified_neighbors))
    if verified_neighbors:
        for r in verified_neighbors:
            print("CONTROL:", r["gazette_number"], r["date"], "pstSn", r["pstSn"], "fn", repr(r.get("runtime_fn")))
    if target:
        print("TARGET 938 info status:", target.get("info_status"), "result:", target.get("result"), "fn", repr(target.get("runtime_fn")))
    print("Output:", OUT)

    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("legacy preview neighborhood control probe validation failed")


if __name__ == "__main__":
    main()
