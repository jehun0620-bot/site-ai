# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import shutil
import subprocess
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urlencode, urljoin, urlparse, urlunparse

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
S226H_OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_site_search_contract_discovery.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_positive_control_search_qualification.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_URBAN_PLANNING_COMMITTEE_RECORD"
OFFICIAL_HOST = "www.seongnam.go.kr"
SEARCH_URL = "https://www.seongnam.go.kr/search/search.jsp"
POSITIVE_CONTROL_TITLE = "2025년 제6회 성남시 도시계획위원회 개최 결과"
ADJACENT_TITLES = (
    "2025년 제5회 성남시 도시계획위원회 개최 결과",
    POSITIVE_CONTROL_TITLE,
    "2025년 제7회 성남시 도시계획위원회 개최 결과",
)
LEGACY_IDX = "374215"
LEGACY_PATH_SIGNAL = "/city/1000557/30229/"
MAX_PROBES = 8
MAX_RESULT_LINKS = 50
MAX_DETAIL_FETCH = 12


def curl_bytes(url: str, *, method: str = "GET", data: str | None = None) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"ok": False, "http": None, "final_url": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "45",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}|%{url_effective}",
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


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", "", unescape(s or "")).lower()


def extract_title(html: str) -> str | None:
    m = re.search(r"(?is)<title\b[^>]*>(.*?)</title>", html or "")
    return clean_html(m.group(1))[:500] if m else None


def extract_forms(html: str, base_url: str) -> list[dict]:
    out = []
    for fm in re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", html or ""):
        attrs, inner = fm.group(1), fm.group(2)
        action_m = re.search(r'''(?is)action\s*=\s*(["'])(.*?)\1''', attrs)
        method_m = re.search(r'''(?is)method\s*=\s*(["'])(.*?)\1''', attrs)
        action = urljoin(base_url, unescape(action_m.group(2).strip())) if action_m else base_url
        method = (method_m.group(2).strip().upper() if method_m else "GET")
        inputs = []
        for im in re.finditer(r"(?is)<(?:input|select|textarea)\b([^>]*)>", inner):
            ia = im.group(1)
            name_m = re.search(r'''(?is)name\s*=\s*(["'])(.*?)\1''', ia)
            value_m = re.search(r'''(?is)value\s*=\s*(["'])(.*?)\1''', ia)
            typ_m = re.search(r'''(?is)type\s*=\s*(["'])(.*?)\1''', ia)
            if name_m:
                inputs.append({
                    "name": unescape(name_m.group(2).strip()),
                    "value": unescape(value_m.group(2)) if value_m else "",
                    "type": typ_m.group(2).lower() if typ_m else "",
                })
        out.append({"action": action, "method": method, "inputs": inputs, "text": clean_html(inner)[:2000]})
    return out


def extract_links(html: str, base_url: str) -> list[dict]:
    out = []
    seen = set()
    for m in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", html or ""):
        attrs, inner = m.group(1), m.group(2)
        href_m = re.search(r'''(?is)href\s*=\s*(["'])(.*?)\1''', attrs)
        href = unescape(href_m.group(2).strip()) if href_m else ""
        if not href or href.lower().startswith(("javascript:", "#", "mailto:", "tel:")):
            continue
        absolute = urljoin(base_url, href)
        if urlparse(absolute).hostname != OFFICIAL_HOST:
            continue
        text = clean_html(inner)[:1000]
        key = (absolute, text)
        if key in seen:
            continue
        seen.add(key)
        out.append({"href": absolute, "text": text})
    return out


def select_query_names(forms: list[dict], html: str) -> list[str]:
    names = []
    preferred = ("query", "searchText", "keyword", "searchKeyword", "qt", "q", "searchWord", "searchTerm", "srchText")
    for form in forms:
        for inp in form["inputs"]:
            n = inp["name"]
            low = n.lower()
            if any(tok in low for tok in ("query", "search", "keyword", "srch", "qt")) and n not in names:
                names.append(n)
    for n in preferred:
        if re.search(fr"(?i)\b{re.escape(n)}\b", html or "") and n not in names:
            names.append(n)
    for n in preferred:
        if n not in names:
            names.append(n)
    return names[:MAX_PROBES]


def build_probes(forms: list[dict], html: str) -> list[dict]:
    probes = []
    seen = set()
    query_names = select_query_names(forms, html)

    for form in forms:
        if urlparse(form["action"]).hostname != OFFICIAL_HOST:
            continue
        if "/search" not in urlparse(form["action"]).path.lower():
            continue
        fields = {i["name"]: i["value"] for i in form["inputs"] if i["name"]}
        qnames = [n for n in query_names if n in fields]
        for qn in qnames[:2]:
            payload = dict(fields)
            payload[qn] = POSITIVE_CONTROL_TITLE
            key = (form["method"], form["action"], tuple(sorted(payload.items())))
            if key in seen:
                continue
            seen.add(key)
            probes.append({"source": "form", "method": form["method"], "url": form["action"], "params": payload, "query_name": qn})

    for qn in query_names:
        params = {qn: POSITIVE_CONTROL_TITLE}
        key = ("GET", SEARCH_URL, tuple(sorted(params.items())))
        if key in seen:
            continue
        seen.add(key)
        probes.append({"source": "fallback", "method": "GET", "url": SEARCH_URL, "params": params, "query_name": qn})
        if len(probes) >= MAX_PROBES:
            break
    return probes[:MAX_PROBES]


def execute_probe(probe: dict) -> dict:
    method = probe["method"].upper()
    if method == "POST":
        f = curl_bytes(probe["url"], method="POST", data=urlencode(probe["params"]))
        request_url = probe["url"]
    else:
        parts = list(urlparse(probe["url"]))
        existing = parse_qs(parts[4], keep_blank_values=True)
        for k, v in probe["params"].items():
            existing[k] = [v]
        parts[4] = urlencode([(k, vv) for k, vals in existing.items() for vv in vals])
        request_url = urlunparse(parts)
        f = curl_bytes(request_url)
    html, enc = decode_body(f.pop("body"))
    text = clean_html(html)
    links = extract_links(html, f.get("final_url") or request_url)
    ntext = normalize_text(text)
    exact = POSITIVE_CONTROL_TITLE in text or normalize_text(POSITIVE_CONTROL_TITLE) in ntext
    adjacent = [t for t in ADJACENT_TITLES if t in text or normalize_text(t) in ntext]
    legacy_idx_hit = LEGACY_IDX in html or LEGACY_IDX in text
    legacy_path_hit = LEGACY_PATH_SIGNAL in html
    city_plan_hits = [t for t in ("도시계획위원회", "도시계획과") if t in text]
    result_links = []
    for row in links:
        blob = f"{row['text']} {row['href']}"
        if (
            "도시계획위원회" in blob
            or LEGACY_IDX in blob
            or LEGACY_PATH_SIGNAL in blob
            or re.search(r"/bbs\d+(?:/\d+)?", urlparse(row["href"]).path)
        ):
            result_links.append(row)
    return {
        **probe,
        **f,
        "request_url": request_url,
        "selected_charset": enc,
        "title": extract_title(html),
        "exact_positive_control_hit": exact,
        "adjacent_title_hits": adjacent,
        "legacy_idx_hit": legacy_idx_hit,
        "legacy_path_hit": legacy_path_hit,
        "city_planning_signal_hits": city_plan_hits,
        "result_link_count": len(result_links),
        "result_links": result_links[:MAX_RESULT_LINKS],
        "body_prefix": text[:4000],
    }


def inspect_detail(url: str, expected_link_text: str = "") -> dict:
    f = curl_bytes(url)
    html, enc = decode_body(f.pop("body"))
    text = clean_html(html)
    ntext = normalize_text(text)
    exact = POSITIVE_CONTROL_TITLE in text or normalize_text(POSITIVE_CONTROL_TITLE) in ntext
    adjacent = [t for t in ADJACENT_TITLES if t in text or normalize_text(t) in ntext]
    city_plan_hits = [t for t in ("도시계획위원회", "도시계획과") if t in text]
    return {
        "url": url,
        "expected_link_text": expected_link_text,
        **f,
        "selected_charset": enc,
        "title": extract_title(html),
        "exact_positive_control_hit": exact,
        "adjacent_title_hits": adjacent,
        "legacy_idx_hit": LEGACY_IDX in html or LEGACY_IDX in text,
        "legacy_path_hit": LEGACY_PATH_SIGNAL in html,
        "city_planning_signal_hits": city_plan_hits,
        "current_bbs_route": bool(re.search(r"/bbs\d+(?:/\d+)?", urlparse(f.get("final_url") or url).path)),
        "body_prefix": text[:4000],
    }


def main() -> None:
    print("=" * 78)
    print("SEONGNAM URBAN PLANNING COMMITTEE POSITIVE-CONTROL SEARCH QUALIFICATION - S226I")
    print("=" * 78)
    print("Purpose: qualify the recovered official search contract with one verified committee positive-control title")
    print(f"Positive control: {POSITIVE_CONTROL_TITLE}")
    print("UQQ700 target query: NOT EXECUTED")
    print("Committee hit != designation notice")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    h = curl_bytes(SEARCH_URL)
    html, enc = decode_body(h.pop("body"))
    forms = extract_forms(html, h.get("final_url") or SEARCH_URL)
    probes = build_probes(forms, html)
    results = [execute_probe(p) for p in probes]

    positive_results = [r for r in results if r.get("ok") and r.get("http") == "200" and r.get("exact_positive_control_hit")]
    linked_urls = []
    seen = set()
    for r in results:
        for link in r.get("result_links") or []:
            u = link["href"]
            if u not in seen:
                seen.add(u)
                linked_urls.append((u, link.get("text") or ""))
    details = [inspect_detail(u, txt) for u, txt in linked_urls[:MAX_DETAIL_FETCH]]

    identity_details = [
        d for d in details
        if d.get("ok") and d.get("http") == "200" and d.get("exact_positive_control_hit") and "도시계획위원회" in (d.get("city_planning_signal_hits") or [])
    ]
    current_successors = [d for d in identity_details if d.get("current_bbs_route")]
    legacy_linked = [d for d in details if d.get("legacy_idx_hit") or d.get("legacy_path_hit")]
    adjacent_hits = sorted({t for r in results for t in (r.get("adjacent_title_hits") or [])})

    if identity_details:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_POSITIVE_CONTROL_SEARCH_CONTRACT_QUALIFIED"
        semantic = "OFFICIAL_SEARCH_RESULT_AND_COMMITTEE_DETAIL_IDENTITY_CONSISTENCY_VERIFIED_WITH_POSITIVE_CONTROL_ONLY"
        if current_successors:
            next_action = "QUALIFY_RECOVERED_COMMITTEE_BOARD_HISTORICAL_COVERAGE_BEFORE_UQQ700_QUERY"
        else:
            next_action = "RECOVER_COMMITTEE_BOARD_CONTAINER_FROM_VERIFIED_DETAIL_IDENTITY_BEFORE_UQQ700_QUERY"
    elif positive_results:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_POSITIVE_CONTROL_SEARCH_HIT_DETAIL_IDENTITY_UNRESOLVED"
        semantic = "OFFICIAL_SEARCH_POSITIVE_CONTROL_HIT_OBSERVED_BUT_DETAIL_IDENTITY_OR_ROUTE_LINKAGE_REMAINS_UNRESOLVED"
        next_action = "HARDEN_SEARCH_RESULT_LINK_EXTRACTION_AND_DETAIL_IDENTITY_WITHOUT_UQQ700_QUERY"
    elif any(r.get("ok") and r.get("http") == "200" for r in results):
        classification = "SEONGNAM_OFFICIAL_SEARCH_CONTRACT_REPLAYED_POSITIVE_CONTROL_NOT_RESOLVED"
        semantic = "OFFICIAL_SEARCH_CONTRACT_REPLAYED_WITH_POSITIVE_CONTROL_ONLY_BUT_MATCHER_OR_PARAMETER_CONTRACT_REMAINS_UNRESOLVED"
        next_action = "RECOVER_EXACT_SEARCH_PARAMETER_CONTRACT_FROM_SEARCH_PAGE_SCRIPT_WITHOUT_UQQ700_QUERY"
    else:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_POSITIVE_CONTROL_SEARCH_TECHNICAL_UNKNOWN"
        semantic = "POSITIVE_CONTROL_SEARCH_QUALIFICATION_NOT_TECHNICALLY_RESOLVED"
        next_action = "RECHECK_OFFICIAL_SEARCH_TRANSPORT_AND_PARAMETER_CONTRACT_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-141-S226I",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "s226h_input_exists": S226H_OUT.exists(),
        "search_url": SEARCH_URL,
        "positive_control_title": POSITIVE_CONTROL_TITLE,
        "search_surface_http": h.get("http"),
        "search_surface_final_url": h.get("final_url"),
        "search_surface_charset": enc,
        "search_form_count": len(forms),
        "search_forms": forms,
        "probe_count": len(probes),
        "probe_results": results,
        "positive_result_count": len(positive_results),
        "linked_result_url_count": len(linked_urls),
        "detail_fetch_count": len(details),
        "detail_results": details,
        "verified_identity_detail_count": len(identity_details),
        "current_successor_count": len(current_successors),
        "legacy_linked_detail_count": len(legacy_linked),
        "adjacent_title_hits": adjacent_hits,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "positive_control_query_executed": True,
            "target_query_executed": False,
            "committee_hit_equals_designation_notice": False,
            "search_no_hit_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
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

    print(f"S226H INPUT EXISTS: {S226H_OUT.exists()}")
    print(f"SEARCH SURFACE HTTP: {h.get('http')}")
    print(f"SEARCH SURFACE FINAL URL: {h.get('final_url')}")
    print(f"SEARCH FORM COUNT: {len(forms)}")
    for i, form in enumerate(forms, 1):
        print(f"FORM [{i:02d}] METHOD={form['method']} ACTION={form['action']} INPUTS={[x['name'] for x in form['inputs']]}")

    print("\nPROBE RESULTS")
    print("-" * 78)
    for i, r in enumerate(results, 1):
        print(f"PROBE [{i:02d}] source={r['source']} method={r['method']} query_name={r['query_name']}")
        print(f"  REQUEST URL: {r.get('request_url')}")
        print(f"  HTTP: {r.get('http')}")
        print(f"  FINAL URL: {r.get('final_url')}")
        print(f"  EXACT CONTROL HIT: {r.get('exact_positive_control_hit')}")
        print(f"  ADJACENT TITLE HITS: {r.get('adjacent_title_hits')}")
        print(f"  LEGACY IDX HIT: {r.get('legacy_idx_hit')}")
        print(f"  LEGACY PATH HIT: {r.get('legacy_path_hit')}")
        print(f"  CITY PLANNING SIGNALS: {r.get('city_planning_signal_hits')}")
        print(f"  RESULT LINK COUNT: {r.get('result_link_count')}")
        for j, link in enumerate((r.get('result_links') or [])[:10], 1):
            print(f"    LINK [{j:02d}] {link['href']} | {link['text']}")

    print("\nDETAIL IDENTITY CHECKS")
    print("-" * 78)
    for i, d in enumerate(details, 1):
        print(f"DETAIL [{i:02d}] {d['url']}")
        print(f"  HTTP: {d.get('http')}")
        print(f"  FINAL URL: {d.get('final_url')}")
        print(f"  TITLE: {d.get('title')}")
        print(f"  EXACT CONTROL HIT: {d.get('exact_positive_control_hit')}")
        print(f"  CURRENT BBS ROUTE: {d.get('current_bbs_route')}")
        print(f"  LEGACY IDX HIT: {d.get('legacy_idx_hit')}")
        print(f"  LEGACY PATH HIT: {d.get('legacy_path_hit')}")
        print(f"  CITY PLANNING SIGNALS: {d.get('city_planning_signal_hits')}")

    print("\n" + "=" * 78)
    print("POSITIVE-CONTROL QUALIFICATION SUMMARY")
    print("=" * 78)
    print(f"PROBE COUNT: {len(results)}")
    print(f"POSITIVE RESULT COUNT: {len(positive_results)}")
    print(f"LINKED RESULT URL COUNT: {len(linked_urls)}")
    print(f"DETAIL FETCH COUNT: {len(details)}")
    print(f"VERIFIED IDENTITY DETAIL COUNT: {len(identity_details)}")
    print(f"CURRENT SUCCESSOR COUNT: {len(current_successors)}")
    print(f"LEGACY-LINKED DETAIL COUNT: {len(legacy_linked)}")
    print(f"ADJACENT TITLE HITS: {adjacent_hits}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Positive-control query executed: True")
    print("Target query executed: False")
    print("Legal absence inference allowed: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S226H input exists": out["s226h_input_exists"] is True,
        "positive control identity fixed": out["positive_control_title"] == POSITIVE_CONTROL_TITLE,
        "classification emitted": classification in {
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_POSITIVE_CONTROL_SEARCH_CONTRACT_QUALIFIED",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_POSITIVE_CONTROL_SEARCH_HIT_DETAIL_IDENTITY_UNRESOLVED",
            "SEONGNAM_OFFICIAL_SEARCH_CONTRACT_REPLAYED_POSITIVE_CONTROL_NOT_RESOLVED",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_POSITIVE_CONTROL_SEARCH_TECHNICAL_UNKNOWN",
        },
        "positive control query executed": out["summary"]["positive_control_query_executed"] is True,
        "target query not executed": out["summary"]["target_query_executed"] is False,
        "committee hit not designation notice": out["summary"]["committee_hit_equals_designation_notice"] is False,
        "search no-hit not legal absence": out["summary"]["search_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
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
        raise AssertionError("S226I validation failed")


if __name__ == "__main__":
    main()
