# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S30
Probe exact empty-query ('?') wire semantics used by viewer ajaxCall/setQueryString.

The official viewer always transforms a URL with no query into URL+'?' even
when extraParam is empty. Compare ordinary requests behavior with an explicit
raw HTTPS request preserving the trailing '?', for both Gazette 938 and modern
Gazette 2087 controls.

No OCR, no cumulative state mutation, no legal promotion.
"""
from __future__ import annotations

import http.client
import json
import re
from pathlib import Path
from urllib.parse import quote, unquote, urlparse, urlsplit

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_preview_empty_query_wire_probe.json"

BASE = "https://www.seongnam.go.kr"
HOST = "www.seongnam.go.kr"
BBS = "16002"
TIMEOUT = 20
MAX_REQUESTS = 10
TARGETS = [
    {"label": "LEGACY_938", "pstSn": "29098", "known_fileNo": "28559"},
    {"label": "MODERN_2087", "pstSn": "404960", "known_fileNo": None},
]


def js_params(url: str) -> dict[str, str]:
    q = urlsplit(url).query
    out = {}
    for pair in q.split("&"):
        if not pair:
            continue
        a = pair.split("=", 1)
        out[a[0]] = unquote(a[1] if len(a) > 1 else "")
    return out


def choose_attachment(html: str, known: str | None):
    candidates = []
    for m in re.finditer(r"fileNo[^0-9]{0,40}(\d+)", html, re.I):
        no = m.group(1)
        a = max(0, m.start() - 500)
        b = min(len(html), m.end() + 900)
        ctx = html[a:b]
        names = re.findall(r"([\w가-힣().\-+ ]+\.(?:hwpx|hwp))", ctx, re.I)
        candidates.append((no, names[-1].strip() if names else None))
    if known:
        for no, name in candidates:
            if no == known:
                return {"fileNo": no, "name": name}
        return {"fileNo": known, "name": None}
    for no, name in candidates:
        if name and name.lower().endswith((".hwpx", ".hwp")):
            return {"fileNo": no, "name": name}
    return None


def cookie_header(session: requests.Session) -> str:
    return "; ".join(f"{k}={v}" for k, v in session.cookies.get_dict().items())


def raw_get_path(path_with_query: str, referer: str, cookies: str) -> dict:
    conn = http.client.HTTPSConnection(HOST, timeout=TIMEOUT)
    headers = {
        "Host": HOST,
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Referer": referer,
        "Connection": "close",
    }
    if cookies:
        headers["Cookie"] = cookies
    conn.request("GET", path_with_query, headers=headers)
    resp = conn.getresponse()
    body = resp.read()
    result = {
        "status": resp.status,
        "reason": resp.reason,
        "content_type": resp.getheader("Content-Type") or "",
        "bytes": len(body),
        "request_target": path_with_query,
    }
    conn.close()
    return result


def encode_path(path: str) -> str:
    return quote(path, safe="/()+-._~")


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("PREVIEW EMPTY-QUERY WIRE PROBE")
    print("=" * 60)
    print("OCR: DISABLED")
    print("State mutation: DISABLED")

    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0", "Accept-Language": "ko-KR,ko;q=0.9"})
    request_count = 0
    rows = []

    for target in TARGETS:
        print("\n--", target["label"], "--")
        d = s.get(f"{BASE}/bbs010308/{target['pstSn']}", timeout=TIMEOUT)
        request_count += 1
        m = s.get(
            f"{BASE}/bbs010308/atchFileDetail",
            params={"pstSn": target["pstSn"]},
            headers={"X-Requested-With": "XMLHttpRequest", "Referer": d.url},
            timeout=TIMEOUT,
        )
        request_count += 1
        att = choose_attachment(m.text, target["known_fileNo"])
        if not att:
            rows.append({"target": target, "error": "NO_HWP_ATTACHMENT"})
            print("Attachment: NONE")
            continue

        p = s.get(
            f"{BASE}/bbs010308/filePreview",
            params={"bbsCrtSn": BBS, "pstSn": target["pstSn"], "fileNo": att["fileNo"]},
            headers={"Referer": d.url},
            allow_redirects=True,
            timeout=TIMEOUT,
        )
        request_count += 1
        pars = js_params(p.url)
        fn = pars.get("fn")
        rs = pars.get("rs")
        print("Preview:", p.status_code, p.url)
        print("Runtime fn:", repr(fn))
        print("Runtime rs:", repr(rs))

        row = {"target": target, "attachment": att, "preview_url": p.url, "runtime_fn": fn, "runtime_rs": rs}
        if not fn or not rs:
            row["error"] = "MISSING_RUNTIME_PARAMS"
            rows.append(row)
            continue

        path = rs.rstrip("/") + "/" + fn + ".xml"
        encoded = encode_path(path)

        normal = s.get(BASE + path, headers={"Referer": p.url}, timeout=TIMEOUT)
        request_count += 1
        print("Requests GET status:", normal.status_code)
        print("Requests prepared URL:", normal.request.url)

        raw = raw_get_path(encoded + "?", p.url, cookie_header(s))
        request_count += 1
        print("RAW trailing-? status:", raw["status"])
        print("RAW request target:", raw["request_target"])
        print("RAW Content-Type:", raw["content_type"], "Bytes:", raw["bytes"])

        row["normal"] = {
            "status": normal.status_code,
            "prepared_url": normal.request.url,
            "content_type": normal.headers.get("Content-Type", ""),
            "bytes": len(normal.content),
        }
        row["raw_trailing_empty_query"] = raw
        rows.append(row)

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S30",
        "rows": rows,
        "network_request_count": request_count,
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "request budget respected": request_count <= MAX_REQUESTS,
        "both targets evaluated": len(rows) == 2,
        "both raw probes attempted": all("raw_trailing_empty_query" in r for r in rows),
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nSUMMARY")
    print("Requests:", request_count)
    for row in rows:
        print(
            row["target"]["label"],
            "normal=", (row.get("normal") or {}).get("status"),
            "raw?=", (row.get("raw_trailing_empty_query") or {}).get("status"),
        )
    print("Output:", OUT)
    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("preview empty-query wire probe validation failed")


if __name__ == "__main__":
    main()
