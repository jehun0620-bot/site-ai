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
S226K_OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_board_list_contract_hardening.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_pagination_historical_coverage_reconstruction.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_URBAN_PLANNING_COMMITTEE_RECORD"
OFFICIAL_HOST = "www.seongnam.go.kr"
BOARD_BASE = "https://www.seongnam.go.kr/ct-bbs020102"
VERIFIED_DETAIL = f"{BOARD_BASE}/374215"
MAX_PAGE = 12
MAX_DETAIL_SAMPLE = 24

SEARCHISH = re.compile(r"(?i)(query|search|srch|keyword|find|sch)")
PAGEISH = re.compile(r"(?i)(page|paging|currentPage|pageIndex|pageNo|cPage|startCount|recordCountPerPage)")
DATE_RE = re.compile(r"\b(20\d{2})[-./](\d{1,2})[-./](\d{1,2})\b")
DETAIL_PATH_RE = re.compile(r"^/ct-bbs020102/(\d+)$")


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


def attr_map(attrs: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r'''(?is)([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(["'])(.*?)\2''', attrs or ""):
        out[m.group(1).lower()] = unescape(m.group(3))
    return out


def extract_title(html: str) -> str | None:
    m = re.search(r"(?is)<title\b[^>]*>(.*?)</title>", html or "")
    return clean_html(m.group(1))[:500] if m else None


def extract_search_form(html: str, base_url: str) -> dict | None:
    for fm in re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", html or ""):
        attrs, inner = fm.group(1), fm.group(2)
        amap = attr_map(attrs)
        if (amap.get("id") or "") != "searchVO" and (amap.get("name") or "") != "searchVO":
            continue
        controls = []
        for im in re.finditer(r"(?is)<(?:input|select|textarea)\b([^>]*)>", inner):
            cmap = attr_map(im.group(1))
            if not cmap.get("name"):
                continue
            controls.append({"name": cmap["name"], "value": cmap.get("value", ""), "id": cmap.get("id"), "type": cmap.get("type")})
        return {
            "action": urljoin(base_url, amap.get("action") or base_url),
            "method": (amap.get("method") or "GET").upper(),
            "controls": controls,
        }
    return None


def extract_inline_scripts(html: str) -> list[str]:
    out = []
    for m in re.finditer(r"(?is)<script\b([^>]*)>(.*?)</script>", html or ""):
        if "src=" not in m.group(1).lower() and m.group(2).strip():
            out.append(m.group(2))
    return out


def extract_function_body(script: str, name: str) -> str | None:
    m = re.search(rf"(?is)function\s+{re.escape(name)}\s*\((.*?)\)\s*\{{", script)
    if not m:
        return None
    start = m.end()
    depth = 1
    i = start
    quote = None
    esc = False
    while i < len(script):
        ch = script[i]
        if quote:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                quote = None
        else:
            if ch in ("'", '"', "`"):
                quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return script[m.start(): i + 1]
        i += 1
    return None


def infer_page_contract(function_texts: dict[str, str]) -> dict:
    candidates = []
    for fname, text in function_texts.items():
        for pat in (
            r'''(?:\[\s*["']([^"']+)["']\s*\]|\.([A-Za-z_$][\w$]*))\s*\.value\s*=\s*([A-Za-z_$][\w$]*|\d+)''',
            r'''(?:getElementById|querySelector)\s*\(\s*["']#?([^"']+)["']\s*\).*?\.value\s*=\s*([A-Za-z_$][\w$]*|\d+)''',
            r'''(?:name|id)\s*=\s*["']([^"']*(?:page|Page|PAGE)[^"']*)["']''',
        ):
            for m in re.finditer(pat, text):
                groups = [g for g in m.groups() if g]
                field = groups[0] if groups else None
                value_expr = groups[-1] if len(groups) > 1 else None
                if field and PAGEISH.search(field):
                    candidates.append({"function": fname, "field": field, "value_expr": value_expr, "evidence": m.group(0)[:300]})
        for m in re.finditer(r'''(?is)([A-Za-z_$][\w$]*)\s*=\s*arguments\[(\d+)\]''', text):
            if PAGEISH.search(m.group(1)):
                candidates.append({"function": fname, "field": m.group(1), "value_expr": f"arguments[{m.group(2)}]", "evidence": m.group(0)})
    dedup = []
    seen = set()
    for c in candidates:
        key = (c["function"], c["field"], c.get("value_expr"))
        if key not in seen:
            seen.add(key)
            dedup.append(c)
    return {"candidates": dedup}


def extract_rows(html: str, base_url: str) -> list[dict]:
    rows = []
    seen = set()
    # Prefer DOM fragments that contain current-board detail routes.
    for m in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", html or ""):
        amap = attr_map(m.group(1))
        href = amap.get("href") or ""
        if not href or href.lower().startswith(("javascript:", "#")):
            continue
        absolute = urljoin(base_url, href)
        p = urlparse(absolute)
        if p.hostname != OFFICIAL_HOST:
            continue
        dm = DETAIL_PATH_RE.fullmatch(p.path)
        if not dm:
            continue
        pst_sn = dm.group(1)
        title = clean_html(m.group(2))
        # Capture a bounded surrounding row/container for date extraction only.
        s = max(0, m.start() - 1200)
        e = min(len(html), m.end() + 1200)
        context = clean_html(html[s:e])
        dates = []
        for y, mo, d in DATE_RE.findall(context):
            val = f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
            if val not in dates:
                dates.append(val)
        key = pst_sn
        if key in seen:
            continue
        seen.add(key)
        rows.append({"pstSn": pst_sn, "url": absolute, "title": title, "row_dates": dates, "context": context[:2200]})
    return rows


def build_default_payload(form: dict) -> dict:
    payload = {}
    for c in form.get("controls") or []:
        name = c["name"]
        value = c.get("value") or ""
        if SEARCHISH.search(name):
            value = ""
        if TARGET in value or "도시계획위원회" in value:
            value = ""
        payload[name] = value
    return payload


def candidate_page_fields(form: dict, inferred: dict) -> list[str]:
    fields = []
    for c in inferred.get("candidates") or []:
        if c["field"] not in fields:
            fields.append(c["field"])
    for c in form.get("controls") or []:
        if PAGEISH.search(c["name"]) and c["name"] not in fields:
            fields.append(c["name"])
    # Conservative fallback names, only if function parsing did not recover an explicit field.
    if not fields:
        fields = ["pageIndex", "page", "currentPage", "pageNo"]
    return fields[:6]


def replay_page(form: dict, field: str, page_no: int) -> dict:
    payload = build_default_payload(form)
    payload[field] = str(page_no)
    if form["method"] == "POST":
        f = curl_bytes(form["action"], method="POST", data=urlencode(payload, doseq=True))
    else:
        q = urlencode(payload, doseq=True)
        f = curl_bytes(form["action"] + ("?" + q if q else ""))
    html, enc = decode_body(f.pop("body"))
    rows = extract_rows(html, f.get("final_url") or form["action"])
    return {
        "field": field,
        "page": page_no,
        **f,
        "selected_charset": enc,
        "title": extract_title(html),
        "row_count": len(rows),
        "rows": rows,
        "target_visible": TARGET in clean_html(html),
    }


def inspect_detail(row: dict) -> dict:
    f = curl_bytes(row["url"])
    html, enc = decode_body(f.pop("body"))
    text = clean_html(html)
    dates = []
    for y, mo, d in DATE_RE.findall(text):
        val = f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
        if val not in dates:
            dates.append(val)
    return {
        "pstSn": row["pstSn"],
        "url": row["url"],
        **f,
        "selected_charset": enc,
        "title": extract_title(html),
        "dates": dates[:20],
        "city_planning_signals": [t for t in ("도시계획위원회", "도시계획과") if t in text],
    }


def main() -> None:
    print("=" * 78)
    print("SEONGNAM URBAN PLANNING COMMITTEE PAGINATION / HISTORICAL COVERAGE RECONSTRUCTION - S226L")
    print("=" * 78)
    print("Purpose: map pagination arguments and reconstruct bounded historical coverage using default-list replay only")
    print("Committee semantic query: NOT EXECUTED")
    print("UQQ700 target query: NOT EXECUTED")
    print("Global/footer dates: NOT ACCEPTED AS COVERAGE WITHOUT ROW/DETAIL IDENTITY")
    print("Negative evidence: DISABLED")
    print("Source closure: BLOCKED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    root = curl_bytes(BOARD_BASE)
    html, enc = decode_body(root.pop("body"))
    form = extract_search_form(html, root.get("final_url") or BOARD_BASE)
    inline_scripts = extract_inline_scripts(html)
    function_texts = {}
    for name in ("fnMovePage", "fn_srch_list", "fn_move_form", "fn_per_type", "fn_select_change", "fn_sort_select_list"):
        for script in inline_scripts:
            body = extract_function_body(script, name)
            if body:
                function_texts[name] = body
                break
    inferred = infer_page_contract(function_texts)

    page_fields = candidate_page_fields(form or {"controls": []}, inferred) if form else []
    probe_matrix = []
    field_quality = []
    if form:
        for field in page_fields:
            pages = []
            fingerprints = []
            for page_no in (1, 2, 3):
                r = replay_page(form, field, page_no)
                pages.append(r)
                fingerprints.append(tuple(x["pstSn"] for x in r["rows"][:20]))
            distinct = len(set(fingerprints))
            nonempty = sum(1 for p in pages if p["row_count"] > 0)
            score = distinct * 10 + nonempty
            field_quality.append({"field": field, "score": score, "distinct_fingerprints": distinct, "nonempty_pages": nonempty})
            probe_matrix.extend(pages)

    best_field = None
    if field_quality:
        best = sorted(field_quality, key=lambda x: (-x["score"], x["field"]))[0]
        if best["distinct_fingerprints"] >= 2 and best["nonempty_pages"] >= 2:
            best_field = best["field"]

    bounded_pages = []
    if form and best_field:
        seen_fingerprints = set()
        for page_no in range(1, MAX_PAGE + 1):
            r = replay_page(form, best_field, page_no)
            fp = tuple(x["pstSn"] for x in r["rows"][:30])
            r["fingerprint"] = list(fp)
            r["duplicate_page"] = fp in seen_fingerprints if fp else False
            bounded_pages.append(r)
            if fp:
                seen_fingerprints.add(fp)
            if page_no > 1 and (r["row_count"] == 0 or r["duplicate_page"]):
                break

    canonical_rows = []
    seen_pst = set()
    for p in bounded_pages:
        for row in p["rows"]:
            if row["pstSn"] not in seen_pst:
                seen_pst.add(row["pstSn"])
                canonical_rows.append(row)

    detail_samples = [inspect_detail(row) for row in canonical_rows[:MAX_DETAIL_SAMPLE]]
    identity_dates = []
    for row in canonical_rows:
        for d in row.get("row_dates") or []:
            identity_dates.append(d)
    for d in detail_samples:
        for date in d.get("dates") or []:
            identity_dates.append(date)
    identity_dates = sorted(set(identity_dates))
    years = sorted({d[:4] for d in identity_dates})

    pagination_argument_mapped = best_field is not None
    bounded_pagination_reconstructed = len(bounded_pages) >= 2 and any(not p.get("duplicate_page") for p in bounded_pages[1:])
    historical_coverage_observed = len(canonical_rows) >= 10 and len(years) >= 2

    if pagination_argument_mapped and bounded_pagination_reconstructed and historical_coverage_observed:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_PAGINATION_HISTORICAL_COVERAGE_QUALIFIED"
        semantic = "CT_BBS020102_PAGINATION_ARGUMENT_AND_BOUNDED_MULTIYEAR_COVERAGE_RECONSTRUCTED_WITHOUT_UQQ700_QUERY"
        next_action = "ASSESS_BOUNDED_UQQ700_HISTORICAL_PRECURSOR_QUERY_ELIGIBILITY_WITHOUT_DESIGNATION_OR_SITE_PROMOTION"
    elif pagination_argument_mapped and bounded_pagination_reconstructed:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_PAGINATION_RECONSTRUCTED_HISTORICAL_COVERAGE_PARTIAL"
        semantic = "CT_BBS020102_PAGINATION_ARGUMENT_RECONSTRUCTED_BUT_OBSERVED_HISTORICAL_COVERAGE_REMAINS_PARTIAL"
        next_action = "EXPAND_BOUNDED_PAGE_RANGE_OR_RECOVER_AUTHORITATIVE_ROW_DATE_FIELDS_WITHOUT_UQQ700_QUERY"
    else:
        classification = "SEONGNAM_URBAN_PLANNING_COMMITTEE_PAGINATION_ARGUMENT_TECHNICAL_UNKNOWN"
        semantic = "CT_BBS020102_PAGINATION_ARGUMENT_OR_MULTI_PAGE_REPLAY_NOT_YET_TECHNICALLY_VERIFIED"
        next_action = "HARDEN_FNMOVEPAGE_FUNCTION_AND_HIDDEN_FIELD_MAPPING_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-141-S226L",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "s226k_input_exists": S226K_OUT.exists(),
        "board_base": BOARD_BASE,
        "verified_detail": VERIFIED_DETAIL,
        "http": root.get("http"),
        "final_url": root.get("final_url"),
        "selected_charset": enc,
        "title": extract_title(html),
        "search_form": form,
        "function_texts": function_texts,
        "inferred_page_contract": inferred,
        "candidate_page_fields": page_fields,
        "field_quality": field_quality,
        "best_page_field": best_field,
        "probe_matrix": probe_matrix,
        "bounded_page_count": len(bounded_pages),
        "bounded_pages": bounded_pages,
        "canonical_row_count": len(canonical_rows),
        "canonical_rows": canonical_rows,
        "detail_sample_count": len(detail_samples),
        "detail_samples": detail_samples,
        "observed_identity_dates": identity_dates,
        "observed_years": years,
        "oldest_identity_date": identity_dates[0] if identity_dates else None,
        "newest_identity_date": identity_dates[-1] if identity_dates else None,
        "pagination_argument_mapped": pagination_argument_mapped,
        "bounded_pagination_reconstructed": bounded_pagination_reconstructed,
        "historical_coverage_observed": historical_coverage_observed,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "committee_semantic_query_executed": False,
            "target_query_executed": False,
            "global_date_used_without_row_or_detail_identity": False,
            "pagination_gap_equals_legal_absence": False,
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

    print("\nFUNCTION CONTRACTS")
    print("-" * 78)
    print(f"SEARCH FORM FOUND: {form is not None}")
    if form:
        print(f"FORM METHOD: {form['method']}")
        print(f"FORM ACTION: {form['action']}")
        print(f"FORM CONTROL NAMES: {[c['name'] for c in form['controls']]}")
    for name, body in function_texts.items():
        print(f"FUNCTION {name}:")
        print(body[:2200])
    print(f"INFERRED PAGE CONTRACT CANDIDATES: {inferred.get('candidates')}")
    print(f"CANDIDATE PAGE FIELDS: {page_fields}")

    print("\nPAGE-FIELD QUALIFICATION")
    print("-" * 78)
    for q in field_quality:
        print(f"FIELD {q['field']} | SCORE={q['score']} | DISTINCT={q['distinct_fingerprints']} | NONEMPTY={q['nonempty_pages']}")
    print(f"BEST PAGE FIELD: {best_field}")

    print("\nBOUNDED PAGINATION")
    print("-" * 78)
    for p in bounded_pages:
        print(f"PAGE {p['page']} | HTTP={p.get('http')} | ROWS={p['row_count']} | DUPLICATE={p.get('duplicate_page')}")
        for row in p["rows"][:10]:
            print(f"  {row['pstSn']} | {row['title']} | ROW_DATES={row['row_dates']}")

    print("\n" + "=" * 78)
    print("HISTORICAL COVERAGE SUMMARY")
    print("=" * 78)
    print(f"PAGINATION ARGUMENT MAPPED: {pagination_argument_mapped}")
    print(f"BEST PAGE FIELD: {best_field}")
    print(f"BOUNDED PAGINATION RECONSTRUCTED: {bounded_pagination_reconstructed}")
    print(f"BOUNDED PAGE COUNT: {len(bounded_pages)}")
    print(f"CANONICAL ROW COUNT: {len(canonical_rows)}")
    print(f"DETAIL SAMPLE COUNT: {len(detail_samples)}")
    print(f"OBSERVED YEARS: {years}")
    print(f"OLDEST IDENTITY DATE: {out['oldest_identity_date']}")
    print(f"NEWEST IDENTITY DATE: {out['newest_identity_date']}")
    print(f"HISTORICAL COVERAGE OBSERVED: {historical_coverage_observed}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Committee semantic query executed: False")
    print("Target query executed: False")
    print("Legal absence inference allowed: False")
    print("SITE FALSE inference allowed: False")
    print("Source closure allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S226K input exists": out["s226k_input_exists"] is True,
        "classification emitted": classification in {
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_PAGINATION_HISTORICAL_COVERAGE_QUALIFIED",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_PAGINATION_RECONSTRUCTED_HISTORICAL_COVERAGE_PARTIAL",
            "SEONGNAM_URBAN_PLANNING_COMMITTEE_PAGINATION_ARGUMENT_TECHNICAL_UNKNOWN",
        },
        "committee semantic query not executed": out["summary"]["committee_semantic_query_executed"] is False,
        "target query not executed": out["summary"]["target_query_executed"] is False,
        "global dates not used without identity": out["summary"]["global_date_used_without_row_or_detail_identity"] is False,
        "pagination gap not legal absence": out["summary"]["pagination_gap_equals_legal_absence"] is False,
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
        raise AssertionError("S226L validation failed")


if __name__ == "__main__":
    main()
