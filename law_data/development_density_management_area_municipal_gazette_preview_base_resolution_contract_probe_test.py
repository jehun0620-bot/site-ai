# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S31
Resolve the browser URL base used by the official preview shell.

For legacy Gazette 938 and modern Gazette 2087:
- replay detail -> metadata -> filePreview
- inspect final preview document URL and HTML <base href>
- resolve config.js, lib.js, newviewer.js exactly as a browser would
- fetch config.js and extract localSynap/config/contextPath/proxy/host/base clues
- compute the absolute info XML URL via urllib.parse.urljoin(preview_or_base, rs/fn.xml)

This is a contract/forensics probe only. It does not treat 404 as legal evidence.
No OCR, no state mutation, no legal promotion.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_preview_base_resolution_contract_probe.json"
BASE = "https://www.seongnam.go.kr"
BBS = "16002"
TIMEOUT = 20
MAX_REQUESTS = 10
TARGETS = [
    {"label": "LEGACY_938", "pstSn": "29098", "known_fileNo": "28559"},
    {"label": "MODERN_2087", "pstSn": "404960", "known_fileNo": None},
]


def js_params(url: str) -> dict[str, str]:
    out = {}
    q = urlsplit(url).query
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


def first_base_href(html: str):
    m = re.search(r"<base\b[^>]*href\s*=\s*['\"]([^'\"]+)['\"]", html, re.I)
    return m.group(1) if m else None


def script_srcs(html: str):
    return re.findall(r"<script\b[^>]*src\s*=\s*['\"]([^'\"]+)['\"]", html, re.I)


def focused_config(text: str):
    pats = [r"localSynap", r"contextPath", r"proxy", r"host", r"base", r"result", r"attach", r"PST"]
    rows = []
    for pat in pats:
        for m in re.finditer(pat, text, re.I):
            a = max(0, m.start() - 500)
            b = min(len(text), m.end() + 1100)
            s = re.sub(r"\s+", " ", text[a:b]).strip()
            if s not in rows:
                rows.append(s[:3500])
            if len(rows) >= 16:
                return rows
    return rows


def main():
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("PREVIEW BASE RESOLUTION CONTRACT PROBE")
    print("=" * 60)
    print("OCR: DISABLED")
    print("State mutation: DISABLED")

    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0", "Accept-Language": "ko-KR,ko;q=0.9"})
    reqs = 0
    rows = []

    for t in TARGETS:
        print("\n--", t["label"], "--")
        d = s.get(f"{BASE}/bbs010308/{t['pstSn']}", timeout=TIMEOUT); reqs += 1
        m = s.get(f"{BASE}/bbs010308/atchFileDetail", params={"pstSn": t["pstSn"]}, headers={"X-Requested-With": "XMLHttpRequest", "Referer": d.url}, timeout=TIMEOUT); reqs += 1
        att = choose_attachment(m.text, t["known_fileNo"])
        if not att:
            rows.append({"target": t, "error": "NO_ATTACHMENT"})
            continue
        p = s.get(f"{BASE}/bbs010308/filePreview", params={"bbsCrtSn": BBS, "pstSn": t["pstSn"], "fileNo": att["fileNo"]}, headers={"Referer": d.url}, allow_redirects=True, timeout=TIMEOUT); reqs += 1

        base_href = first_base_href(p.text)
        effective_base = urljoin(p.url, base_href) if base_href else p.url
        scripts = script_srcs(p.text)
        resolved_scripts = [urljoin(effective_base, x) for x in scripts]
        config_url = next((u for u in resolved_scripts if u.endswith("/config.js") or u.endswith("config.js")), None)
        config = None
        config_ctx = []
        if config_url:
            c = s.get(config_url, headers={"Referer": p.url}, timeout=TIMEOUT); reqs += 1
            config = {"status": c.status_code, "url": c.url, "content_type": c.headers.get("Content-Type", ""), "bytes": len(c.content)}
            config_ctx = focused_config(c.text)

        pars = js_params(p.url)
        fn = pars.get("fn")
        rs = pars.get("rs")
        relative_info = (rs.rstrip("/") + "/" + fn + ".xml") if fn and rs else None
        browser_resolved_info = urljoin(effective_base, relative_info) if relative_info else None

        print("Preview URL:", p.url)
        print("Base href:", repr(base_href))
        print("Effective base:", effective_base)
        print("Script srcs:", scripts)
        print("Resolved config:", config_url)
        print("Runtime fn:", repr(fn))
        print("Runtime rs:", repr(rs))
        print("Browser-resolved info URL:", browser_resolved_info)
        print("CONFIG FOCUSED CONTEXTS")
        for i, x in enumerate(config_ctx, 1):
            print(f"[{i}] {x}")

        rows.append({
            "target": t,
            "attachment": att,
            "preview_status": p.status_code,
            "preview_url": p.url,
            "base_href": base_href,
            "effective_base": effective_base,
            "script_srcs": scripts,
            "resolved_scripts": resolved_scripts,
            "config": config,
            "config_contexts": config_ctx,
            "runtime_fn": fn,
            "runtime_rs": rs,
            "relative_info": relative_info,
            "browser_resolved_info_url": browser_resolved_info,
        })

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S31",
        "rows": rows,
        "network_request_count": reqs,
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "request budget respected": reqs <= MAX_REQUESTS,
        "both targets evaluated": len(rows) == 2,
        "both previews succeeded": all(r.get("preview_status") == 200 for r in rows),
        "browser info URLs resolved": all(bool(r.get("browser_resolved_info_url")) for r in rows),
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nSUMMARY")
    print("Requests:", reqs)
    for r in rows:
        print(r["target"]["label"], "base=", repr(r.get("base_href")), "info=", r.get("browser_resolved_info_url"))
    print("Output:", OUT)
    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("preview base resolution contract validation failed")


if __name__ == "__main__":
    main()
