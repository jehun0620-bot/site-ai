from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests


TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"

MOLIT_ORIGIN = "https://www.molit.go.kr"
ENTRY_URLS = [
    "https://www.molit.go.kr/",
    "https://www.molit.go.kr/USR/I0204/m_45/lst.jsp",
]
EXPECTED_HOSTS = {"www.molit.go.kr", "molit.go.kr"}
OUTPUT_PATH = Path(
    "law_data/output/development_density_management_area_molit_entry_access_qualification_test.json"
)

TIMEOUT = 30
MAX_FORM_COUNT = 40
MAX_LINK_COUNT = 120
MAX_FIELD_COUNT = 120

SIGNAL_TERMS = (
    "행정규칙",
    "훈령",
    "예규",
    "고시",
    "공고",
    "도시계획",
    "지형도면",
    "검색",
)


class QualificationError(RuntimeError):
    pass


def normalize_space(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def strip_tags(value: str) -> str:
    value = re.sub(r"(?is)<script\b[^>]*>.*?</script>", " ", value)
    value = re.sub(r"(?is)<style\b[^>]*>.*?</style>", " ", value)
    value = re.sub(r"(?is)<[^>]+>", " ", value)
    value = value.replace("&nbsp;", " ").replace("&amp;", "&")
    return normalize_space(value)


def attr_value(tag: str, name: str) -> str:
    match = re.search(
        rf"\b{re.escape(name)}\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))",
        tag,
        re.I,
    )
    if not match:
        return ""
    return next((group for group in match.groups() if group is not None), "")


def html_title(html: str) -> str:
    match = re.search(r"(?is)<title\b[^>]*>(.*?)</title>", html)
    return strip_tags(match.group(1)) if match else ""


def is_official_molit_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in EXPECTED_HOSTS or host.endswith(".molit.go.kr")


def extract_forms(html: str, base_url: str) -> list[dict]:
    forms: list[dict] = []
    for form_match in re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", html):
        attrs, body = form_match.groups()
        method = (attr_value(attrs, "method") or "GET").upper()
        raw_action = attr_value(attrs, "action")
        action = urljoin(base_url, raw_action or base_url)

        fields: list[dict] = []
        field_names: list[str] = []
        for tag_match in re.finditer(r"(?is)<(?:input|select|textarea)\b[^>]*>", body):
            tag = tag_match.group(0)
            name = attr_value(tag, "name")
            if not name:
                continue
            field_type = attr_value(tag, "type") or tag.split("<", 1)[-1].split(None, 1)[0].rstrip(">")
            value = attr_value(tag, "value")
            fields.append(
                {
                    "name": name,
                    "type": field_type.lower(),
                    "value_preview": normalize_space(value)[:160],
                }
            )
            field_names.append(name)
            if len(fields) >= MAX_FIELD_COUNT:
                break

        names_lower = " ".join(field_names).lower()
        action_lower = action.lower()
        signal_score = 0
        for token in (
            "search",
            "srch",
            "keyword",
            "query",
            "titl",
            "ctnt",
            "regdate",
            "usr_num",
            "gubun",
            "lcmspage",
            "psize",
        ):
            if token in names_lower or token in action_lower:
                signal_score += 1

        forms.append(
            {
                "method": method,
                "action": action,
                "official_host": is_official_molit_url(action),
                "field_names": field_names,
                "fields": fields,
                "signal_score": signal_score,
            }
        )
        if len(forms) >= MAX_FORM_COUNT:
            break

    forms.sort(key=lambda item: (-item["signal_score"], item["action"]))
    return forms


def extract_links(html: str, base_url: str) -> list[dict]:
    links: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for match in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", html):
        attrs, body = match.groups()
        raw_href = attr_value(attrs, "href")
        if not raw_href or raw_href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        title = strip_tags(body)
        absolute = urljoin(base_url, raw_href)
        if not is_official_molit_url(absolute):
            continue

        signal_blob = f"{title} {absolute}".lower()
        signal_terms = [term for term in SIGNAL_TERMS if term.lower() in signal_blob]
        parsed = urlparse(absolute)
        params = parse_qs(parsed.query, keep_blank_values=True)

        is_i0204 = "/USR/I0204/" in parsed.path
        is_list = parsed.path.endswith("/lst.jsp")
        is_detail = parsed.path.endswith("/dtl.jsp")
        has_idx = "idx" in params
        score = len(signal_terms)
        if is_i0204:
            score += 3
        if is_list:
            score += 2
        if is_detail:
            score += 3
        if has_idx:
            score += 2

        if score <= 0:
            continue

        key = (absolute, title)
        if key in seen:
            continue
        seen.add(key)
        links.append(
            {
                "title": title[:500],
                "url": absolute,
                "path": parsed.path,
                "query_keys": sorted(params),
                "signal_terms": signal_terms,
                "i0204_family": is_i0204,
                "list_endpoint": is_list,
                "detail_endpoint": is_detail,
                "detail_identity_parameter_present": has_idx,
                "score": score,
            }
        )

    links.sort(key=lambda item: (-item["score"], item["url"]))
    return links[:MAX_LINK_COUNT]


def extract_structural_signals(html: str) -> dict:
    text = strip_tags(html)
    lower_html = html.lower()
    return {
        "signal_terms_present": [term for term in SIGNAL_TERMS if term in text],
        "i0204_occurrences": lower_html.count("/usr/i0204/"),
        "lst_jsp_occurrences": lower_html.count("lst.jsp"),
        "dtl_jsp_occurrences": lower_html.count("dtl.jsp"),
        "idx_parameter_occurrences": len(re.findall(r"(?:[?&]|&amp;)idx=", lower_html)),
        "search_field_tokens": sorted(
            set(
                re.findall(
                    r"(?i)\b(?:search|srch_[a-z0-9_]+|lcmspage|psize|gubun)\b",
                    html,
                )
            )
        )[:100],
    }


def fetch_entry(session: requests.Session, url: str) -> dict:
    try:
        response = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        response.raise_for_status()
    except requests.RequestException as exc:
        return {
            "requested_url": url,
            "technical_unknown": True,
            "error": repr(exc),
            "http_status": getattr(getattr(exc, "response", None), "status_code", None),
            "final_url": getattr(getattr(exc, "response", None), "url", None),
            "official_final_host": False,
            "title": "",
            "forms": [],
            "links": [],
            "structure": {},
        }

    html = response.text
    final_url = response.url
    return {
        "requested_url": url,
        "technical_unknown": False,
        "error": None,
        "http_status": response.status_code,
        "final_url": final_url,
        "official_final_host": is_official_molit_url(final_url),
        "content_type": response.headers.get("content-type", ""),
        "title": html_title(html),
        "html_size": len(html.encode(response.encoding or "utf-8", errors="ignore")),
        "forms": extract_forms(html, final_url),
        "links": extract_links(html, final_url),
        "structure": extract_structural_signals(html),
    }


def classify(entries: list[dict]) -> tuple[str, str, bool]:
    usable = [
        entry
        for entry in entries
        if not entry["technical_unknown"]
        and entry["http_status"] == 200
        and entry["official_final_host"]
    ]
    if not usable:
        return (
            "MOLIT_ENTRY_ACCESS_TECHNICAL_UNKNOWN",
            "HARDEN_MOLIT_ENTRY_TRANSPORT_OR_OFFICIAL_HOST_ACCESS_WITHOUT_LEGAL_INFERENCE",
            False,
        )

    i0204_surface = any(
        entry["structure"].get("i0204_occurrences", 0) > 0
        or any(link.get("i0204_family") for link in entry["links"])
        or "/USR/I0204/" in (urlparse(entry["final_url"]).path or "")
        for entry in usable
    )
    search_contract_signal = any(
        any(form.get("signal_score", 0) > 0 and form.get("official_host") for form in entry["forms"])
        for entry in usable
    )
    list_or_detail_signal = any(
        any(link.get("list_endpoint") or link.get("detail_endpoint") for link in entry["links"])
        or (urlparse(entry["final_url"]).path or "").endswith(("/lst.jsp", "/dtl.jsp"))
        for entry in usable
    )

    if i0204_surface and (search_contract_signal or list_or_detail_signal):
        return (
            "MOLIT_OFFICIAL_I0204_ENTRY_SURFACE_QUALIFIED",
            "RECOVER_AND_POSITIVE_CONTROL_THE_MOLIT_I0204_LIST_SEARCH_CONTRACT_BEFORE_ANY_UQQ700_QUERY",
            True,
        )

    return (
        "MOLIT_ENTRY_ACCESS_REACHED_BUT_SEARCH_SURFACE_NOT_QUALIFIED",
        "INSPECT_ONLY_OFFICIAL_MOLIT_ENTRY_FOR_REAL_LIST_FORM_OR_I0204_NAVIGATION_CONTRACT",
        False,
    )


def main() -> None:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; site-ai-official-source-qualification/1.0)",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.6",
        }
    )

    entries = [fetch_entry(session, url) for url in ENTRY_URLS]
    classification, next_action, entry_surface_qualified = classify(entries)

    technical_unknown_count = sum(1 for entry in entries if entry["technical_unknown"])
    form_count = sum(len(entry["forms"]) for entry in entries)
    link_count = sum(len(entry["links"]) for entry in entries)
    detail_link_count = sum(
        1 for entry in entries for link in entry["links"] if link.get("detail_endpoint")
    )
    list_link_count = sum(
        1 for entry in entries for link in entry["links"] if link.get("list_endpoint")
    )
    field_counter = Counter(
        name
        for entry in entries
        for form in entry["forms"]
        for name in form.get("field_names", [])
    )

    summary = {
        "target": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "classification": classification,
        "next_action": next_action,
        "entry_surface_qualified": entry_surface_qualified,
        "entry_url_count": len(ENTRY_URLS),
        "technical_unknown_count": technical_unknown_count,
        "form_count": form_count,
        "qualified_signal_link_count": link_count,
        "list_endpoint_signal_count": list_link_count,
        "detail_endpoint_signal_count": detail_link_count,
        "field_frequency": dict(field_counter.most_common(50)),
        "entry_access_is_designation": False,
        "entry_access_is_current_validity": False,
        "entry_access_is_site_inclusion": False,
        "entry_access_failure_is_legal_absence": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_false_inference_allowed": False,
        "official_designation_identity_verified": False,
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "runtime_registration_allowed": False,
        "final_resolution": "UNKNOWN",
    }

    validation = {
        "target name": summary["target"] == TARGET,
        "standard code": summary["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": summary["resolution_type"] == RESOLUTION_TYPE,
        "entry URL scope bounded": len(ENTRY_URLS) == 2,
        "official entry access only": all(is_official_molit_url(url) for url in ENTRY_URLS),
        "technical state explicit": all("technical_unknown" in entry for entry in entries),
        "entry access not designation": not summary["entry_access_is_designation"],
        "entry access not validity": not summary["entry_access_is_current_validity"],
        "entry access not site inclusion": not summary["entry_access_is_site_inclusion"],
        "entry failure not legal absence": not summary["entry_access_failure_is_legal_absence"],
        "negative evidence disabled": not summary["negative_evidence_allowed"],
        "legal absence inference disabled": not summary["legal_absence_inference_allowed"],
        "SITE FALSE inference disabled": not summary["site_false_inference_allowed"],
        "designation not promoted": not summary["official_designation_identity_verified"],
        "validity not promoted": not summary["current_validity_verified"],
        "site inclusion not promoted": not summary["site_spatial_inclusion_verified"],
        "runtime registration blocked": not summary["runtime_registration_allowed"],
        "UQQ700 remains UNKNOWN": summary["final_resolution"] == "UNKNOWN",
    }

    payload = {
        "summary": summary,
        "entries": entries,
        "validation": validation,
        "all_pass": all(validation.values()),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 78)
    print("MOLIT ENTRY ACCESS QUALIFICATION TEST")
    print("=" * 78)
    print("Purpose: qualify only the official MOLIT entry/search surface before UQQ700 querying")
    print("Entry/search access != designation/current validity/site inclusion")
    print("Entry access failure != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    print("\n" + "=" * 78)
    print("ENTRY ACCESS")
    print("=" * 78)
    for index, entry in enumerate(entries, start=1):
        print(f"ENTRY {index}: {entry['requested_url']}")
        print(f"  http={entry.get('http_status')} technical_unknown={entry['technical_unknown']}")
        print(f"  final={entry.get('final_url')}")
        print(f"  official_final_host={entry.get('official_final_host')}")
        print(f"  title={entry.get('title')}")
        print(f"  forms={len(entry.get('forms', []))} signal_links={len(entry.get('links', []))}")
        for form_index, form in enumerate(entry.get("forms", [])[:8], start=1):
            print(
                f"    FORM {form_index}: method={form['method']} score={form['signal_score']} "
                f"action={form['action']}"
            )
            print(f"      fields={form['field_names'][:30]}")
        for link_index, link in enumerate(entry.get("links", [])[:12], start=1):
            print(
                f"    LINK {link_index}: score={link['score']} "
                f"list={link['list_endpoint']} detail={link['detail_endpoint']} title={link['title'][:140]}"
            )
            print(f"      url={link['url']}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print(f"Entry surface qualified: {entry_surface_qualified}")
    print("Entry/search access == designation: False")
    print("Entry/search access == current validity: False")
    print("Entry/search access == site inclusion: False")
    print("Entry access failure == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for name, passed in validation.items():
        print(f"{name}: {passed}")
    print(f"output written: {OUTPUT_PATH.exists()}")
    print(f"all_pass: {payload['all_pass']}")
    print(f"Output: {OUTPUT_PATH.resolve()}")


if __name__ == "__main__":
    main()
