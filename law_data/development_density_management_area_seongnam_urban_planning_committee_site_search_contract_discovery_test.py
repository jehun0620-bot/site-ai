# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import shutil
import subprocess
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_site_search_contract_discovery.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_URBAN_PLANNING_COMMITTEE_RECORD"
OFFICIAL_HOST = "www.seongnam.go.kr"
ROOT_URLS = (
    "https://www.seongnam.go.kr/",
    "https://www.seongnam.go.kr/index",
)
SEARCH_TERMS = (
    "search",
    "검색",
    "통합검색",
    "totalSearch",
    "totalsearch",
    "search.do",
    "search.json",
    "search.ajax",
    "menu",
    "sitemap",
)
MAX_SCRIPT_FETCH = 20
MAX_PASSIVE_PROBES = 12


def curl_bytes(url: str) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"ok": False, "http": None, "final_url": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS",
        "--connect-timeout", "15", "--max-time", "45",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}|%{url_effective}",
        url,
    ]
    p = subprocess.run(cmd, capture_output=True)
    raw = p.stdout or b""
    marker = b"\n__META__"
    if marker in raw:
        body, meta = raw.rsplit(marker, 1)
        parts = meta.decode("utf-8", errors="replace").strip().split("|", 1)
        http = parts[0] if parts else None
        final_url = parts[1] if len(parts) > 1 else None
    else:
        body, http, final_url = raw, None, None
    return {
        "ok": p.returncode == 0 and bool(http and http != "000"),
        "returncode": p.returncode,
        "http": http,
        "final_url": final_url,
        "body": body,
        "stderr": (p.stderr or b"").decode("utf-8", errors="replace").strip(),
    }


def decode_body(body: bytes) -> tuple[str, str]:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            text = body.decode(enc)
            if enc == "utf-8" or "성남" in text:
                return text, enc
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", errors="replace"), "utf-8-replace"


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def extract_title(html: str) -> str | None:
    m = re.search(r"(?is)<title\b[^>]*>(.*?)</title>", html or "")
    return clean_html(m.group(1))[:500] if m else None


def extract_forms(html: str, base_url: str) -> list[dict]:
    out = []
    for m in re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", html or ""):
        attrs, inner = m.group(1), m.group(2)
        action_m = re.search(r'''(?is)action\s*=\s*(["'])(.*?)\1''', attrs)
        method_m = re.search(r'''(?is)method\s*=\s*(["'])(.*?)\1''', attrs)
        action = unescape(action_m.group(2).strip()) if action_m else ""
        method = method_m.group(2).strip().upper() if method_m else "GET"
        action_abs = urljoin(base_url, action) if action else base_url
        inputs = []
        for im in re.finditer(r"(?is)<input\b([^>]*)>", inner):
            ia = im.group(1)
            name_m = re.search(r'''(?is)name\s*=\s*(["'])(.*?)\1''', ia)
            type_m = re.search(r'''(?is)type\s*=\s*(["'])(.*?)\1''', ia)
            value_m = re.search(r'''(?is)value\s*=\s*(["'])(.*?)\1''', ia)
            if name_m:
                inputs.append({
                    "name": unescape(name_m.group(2).strip()),
                    "type": type_m.group(2).strip().lower() if type_m else None,
                    "value": unescape(value_m.group(2).strip()) if value_m else None,
                })
        text = clean_html(inner)[:1500]
        blob = (action_abs + " " + text + " " + " ".join(i["name"] for i in inputs)).lower()
        search_signal = any(t.lower() in blob for t in SEARCH_TERMS)
        out.append({
            "action": action_abs,
            "method": method,
            "inputs": inputs,
            "text": text,
            "search_signal": search_signal,
            "same_official_host": urlparse(action_abs).hostname == OFFICIAL_HOST,
        })
    return out


def extract_scripts(html: str, base_url: str) -> tuple[list[str], list[str]]:
    external = []
    inline = []
    for m in re.finditer(r"(?is)<script\b([^>]*)>(.*?)</script>", html or ""):
        attrs, body = m.group(1), m.group(2)
        src_m = re.search(r'''(?is)src\s*=\s*(["'])(.*?)\1''', attrs)
        if src_m:
            src = urljoin(base_url, unescape(src_m.group(2).strip()))
            if urlparse(src).hostname == OFFICIAL_HOST and src not in external:
                external.append(src)
        elif body.strip():
            inline.append(body)
    return external, inline


def extract_contract_literals(text: str, base_url: str) -> list[dict]:
    out = {}
    pats = [
        r'''(?i)(https?://www\.seongnam\.go\.kr/[^"'<>\s)]+)''',
        r'''(?i)(/[A-Za-z0-9_./?-]*(?:search|totalSearch|totalsearch|sitemap|menu)[A-Za-z0-9_./?=&%-]*)''',
    ]
    for pat in pats:
        for hit in re.findall(pat, text or ""):
            u = urljoin(base_url, unescape(hit))
            if urlparse(u).hostname != OFFICIAL_HOST:
                continue
            low = u.lower()
            signals = [t for t in SEARCH_TERMS if t.lower() in low]
            if signals:
                out[u] = {"url": u, "signals": signals}
    return sorted(out.values(), key=lambda x: x["url"])


def inspect_surface(label: str, url: str) -> dict:
    f = curl_bytes(url)
    html, enc = decode_body(f.pop("body"))
    final_url = f.get("final_url") or url
    forms = extract_forms(html, final_url)
    scripts, inline = extract_scripts(html, final_url)
    literals = extract_contract_literals(html, final_url)
    return {
        "label": label,
        "url": url,
        **f,
        "selected_charset": enc,
        "same_official_host": bool(final_url and urlparse(final_url).hostname == OFFICIAL_HOST),
        "title": extract_title(html),
        "form_count": len(forms),
        "forms": forms,
        "search_form_count": sum(1 for x in forms if x["search_signal"]),
        "same_host_script_count": len(scripts),
        "script_urls": scripts,
        "inline_script_count": len(inline),
        "contract_literal_count": len(literals),
        "contract_literals": literals,
        "html_prefix": clean_html(html)[:2500],
        "_inline_scripts": inline,
    }


def passive_probe(url: str) -> dict:
    f = curl_bytes(url)
    body, enc = decode_body(f.pop("body"))
    text = clean_html(body)
    return {
        "url": url,
        **f,
        "selected_charset": enc,
        "title": extract_title(body),
        "same_official_host": bool(f.get("final_url") and urlparse(f["final_url"]).hostname == OFFICIAL_HOST),
        "search_surface_signal": any(t in text for t in ("통합검색", "검색결과", "검색어", "상세검색")),
        "body_prefix": text[:2000],
    }


def main() -> None:
    print("=" * 78)
    print("SEONGNAM OFFICIAL SITE SEARCH CONTRACT DISCOVERY - S226H")
    print("=" * 78)
    print("Purpose: recover current official search form/action/API contract before any committee or UQQ700 query")
    print("Committee search query: NOT EXECUTED")
    print("UQQ700 target query: NOT EXECUTED")
    print("Generic /search 404 from S226G: DIAGNOSTIC_ONLY")
    print("Negative evidence: DISABLED")
    print("Source closure: BLOCKED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    surfaces = [inspect_surface(f"root_{i}", u) for i, u in enumerate(ROOT_URLS, 1)]

    script_results = []
    script_urls = []
    for s in surfaces:
        for u in s.get("script_urls") or []:
            if u not in script_urls:
                script_urls.append(u)
    for u in script_urls[:MAX_SCRIPT_FETCH]:
        f = curl_bytes(u)
        text, enc = decode_body(f.pop("body"))
        literals = extract_contract_literals(text, u)
        script_results.append({
            "url": u,
            **f,
            "selected_charset": enc,
            "contract_literal_count": len(literals),
            "contract_literals": literals,
            "search_term_hits": [t for t in SEARCH_TERMS if t.lower() in text.lower()],
        })

    candidate_urls = {}
    for s in surfaces:
        for form in s.get("forms") or []:
            if form.get("search_signal") and form.get("same_official_host"):
                candidate_urls[form["action"]] = {"source": "form_action", "url": form["action"]}
        for lit in s.get("contract_literals") or []:
            candidate_urls[lit["url"]] = {"source": "html_literal", "url": lit["url"]}
    for r in script_results:
        for lit in r.get("contract_literals") or []:
            candidate_urls[lit["url"]] = {"source": "script_literal", "url": lit["url"]}

    # Passive qualification only: GET discovered surface without search terms.
    probes = []
    for row in list(candidate_urls.values())[:MAX_PASSIVE_PROBES]:
        probes.append({"source": row["source"], **passive_probe(row["url"])})

    qualified_forms = []
    for s in surfaces:
        for form in s.get("forms") or []:
            if form.get("search_signal") and form.get("same_official_host"):
                qualified_forms.append({"surface": s["url"], **form})

    qualified_probe_urls = [
        p for p in probes
        if p.get("ok") and p.get("http") == "200" and p.get("same_official_host") and p.get("search_surface_signal")
    ]

    if qualified_forms or qualified_probe_urls:
        classification = "SEONGNAM_OFFICIAL_SITE_SEARCH_CONTRACT_QUALIFIED"
        semantic = "CURRENT_SEONGNAM_OFFICIAL_SEARCH_CONTRACT_RECOVERED_WITHOUT_SUBMITTING_TARGET_QUERY"
        next_action = "QUALIFY_SEARCH_CONTRACT_WITH_POSITIVE_CONTROL_COMMITTEE_TITLE_ONLY_BEFORE_UQQ700_QUERY"
    elif candidate_urls and any(s.get("ok") for s in surfaces):
        classification = "SEONGNAM_OFFICIAL_SITE_SEARCH_SURFACE_DISCOVERED_CONTRACT_UNRESOLVED"
        semantic = "SEARCH_RELATED_OFFICIAL_SURFACE_DISCOVERED_BUT_EXECUTABLE_CONTRACT_NOT_YET_QUALIFIED"
        next_action = "REFINE_DISCOVERED_SEARCH_ENDPOINT_PARAMETERS_WITHOUT_COMMITTEE_OR_UQQ700_QUERY"
    else:
        classification = "SEONGNAM_OFFICIAL_SITE_SEARCH_CONTRACT_TECHNICAL_UNKNOWN"
        semantic = "CURRENT_SEONGNAM_OFFICIAL_SEARCH_CONTRACT_NOT_RECOVERED_FROM_ROOT_INDEX_OR_SCRIPTS"
        next_action = "EXPAND_OFFICIAL_MENU_SITEMAP_AND_SCRIPT_DISCOVERY_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-141-S226H",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "surface_count": len(surfaces),
        "surfaces": [{k: v for k, v in s.items() if k != "_inline_scripts"} for s in surfaces],
        "script_fetch_count": len(script_results),
        "script_results": script_results,
        "candidate_contract_count": len(candidate_urls),
        "candidate_contracts": list(candidate_urls.values()),
        "passive_probe_count": len(probes),
        "passive_probes": probes,
        "qualified_search_form_count": len(qualified_forms),
        "qualified_search_forms": qualified_forms,
        "qualified_passive_probe_count": len(qualified_probe_urls),
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "committee_query_executed": False,
            "target_query_executed": False,
            "generic_search_404_negative_evidence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "source_closure_allowed": False,
            "official_designation_identity_verified": False,
            "current_validity_verified": False,
            "site_spatial_inclusion_verified": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "runtime_registration_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    for s in surfaces:
        print("-" * 78)
        print(f"[{s['label']}] {s['url']}")
        print(f"HTTP: {s.get('http')}")
        print(f"FINAL URL: {s.get('final_url')}")
        print(f"TITLE: {s.get('title')}")
        print(f"FORM COUNT: {s.get('form_count')}")
        print(f"SEARCH FORM COUNT: {s.get('search_form_count')}")
        for i, form in enumerate(s.get('forms') or [], 1):
            if form.get('search_signal'):
                print(f"  SEARCH FORM [{i:02d}] METHOD={form['method']} ACTION={form['action']} INPUTS={[x['name'] for x in form['inputs']]}")
        print(f"SAME-HOST SCRIPT COUNT: {s.get('same_host_script_count')}")
        print(f"CONTRACT LITERAL COUNT: {s.get('contract_literal_count')}")

    print("\nSCRIPT CONTRACT DISCOVERY")
    print("-" * 78)
    for r in script_results:
        if r.get("contract_literal_count") or r.get("search_term_hits"):
            print(f"SCRIPT {r['url']} | HTTP={r.get('http')} | SEARCH TERMS={r.get('search_term_hits')} | CONTRACTS={r.get('contract_literal_count')}")
            for lit in r.get("contract_literals") or []:
                print(f"  CONTRACT {lit['url']} | SIGNALS={lit['signals']}")

    print("\nPASSIVE CONTRACT PROBES")
    print("-" * 78)
    for p in probes:
        print(f"{p['source']} | {p['url']} | HTTP={p.get('http')} | FINAL={p.get('final_url')} | SEARCH SURFACE={p.get('search_surface_signal')} | TITLE={p.get('title')}")

    print("\n" + "=" * 78)
    print("SEARCH CONTRACT SUMMARY")
    print("=" * 78)
    print(f"CANDIDATE CONTRACT COUNT: {len(candidate_urls)}")
    print(f"PASSIVE PROBE COUNT: {len(probes)}")
    print(f"QUALIFIED SEARCH FORM COUNT: {len(qualified_forms)}")
    print(f"QUALIFIED PASSIVE PROBE COUNT: {len(qualified_probe_urls)}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Committee query executed: False")
    print("Target query executed: False")
    print("Generic /search 404 used as negative evidence: False")
    print("Legal absence inference allowed: False")
    print("SITE FALSE inference allowed: False")
    print("Source closure allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "classification emitted": classification in {
            "SEONGNAM_OFFICIAL_SITE_SEARCH_CONTRACT_QUALIFIED",
            "SEONGNAM_OFFICIAL_SITE_SEARCH_SURFACE_DISCOVERED_CONTRACT_UNRESOLVED",
            "SEONGNAM_OFFICIAL_SITE_SEARCH_CONTRACT_TECHNICAL_UNKNOWN",
        },
        "committee query not executed": out["summary"]["committee_query_executed"] is False,
        "target query not executed": out["summary"]["target_query_executed"] is False,
        "generic search 404 not negative evidence": out["summary"]["generic_search_404_negative_evidence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "source closure blocked": out["summary"]["source_closure_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "SITE promotion blocked": out["summary"]["site_positive_allowed"] is False and out["summary"]["site_negative_allowed"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for key, value in validation.items():
        print(f"{key}: {value}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT}")

    if not all(validation.values()):
        raise AssertionError("S226H validation failed")


if __name__ == "__main__":
    main()
