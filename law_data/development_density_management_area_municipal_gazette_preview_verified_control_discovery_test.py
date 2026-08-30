# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S34
Discover a genuinely renderable municipal-gazette preview control.

S33 proved that module-mode info XML 403/404 terminates viewer load immediately.
Therefore Gazette 2087 cannot be treated as a known-good control merely because
filePreview redirects to the viewer shell.

This probe scans a small recent slice of the T-23 registry and requires an actual
HTTP 200 module info XML response before a row can become a preview control.
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
OUT = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_preview_verified_control_discovery.json"
BASE = "https://www.seongnam.go.kr"
BBS = "16002"
TIMEOUT = 20
MAX_ROWS = 10
MAX_REQUESTS = MAX_ROWS * 3
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


def js_params(url: str) -> dict[str, str]:
    out: dict[str, str] = {}
    q = urlsplit(url).query
    for pair in q.split("&"):
        if not pair:
            continue
        k, _, v = pair.partition("=")
        out[k] = unquote(v)  # JS decodeURIComponent semantics: '+' remains '+'
    return out


def choose_attachment(text: str):
    # Metadata fragment has varied schemas across eras. Recover fileNo + nearby HWP/HWPX name.
    found = []
    for m in re.finditer(r"fileNo[^0-9]{0,80}(\d+)", text or "", re.I):
        no = m.group(1)
        a = max(0, m.start() - 900)
        b = min(len(text), m.end() + 1400)
        ctx = html.unescape(text[a:b])
        names = re.findall(r"([\w가-힣()\[\].,+\- _]+\.(?:hwpx|hwp))", ctx, re.I)
        name = names[-1].strip() if names else ""
        found.append({"fileNo": no, "name": name})
    # Prefer HWPX, then HWP, then any recovered fileNo.
    for ext in (".hwpx", ".hwp"):
        for x in found:
            if x["name"].lower().endswith(ext):
                return x
    return found[0] if found else None


def main():
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("PREVIEW VERIFIED CONTROL DISCOVERY")
    print("=" * 60)
    print("Control criterion: module info XML HTTP 200")
    print("OCR: DISABLED")
    print("State mutation: DISABLED")

    if not REGISTRY.exists():
        raise FileNotFoundError(REGISTRY)
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    rows = data.get("canonical_gazette_rows") or []
    if not rows:
        raise AssertionError("T-23 canonical_gazette_rows missing")

    # Registry is already sorted newest-first by gazette number.
    sample = rows[:MAX_ROWS]
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})

    reqs = 0
    results = []
    verified = None

    for row in sample:
        pst = str(row.get("pstSn") or "")
        gazette = row.get("gazette_number")
        date = row.get("date")
        print("\n-- Gazette", gazette, date, "pstSn", pst, "--")

        meta = s.get(
            f"{BASE}/bbs010308/atchFileDetail",
            params={"pstSn": pst},
            headers={"X-Requested-With": "XMLHttpRequest", "Referer": f"{BASE}/bbs010308/{pst}"},
            timeout=TIMEOUT,
        )
        reqs += 1
        att = choose_attachment(meta.text) if meta.status_code == 200 else None
        print("Metadata:", meta.status_code, "attachment:", att)
        if not att:
            results.append({"gazette_number": gazette, "date": date, "pstSn": pst, "metadata_status": meta.status_code, "result": "NO_HWP_ATTACHMENT_RECOVERED"})
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
        print("filePreview:", fp.status_code, "Location:", preview_url)
        if fp.status_code not in (301, 302, 303, 307, 308) or not preview_url:
            results.append({"gazette_number": gazette, "date": date, "pstSn": pst, "attachment": att, "metadata_status": meta.status_code, "filePreview_status": fp.status_code, "result": "NO_PREVIEW_REDIRECT"})
            continue

        p = js_params(preview_url)
        fn = p.get("fn")
        rs = p.get("rs")
        info_url = urljoin(preview_url, rs.rstrip("/") + "/" + fn + ".xml") if fn and rs else ""
        if not info_url:
            results.append({"gazette_number": gazette, "date": date, "pstSn": pst, "attachment": att, "filePreview_status": fp.status_code, "preview_url": preview_url, "result": "NO_INFO_URL"})
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
        looks_xml = "xml" in (info.headers.get("Content-Type", "").lower()) or info.text.lstrip().startswith("<")
        has_index = bool(re.search(r"<index\b|\"index\"\s*:", info.text[:200000], re.I))
        print("Info XML:", info.status_code, "bytes:", len(info.content), "content-type:", info.headers.get("Content-Type", ""), "index-like:", has_index)

        item = {
            "gazette_number": gazette,
            "date": date,
            "pstSn": pst,
            "attachment": att,
            "metadata_status": meta.status_code,
            "filePreview_status": fp.status_code,
            "preview_url": preview_url,
            "runtime_fn": fn,
            "runtime_rs": rs,
            "info_url": info_url,
            "info_status": info.status_code,
            "info_content_type": info.headers.get("Content-Type", ""),
            "info_bytes": len(info.content),
            "looks_xml": looks_xml,
            "has_index_like_payload": has_index,
            "result": "VERIFIED_PREVIEW_CONTROL" if info.status_code == 200 and looks_xml else "NOT_VERIFIED_CONTROL",
        }
        results.append(item)
        if item["result"] == "VERIFIED_PREVIEW_CONTROL":
            verified = item
            print("VERIFIED CONTROL FOUND")
            break

        if reqs >= MAX_REQUESTS:
            break

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S34",
        "registry": str(REGISTRY),
        "sample_size": len(sample),
        "network_request_count": reqs,
        "results": results,
        "verified_control": verified,
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "registry loaded": bool(rows),
        "bounded recent sample": len(sample) <= MAX_ROWS,
        "request budget respected": reqs <= MAX_REQUESTS,
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nSUMMARY")
    print("Rows evaluated:", len(results))
    print("Requests:", reqs)
    print("Verified control found:", bool(verified))
    if verified:
        print("Control gazette:", verified["gazette_number"], verified["date"], "pstSn", verified["pstSn"])
        print("Control info URL:", verified["info_url"])
    else:
        print("Control result: NONE_IN_BOUNDED_RECENT_SAMPLE")
    print("Output:", OUT)

    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("preview verified-control discovery validation failed")


if __name__ == "__main__":
    main()
