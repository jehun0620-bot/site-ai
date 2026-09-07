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
S227AP_OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_attachment_parameter_contract_recovery.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_attachment_markup_contract_forensic.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE"
LIST_URL = "https://www.seongnam.go.kr/ct-bbs020101"
OFFICIAL_HOST = "www.seongnam.go.kr"
MAX_DETAILS = 10
MAX_SCRIPTS = 30

MOVE_RE = re.compile(r"fn_move_form\s*\(\s*['\"]?(\d+)['\"]?\s*\)", re.I)
SCRIPT_SRC_RE = re.compile(r'''(?is)<script\b[^>]*src\s*=\s*(["'])(.*?)\1''')
TITLE_RE = re.compile(r"(?is)<title[^>]*>(.*?)</title>")
FILE_KEY_RE = re.compile(r"(?i)(file|atch|attach|download|preview|pstSn|bbsCrtSn|idx|sn|seq|id)")
FILE_NAME_RE = re.compile(r"(?i)[^\s<>\"']+\.(?:pdf|hwp|hwpx|xls|xlsx|doc|docx|zip)")
FUNC_DEF_RE = re.compile(r"(?is)function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{(.*?)\}")


def curl_request(url: str) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"http": None, "final_url": None, "content_type": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "60",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}|%{url_effective}|%{content_type}",
        url,
    ]
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


def decode_body(body: bytes) -> tuple[str, str]:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            t = body.decode(enc)
            if enc == "utf-8" or "성남" in t:
                return t, enc
        except UnicodeDecodeError:
            pass
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


def page_title(html: str) -> str | None:
    m = TITLE_RE.search(html or "")
    return clean_html(m.group(1)) if m else None


def same_host(url: str) -> bool:
    try:
        return (urlparse(url).hostname or "").lower() == OFFICIAL_HOST
    except Exception:
        return False


def extract_detail_ids(html: str) -> list[str]:
    ids = []
    seen = set()
    for m in MOVE_RE.finditer(html or ""):
        v = m.group(1)
        if v not in seen:
            seen.add(v)
            ids.append(v)
    return ids


def extract_markup_signals(html: str, base_url: str) -> dict:
    anchors = []
    data_attrs = []
    hidden_inputs = []
    forms = []
    file_names = sorted(set(FILE_NAME_RE.findall(html or "")))
    suspicious_snippets = []

    for m in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", html or ""):
        attrs = attr_map(m.group(1))
        label = clean_html(m.group(2))
        blob = " ".join([label] + [f"{k}={v}" for k, v in attrs.items()])
        if FILE_KEY_RE.search(blob) or FILE_NAME_RE.search(blob):
            href = attrs.get("href")
            anchors.append({
                "label": label[:500],
                "href": urljoin(base_url, href) if href else None,
                "onclick": attrs.get("onclick"),
                "title": attrs.get("title"),
                "attrs": attrs,
            })

    for m in re.finditer(r"(?is)<([A-Za-z0-9:_-]+)\b([^>]*)>", html or ""):
        attrs = attr_map(m.group(2))
        picked = {k: v for k, v in attrs.items() if k.startswith("data-") and FILE_KEY_RE.search(k + " " + v)}
        if picked:
            data_attrs.append({"tag": m.group(1), "attrs": picked})

    for m in re.finditer(r"(?is)<input\b([^>]*)>", html or ""):
        attrs = attr_map(m.group(1))
        typ = (attrs.get("type") or "text").lower()
        name = attrs.get("name") or ""
        ident = attrs.get("id") or ""
        val = attrs.get("value") or ""
        if typ == "hidden" and FILE_KEY_RE.search(" ".join([name, ident, val])):
            hidden_inputs.append({"name": name, "id": ident, "value": val, "type": typ})

    for fm in re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", html or ""):
        fa = attr_map(fm.group(1))
        inner = fm.group(2)
        if FILE_KEY_RE.search(inner) or FILE_NAME_RE.search(inner):
            forms.append({
                "id": fa.get("id"),
                "name": fa.get("name"),
                "method": (fa.get("method") or "GET").upper(),
                "action": urljoin(base_url, fa.get("action") or base_url),
                "snippet": clean_html(inner)[:1500],
            })

    for pat in ("getFile", "filePreview", "download", "첨부파일", "바로보기", "fileSn", "atchFile", "bbsCrtSn"):
        for m in re.finditer(re.escape(pat), html or "", re.I):
            suspicious_snippets.append(clean_html((html or "")[max(0, m.start()-500):m.end()+800])[:1800])
            if len(suspicious_snippets) >= 30:
                break
        if len(suspicious_snippets) >= 30:
            break

    return {
        "anchors": anchors[:50],
        "data_attrs": data_attrs[:50],
        "hidden_inputs": hidden_inputs[:50],
        "forms": forms[:20],
        "file_names": file_names[:100],
        "suspicious_snippets": suspicious_snippets[:30],
    }


def extract_script_urls(html: str, base_url: str) -> list[str]:
    urls = []
    seen = set()
    for m in SCRIPT_SRC_RE.finditer(html or ""):
        url = urljoin(base_url, unescape(m.group(2)).strip())
        if same_host(url) and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def inspect_script(url: str) -> dict:
    r = curl_request(url)
    text, enc = decode_body(r.get("body") or b"")
    functions = []
    snippets = []
    if r.get("http") == "200":
        for fm in FUNC_DEF_RE.finditer(text):
            name = fm.group(1)
            args = fm.group(2)
            body = fm.group(3)
            blob = f"{name} {args} {body}"
            if FILE_KEY_RE.search(blob):
                functions.append({"name": name, "args": args, "body": body[:2500]})
        for pat in ("getFile", "filePreview", "download", "fileSn", "atchFile", "bbsCrtSn"):
            for m in re.finditer(re.escape(pat), text, re.I):
                snippets.append(text[max(0, m.start()-400):m.end()+1000][:1800])
                if len(snippets) >= 30:
                    break
            if len(snippets) >= 30:
                break
    return {
        "url": url,
        "http": r.get("http"),
        "content_type": r.get("content_type"),
        "charset": enc,
        "function_hits": functions[:30],
        "snippets": snippets[:30],
    }


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY PLANNING DOCUMENT ATTACHMENT MARKUP CONTRACT FORENSIC - S227A-P2")
    print("=" * 78)
    print("Purpose: recover attachment identifiers from detail markup, hidden inputs, data-* and linked JS")
    print("UQQ700 target query: NOT EXECUTED")
    print("Attachment markup hit != designation notice")
    print("Markup no-hit != legal absence")
    print("SITE FALSE inference: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    prior_exists = S227AP_OUT.exists()
    prior = json.loads(S227AP_OUT.read_text(encoding="utf-8")) if prior_exists else {}
    prior_route_ok = bool(prior.get("prior_route_contract_qualified"))

    lr = curl_request(LIST_URL)
    list_html, _ = decode_body(lr.get("body") or b"")
    detail_ids = extract_detail_ids(list_html)[:MAX_DETAILS]

    details = []
    script_urls = []
    script_seen = set()
    total_signal_count = 0
    file_name_count = 0

    for pst_sn in detail_ids:
        url = f"{LIST_URL}/{pst_sn}"
        r = curl_request(url)
        html, enc = decode_body(r.get("body") or b"")
        signals = extract_markup_signals(html, url) if r.get("http") == "200" else {
            "anchors": [], "data_attrs": [], "hidden_inputs": [], "forms": [], "file_names": [], "suspicious_snippets": []
        }
        count = sum(len(signals[k]) for k in ("anchors", "data_attrs", "hidden_inputs", "forms", "suspicious_snippets"))
        total_signal_count += count
        file_name_count += len(signals["file_names"])
        for su in extract_script_urls(html, url):
            if su not in script_seen:
                script_seen.add(su)
                script_urls.append(su)
        details.append({
            "pstSn": pst_sn,
            "url": url,
            "http": r.get("http"),
            "content_type": r.get("content_type"),
            "charset": enc,
            "title": page_title(html),
            "signal_count": count,
            **signals,
        })

    script_results = [inspect_script(u) for u in script_urls[:MAX_SCRIPTS]]
    script_contract_hits = sum(len(x["function_hits"]) + len(x["snippets"]) for x in script_results)

    markup_contract_observed = total_signal_count > 0 or file_name_count > 0
    js_contract_observed = script_contract_hits > 0

    if prior_route_ok and (markup_contract_observed or js_contract_observed):
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ATTACHMENT_MARKUP_CONTRACT_OBSERVED"
        semantic = "VERIFIED_PLANNING_DETAILS_EXPOSED_ATTACHMENT_RELATED_MARKUP_OR_LINKED_JS_IDENTIFIERS_WITHOUT_UQQ700_QUERY"
        next_action = "RECONSTRUCT_EXACT_DOWNLOAD_REQUEST_FROM_OBSERVED_MARKUP_OR_JS_AND_VERIFY_BINARY_ATTACHMENT"
    else:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ATTACHMENT_MARKUP_CONTRACT_TECHNICAL_UNKNOWN"
        semantic = "NO_ATTACHMENT_IDENTIFIER_CONTRACT_RECOVERED_YET_FROM_VERIFIED_DETAILS_OR_LINKED_SCRIPTS"
        next_action = "EXPAND_DETAIL_SURFACE_OR_NETWORK_STYLE_PARAMETER_FORENSICS_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-145-S227A-P2",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "s227ap_input_exists": prior_exists,
        "prior_route_contract_qualified": prior_route_ok,
        "target_query_executed": False,
        "list_http": lr.get("http"),
        "detail_ids": detail_ids,
        "details": details,
        "script_url_count": len(script_urls),
        "script_results": script_results,
        "markup_signal_count": total_signal_count,
        "file_name_count": file_name_count,
        "script_contract_hit_count": script_contract_hits,
        "markup_contract_observed": markup_contract_observed,
        "js_contract_observed": js_contract_observed,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "attachment_markup_hit_equals_designation_notice": False,
            "attachment_markup_hit_equals_current_validity": False,
            "attachment_markup_hit_equals_site_inclusion": False,
            "markup_no_hit_equals_legal_absence": False,
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

    print("\nDETAIL MARKUP FORENSICS")
    print("-" * 78)
    print(f"LIST HTTP: {lr.get('http')}")
    print(f"DETAIL COUNT: {len(details)}")
    print(f"MARKUP SIGNAL COUNT: {total_signal_count}")
    print(f"FILE NAME COUNT: {file_name_count}")
    for d in details:
        print(f"PSTSN={d['pstSn']} HTTP={d['http']} SIGNALS={d['signal_count']} FILE_NAMES={len(d['file_names'])}")
        if d['file_names']:
            print(f"  FILES={d['file_names'][:10]}")
        if d['anchors']:
            print(f"  ANCHOR={d['anchors'][0]}")
        if d['hidden_inputs']:
            print(f"  HIDDEN={d['hidden_inputs'][:5]}")
        if d['data_attrs']:
            print(f"  DATA={d['data_attrs'][:5]}")

    print("\nLINKED SCRIPT FORENSICS")
    print("-" * 78)
    print(f"SCRIPT URL COUNT: {len(script_urls)}")
    print(f"SCRIPT CONTRACT HIT COUNT: {script_contract_hits}")
    for s in script_results:
        if s['function_hits'] or s['snippets']:
            print(f"HTTP={s['http']} URL={s['url']}")
            for f in s['function_hits'][:5]:
                print(f"  FUNCTION={f['name']}({f['args']})")
                print(f"  BODY={f['body'][:1200]}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"PRIOR ROUTE CONTRACT QUALIFIED: {prior_route_ok}")
    print(f"MARKUP CONTRACT OBSERVED: {markup_contract_observed}")
    print(f"JS CONTRACT OBSERVED: {js_contract_observed}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Target query executed: False")
    print("Markup no-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S227A-P input exists": prior_exists,
        "target query not executed": out["target_query_executed"] is False,
        "classification emitted": classification in {
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ATTACHMENT_MARKUP_CONTRACT_OBSERVED",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ATTACHMENT_MARKUP_CONTRACT_TECHNICAL_UNKNOWN",
        },
        "attachment markup hit not designation notice": out["summary"]["attachment_markup_hit_equals_designation_notice"] is False,
        "attachment markup hit not current validity": out["summary"]["attachment_markup_hit_equals_current_validity"] is False,
        "attachment markup hit not site inclusion": out["summary"]["attachment_markup_hit_equals_site_inclusion"] is False,
        "markup no-hit not legal absence": out["summary"]["markup_no_hit_equals_legal_absence"] is False,
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
        raise AssertionError("S227A-P2 validation failed")


if __name__ == "__main__":
    main()
