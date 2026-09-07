# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
S225B = OUT_DIR / "development_density_management_area_local_gosi_official_nf_form_entry_gate_replay.json"
OUT = OUT_DIR / "development_density_management_area_local_gosi_official_source_role_qualification.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "LOCAL_GOSI_OFFICIAL"
ENTRY_URL = "https://local.gosi.go.kr/klid/main/main.do"
GOSI_URL = "https://local.gosi.go.kr/klid/gosi/gosi.do"
EXAM_GOSI_URL = "https://local.gosi.go.kr/klid/sihum/examgosi.do"

EXPECTED_S225B = "LOCAL_GOSI_OFFICIAL_NF_FORM_ENTRY_GATE_REPLAY_APPLICATION_SURFACE_RECOVERED"

GENERAL_NOTICE_TERMS = (
    "고시·공고", "고시ㆍ공고", "고시/공고", "행정고시", "행정공고", "공고번호", "고시번호",
    "입법예고", "행정예고", "도시계획", "도시관리계획", "지형도면", "토지", "개발행위",
)
EXAM_RECRUITMENT_TERMS = (
    "인터넷원서접수센터", "시험시행정보", "시험공고", "합격 및 면접", "시험장소", "시험통계",
    "시험문제 및 정답", "원서접수", "응시표", "합격/성적", "채용", "가산자격증",
    "영어시험", "한국사시험", "임용등록",
)
SEARCH_CONTROL_TERMS = ("검색", "조회", "search", "keyword", "searchKeyword", "searchText", "query")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def attrs(tag: str) -> dict[str, str]:
    pairs = re.findall(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', tag, flags=re.S)
    return {k: unescape(v) for k, _, v in pairs}


def extract_forms(html: str, base_url: str) -> list[dict]:
    forms: list[dict] = []
    for m in re.finditer(r"(?is)<form\b([^>]*)>(.*?)</form>", html or ""):
        fa = attrs("<form" + m.group(1) + ">")
        body = m.group(2)
        controls = []
        for cm in re.finditer(r"(?is)<(input|select|textarea|button)\b([^>]*)>", body):
            tag = cm.group(1).lower()
            ca = attrs(f"<{tag}" + cm.group(2) + ">")
            controls.append({
                "tag": tag,
                "type": (ca.get("type") or "").lower() or None,
                "name": ca.get("name"),
                "id": ca.get("id"),
                "value": ca.get("value"),
            })
        forms.append({
            "id": fa.get("id"),
            "name": fa.get("name"),
            "method": (fa.get("method") or "GET").upper(),
            "action_raw": fa.get("action"),
            "action_absolute": urljoin(base_url, fa.get("action")) if fa.get("action") else base_url,
            "controls": controls,
            "control_names": sorted({c["name"] for c in controls if c.get("name")}),
            "text": clean_html(body)[:1200],
        })
    return forms


def extract_links(html: str, base_url: str) -> list[dict]:
    rows = []
    for m in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", html or ""):
        a = attrs("<a" + m.group(1) + ">")
        href = a.get("href")
        text = clean_html(m.group(2))[:300]
        rows.append({
            "text": text,
            "href_raw": href,
            "href_absolute": urljoin(base_url, href) if href and not href.lower().startswith("javascript:") else None,
            "onclick": a.get("onclick"),
        })
    return rows[:500]


def extract_title(html: str) -> str | None:
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html or "")
    return clean_html(m.group(1)) if m else None


def term_hits(text: str, terms: tuple[str, ...]) -> list[str]:
    low = (text or "").lower()
    return [t for t in terms if t.lower() in low]


def analyze_page(resp: requests.Response | None, error: str | None) -> dict:
    html = resp.text if resp is not None else ""
    final_url = resp.url if resp is not None else None
    base_url = final_url or ENTRY_URL
    text = clean_html(html)
    forms = extract_forms(html, base_url)
    links = extract_links(html, base_url)
    control_names = sorted({name for f in forms for name in f.get("control_names", [])})
    search_control_hits = [x for x in SEARCH_CONTROL_TERMS if any(x.lower() in n.lower() for n in control_names)]
    return {
        "http": resp.status_code if resp is not None else None,
        "final_url": final_url,
        "same_official_host": bool(final_url and urlparse(final_url).hostname == "local.gosi.go.kr"),
        "error": error,
        "title": extract_title(html),
        "text_length": len(text),
        "text_prefix": text[:1800],
        "general_notice_term_hits": term_hits(text, GENERAL_NOTICE_TERMS),
        "exam_recruitment_term_hits": term_hits(text, EXAM_RECRUITMENT_TERMS),
        "form_count": len(forms),
        "forms": forms,
        "control_names": control_names,
        "search_control_hits": search_control_hits,
        "link_count": len(links),
        "links_sample": links[:120],
    }


def get(session: requests.Session, url: str, referer: str | None = None) -> tuple[requests.Response | None, str | None]:
    try:
        headers = {"Referer": referer} if referer else None
        return session.get(url, timeout=60, allow_redirects=True, headers=headers), None
    except requests.RequestException as ex:
        return None, f"{type(ex).__name__}: {ex}"


def pass_nf_gate(session: requests.Session) -> tuple[requests.Response | None, requests.Response | None, str | None]:
    entry, entry_err = get(session, ENTRY_URL)
    if entry is None:
        return None, None, entry_err

    forms = extract_forms(entry.text, entry.url)
    nf = [f for f in forms if f.get("id") == "nfForm" and "nf_token" in (f.get("control_names") or [])]
    if len(nf) != 1:
        return entry, None, f"NF_FORM_COUNT_{len(nf)}"

    # Recover the exact hidden nf_token value from raw HTML; no search fields are added.
    m = re.search(r'''(?is)<input\b[^>]*name=["']nf_token["'][^>]*>''', entry.text)
    if not m:
        return entry, None, "NF_TOKEN_INPUT_NOT_FOUND"
    ia = attrs(m.group(0))
    token = ia.get("value")
    action = nf[0].get("action_absolute")
    if not token or not action or urlparse(action).hostname != "local.gosi.go.kr":
        return entry, None, "NF_FORM_UNSAFE_OR_INCOMPLETE"

    try:
        post = session.post(
            action,
            data={"nf_token": token},
            timeout=60,
            allow_redirects=True,
            headers={"Referer": entry.url},
        )
        return entry, post, None
    except requests.RequestException as ex:
        return entry, None, f"{type(ex).__name__}: {ex}"


def main() -> None:
    print("=" * 78)
    print("LOCAL GOSI OFFICIAL SOURCE-ROLE QUALIFICATION - S225C")
    print("=" * 78)
    print("Purpose: determine whether local.gosi.go.kr is a general official-notice source or exam/recruitment service")
    print("Positive-control search: NOT EXECUTED")
    print("UQQ700 target query: NOT EXECUTED")
    print("Search request: NOT EXECUTED")
    print("Search no-hit != legal absence")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s225b = load(S225B)
    gate = (
        s225b.get("classification") == EXPECTED_S225B
        and (s225b.get("replay") or {}).get("same_official_host") is True
        and (s225b.get("replay") or {}).get("post_gate_application_surface_recovered") is True
        and (s225b.get("summary") or {}).get("search_request_executed") is False
        and (s225b.get("summary") or {}).get("target_query_executed") is False
        and (s225b.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    if not gate:
        raise AssertionError("S225C prerequisite S225B gate not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    entry, post_gate, gate_error = pass_nf_gate(session)
    post_gate_ok = bool(
        post_gate is not None
        and post_gate.status_code == 200
        and urlparse(post_gate.url).hostname == "local.gosi.go.kr"
    )

    gosi_resp = exam_resp = None
    gosi_err = exam_err = None
    if post_gate_ok:
        gosi_resp, gosi_err = get(session, GOSI_URL, referer=post_gate.url)
        exam_resp, exam_err = get(session, EXAM_GOSI_URL, referer=post_gate.url)

    main_page = analyze_page(post_gate, gate_error if post_gate is None else None)
    gosi_page = analyze_page(gosi_resp, gosi_err)
    exam_page = analyze_page(exam_resp, exam_err)

    pages_ok = all(
        p.get("http") == 200 and p.get("same_official_host") is True
        for p in (main_page, gosi_page, exam_page)
    )

    all_text = " ".join(
        (p.get("text_prefix") or "") for p in (main_page, gosi_page, exam_page)
    )
    general_hits = sorted(set(
        main_page["general_notice_term_hits"] + gosi_page["general_notice_term_hits"] + exam_page["general_notice_term_hits"]
    ))
    exam_hits = sorted(set(
        main_page["exam_recruitment_term_hits"] + gosi_page["exam_recruitment_term_hits"] + exam_page["exam_recruitment_term_hits"]
    ))

    gosi_exam_context = bool(
        any(t in (gosi_page.get("text_prefix") or "") for t in ("시험", "원서", "채용", "응시", "합격"))
        or "인터넷원서접수센터" in (gosi_page.get("text_prefix") or "")
    )
    general_role_signal = bool(
        any(t in all_text for t in ("도시계획", "도시관리계획", "지형도면", "입법예고", "행정예고", "고시번호", "공고번호"))
    )
    exam_role_signal = bool(
        "지방자치단체 인터넷원서접수센터" in all_text
        and len(exam_hits) >= 5
        and gosi_exam_context
    )

    if pages_ok and general_role_signal and not exam_role_signal:
        classification = "LOCAL_GOSI_SOURCE_ROLE_GENERAL_OFFICIAL_NOTICE_QUALIFIED"
        semantic = "LOCAL_GOSI_GENERAL_OFFICIAL_NOTICE_SOURCE_ROLE_QUALIFIED_WITHOUT_TARGET_QUERY"
        next_action = "BUILD_POSITIVE_CONTROL_SEARCH_CONTRACT_WITHOUT_UQQ700_QUERY"
        source_role = "GENERAL_OFFICIAL_NOTICE"
        target_search_eligible = True
    elif pages_ok and exam_role_signal and not general_role_signal:
        classification = "LOCAL_GOSI_SOURCE_ROLE_EXAM_RECRUITMENT_SERVICE_ONLY"
        semantic = "LOCAL_GOSI_OFFICIAL_HOST_VERIFIED_BUT_SOURCE_ROLE_IS_EXAM_RECRUITMENT_SERVICE_NOT_GENERAL_DESIGNATION_NOTICE"
        next_action = "EXCLUDE_LOCAL_GOSI_FROM_UQQ700_DESIGNATION_SEARCH_ROLE_AND_KEEP_UQQ700_UNKNOWN"
        source_role = "EXAM_RECRUITMENT_SERVICE"
        target_search_eligible = False
    else:
        classification = "LOCAL_GOSI_SOURCE_ROLE_UNRESOLVED"
        semantic = "LOCAL_GOSI_SOURCE_ROLE_NOT_YET_QUALIFIED_FOR_GENERAL_OFFICIAL_NOTICE_SEARCH"
        next_action = "HARDEN_LOCAL_GOSI_SOURCE_ROLE_USING_PAGE_BODY_AND_FORM_CONTRACT_WITHOUT_UQQ700_QUERY"
        source_role = "UNRESOLVED"
        target_search_eligible = False

    out = {
        "step": "STEP 17-21-C-16-8-T-140-S225C",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "prerequisite_s225b": gate,
        "network": {
            "nf_gate_replay_executed": post_gate is not None,
            "main_surface_get": True,
            "gosi_page_get": gosi_resp is not None or gosi_err is not None,
            "exam_gosi_page_get": exam_resp is not None or exam_err is not None,
            "search_request_executed": False,
            "positive_control_search_executed": False,
            "target_query_executed": False,
        },
        "pages": {
            "main": main_page,
            "gosi_notice": gosi_page,
            "exam_gosi": exam_page,
        },
        "role_signals": {
            "pages_ok": pages_ok,
            "general_notice_term_hits": general_hits,
            "exam_recruitment_term_hits": exam_hits,
            "gosi_page_exam_context": gosi_exam_context,
            "general_official_notice_role_signal": general_role_signal,
            "exam_recruitment_role_signal": exam_role_signal,
            "source_role": source_role,
            "target_search_eligible": target_search_eligible,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "search_request_executed": False,
            "positive_control_search_executed": False,
            "target_query_executed": False,
            "search_hit_equals_legal_fact": False,
            "search_hit_equals_designation_identity": False,
            "search_no_hit_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "official_designation_identity_verified": False,
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("S225B GATE:", gate)
    print("POST-GATE HTTP:", main_page["http"])
    print("GOSI PAGE HTTP:", gosi_page["http"])
    print("GOSI PAGE TITLE:", gosi_page["title"])
    print("EXAM GOSI PAGE HTTP:", exam_page["http"])
    print("EXAM GOSI PAGE TITLE:", exam_page["title"])
    print("PAGES OK:", pages_ok)
    print("GENERAL NOTICE TERM HITS:", general_hits)
    print("EXAM/RECRUITMENT TERM HITS:", exam_hits)
    print("GOSI PAGE EXAM CONTEXT:", gosi_exam_context)
    print("GENERAL OFFICIAL NOTICE ROLE SIGNAL:", general_role_signal)
    print("EXAM/RECRUITMENT ROLE SIGNAL:", exam_role_signal)
    print("SOURCE ROLE:", source_role)
    print("TARGET SEARCH ELIGIBLE:", target_search_eligible)
    print("CLASSIFICATION:", classification)

    print("\nGOSI PAGE FORMS")
    print(json.dumps(gosi_page["forms"], ensure_ascii=False, indent=2))
    print("\nGOSI PAGE LINKS SAMPLE")
    print(json.dumps(gosi_page["links_sample"], ensure_ascii=False, indent=2))
    print("\nEXAM GOSI PAGE FORMS")
    print(json.dumps(exam_page["forms"], ensure_ascii=False, indent=2))

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("Search request executed: False")
    print("Positive-control search executed: False")
    print("Target query executed: False")
    print("Search no-hit equals legal absence: False")
    print("Negative evidence allowed: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S225B prerequisite gate": gate,
        "nfForm gate replay classified": post_gate is not None or gate_error is not None,
        "source-role classification emitted": classification in {
            "LOCAL_GOSI_SOURCE_ROLE_GENERAL_OFFICIAL_NOTICE_QUALIFIED",
            "LOCAL_GOSI_SOURCE_ROLE_EXAM_RECRUITMENT_SERVICE_ONLY",
            "LOCAL_GOSI_SOURCE_ROLE_UNRESOLVED",
        },
        "search request not executed": out["network"]["search_request_executed"] is False,
        "positive control search not executed": out["network"]["positive_control_search_executed"] is False,
        "target query not executed": out["network"]["target_query_executed"] is False,
        "search hit not legal fact": out["summary"]["search_hit_equals_legal_fact"] is False,
        "search hit not designation identity": out["summary"]["search_hit_equals_designation_identity"] is False,
        "search no-hit not legal absence": out["summary"]["search_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["official_designation_identity_verified"] is False,
        "current validity not promoted": out["current_validity_verified"] is False,
        "site inclusion not promoted": out["site_spatial_inclusion_verified"] is False,
        "SITE promotion blocked": not out["site_positive_allowed"] and not out["site_negative_allowed"],
        "runtime registration blocked": out["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("\nVALIDATION")
    for name, value in checks.items():
        print(f"{name}: {value}")
    print("all_pass:", all(checks.values()))
    if not all(checks.values()):
        raise AssertionError("S225C local.gosi.go.kr source-role qualification failed")


if __name__ == "__main__":
    main()
