# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlencode

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_council_uqq700_bounded_target_search.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_COUNCIL_OFFICIAL_RECORD"

CONTRACTS = [
    {
        "family": "MINUTES",
        "url": "https://www.sncouncil.go.kr/kr/assembly/details.do",
        "query_field": "keyword",
        "fixed_payload": {
            "startDay": "",
            "endDay": "",
            "sTh": "10",
            "session": "",
            "committeeCode": "",
            "memberCode": "",
        },
    },
    {
        "family": "AGENDA",
        "url": "https://www.sncouncil.go.kr/kr/bill/bill.do",
        "query_field": "subject",
        "fixed_payload": {
            "proposer": "",
            "startDay": "",
            "endDay": "",
            "sTh": "",
            "session": "",
            "code": "",
            "committeeType": "",
            "committeeCode": "",
            "proposerType": "",
            "memberCode": "",
            "result": "",
        },
    },
]

QUERIES = [
    {"query": "개발밀도관리구역", "class": "EXACT"},
    {"query": "개발밀도 관리구역", "class": "VARIANT"},
    {"query": "개발밀도", "class": "WEAK"},
]

NOTICE_PATTERNS = [
    re.compile(r"성남시\s*고시\s*제\s*\d{4}\s*[-–]\s*\d+\s*호?"),
    re.compile(r"성남시\s*공고\s*제\s*\d{4}\s*[-–]\s*\d+\s*호?"),
    re.compile(r"고시\s*제\s*\d{4}\s*[-–]\s*\d+\s*호?"),
]


def curl_get(url: str, params: dict) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"http": None, "final_url": None, "content_type": None, "redirects": None, "body": b"", "stderr": "curl not found"}
    full = url + ("&" if "?" in url else "?") + urlencode(params, doseq=True)
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "120",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-e", url,
        "-w", "\n__META__%{http_code}|%{url_effective}|%{content_type}|%{num_redirects}",
        full,
    ]
    p = subprocess.run(cmd, capture_output=True)
    raw = p.stdout or b""
    marker = b"\n__META__"
    if marker in raw:
        body, meta = raw.rsplit(marker, 1)
        parts = meta.decode("utf-8", errors="replace").strip().split("|", 3)
        http = parts[0] if parts else None
        final_url = parts[1] if len(parts) > 1 else None
        content_type = parts[2] if len(parts) > 2 else None
        redirects = parts[3] if len(parts) > 3 else None
    else:
        body, http, final_url, content_type, redirects = raw, None, None, None, None
    return {
        "http": http,
        "final_url": final_url,
        "content_type": content_type,
        "redirects": redirects,
        "body": body,
        "stderr": (p.stderr or b"").decode("utf-8", errors="replace").strip(),
    }


def decode(body: bytes) -> str:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            return body.decode(enc)
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", errors="replace")


def strip_tags(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s)
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def target_occurrence_count(text: str, query: str) -> int:
    if not query:
        return 0
    return text.count(query)


def extract_notice_identities(text: str) -> list[str]:
    found = []
    seen = set()
    for pat in NOTICE_PATTERNS:
        for m in pat.finditer(text):
            v = re.sub(r"\s+", " ", m.group(0)).strip()
            if v not in seen:
                seen.add(v)
                found.append(v)
    return found[:50]


def extract_contexts(text: str, needles: list[str], radius: int = 180) -> list[str]:
    rows = []
    seen = set()
    for needle in needles:
        if not needle:
            continue
        start = 0
        while True:
            idx = text.find(needle, start)
            if idx < 0:
                break
            lo = max(0, idx - radius)
            hi = min(len(text), idx + len(needle) + radius)
            ctx = re.sub(r"\s+", " ", text[lo:hi]).strip()
            if ctx and ctx not in seen:
                seen.add(ctx)
                rows.append(ctx)
            start = idx + max(1, len(needle))
            if len(rows) >= 30:
                return rows
    return rows


def detect_result_count(plain: str) -> int | None:
    patterns = [
        r"총\s*([0-9,]+)\s*건",
        r"검색결과\s*[:：]?\s*([0-9,]+)\s*건",
        r"검색 결과\s*[:：]?\s*([0-9,]+)\s*건",
    ]
    for p in patterns:
        m = re.search(p, plain)
        if m:
            try:
                return int(m.group(1).replace(",", ""))
            except ValueError:
                pass
    return None


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY COUNCIL UQQ700 BOUNDED TARGET SEARCH - S228D")
    print("=" * 78)
    print("Purpose: bounded target search on semantically hardened council contracts only")
    print("Contracts: MINUTES.keyword + AGENDA.subject")
    print("Queries: exact / variant / weak")
    print("Council hit != designation notice/current validity/site inclusion")
    print("Council no-hit != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    results = []
    exact_hit_count = 0
    variant_hit_count = 0
    weak_hit_count = 0
    technical_unknown_count = 0
    notice_identity_candidates = []
    notice_seen = set()

    for contract in CONTRACTS:
        for q in QUERIES:
            payload = dict(contract["fixed_payload"])
            payload[contract["query_field"]] = q["query"]
            rr = curl_get(contract["url"], payload)
            text = decode(rr.get("body") or b"")
            plain = strip_tags(text)
            query_echo = q["query"] in text or q["query"] in plain
            error_signal = any(x in plain.lower() for x in ["error", "오류", "잘못된 접근", "페이지를 찾을 수 없습니다"])
            transport_ok = rr.get("http") == "200" and len(rr.get("body") or b"") > 1000 and not error_signal
            occurrence_count = target_occurrence_count(plain, q["query"])
            result_count = detect_result_count(plain)
            notices = extract_notice_identities(plain)
            contexts = extract_contexts(plain, [q["query"]] + notices)

            # Query echo proves the request was reflected, but not by itself that a record matched.
            # Treat a hit only when the term occurs more than once (echo + result/context occurrence)
            # or the page exposes a positive result count. Weak terms remain weak anchors only.
            content_hit = False
            if transport_ok and query_echo:
                if result_count is not None:
                    content_hit = result_count > 0
                else:
                    content_hit = occurrence_count > 1

            if not transport_ok or not query_echo:
                status = "TECHNICAL_UNKNOWN"
                technical_unknown_count += 1
            elif content_hit:
                status = f"{q['class']}_HIT"
                if q["class"] == "EXACT":
                    exact_hit_count += 1
                elif q["class"] == "VARIANT":
                    variant_hit_count += 1
                else:
                    weak_hit_count += 1
            else:
                status = f"{q['class']}_NO_HIT"

            for n in notices:
                key = (contract["family"], q["query"], n)
                if key not in notice_seen:
                    notice_seen.add(key)
                    notice_identity_candidates.append({
                        "family": contract["family"],
                        "query": q["query"],
                        "query_class": q["class"],
                        "identity": n,
                        "source_role": "COUNCIL_HISTORICAL_REVERSE_LOOKUP_ANCHOR_ONLY",
                    })

            row = {
                "family": contract["family"],
                "url": contract["url"],
                "query_field": contract["query_field"],
                "query": q["query"],
                "query_class": q["class"],
                "http": rr.get("http"),
                "final_url": rr.get("final_url"),
                "content_type": rr.get("content_type"),
                "redirects": rr.get("redirects"),
                "body_size": len(rr.get("body") or b""),
                "query_echo": query_echo,
                "error_signal": error_signal,
                "transport_ok": transport_ok,
                "query_occurrence_count": occurrence_count,
                "reported_result_count": result_count,
                "content_hit": content_hit,
                "notice_identities": notices,
                "contexts": contexts,
                "status": status,
            }
            results.append(row)
            print(json.dumps({k: row[k] for k in ["family", "query_class", "query", "http", "query_echo", "query_occurrence_count", "reported_result_count", "content_hit", "status", "notice_identities"]}, ensure_ascii=False))

    request_count = len(results)
    hit_count = exact_hit_count + variant_hit_count + weak_hit_count
    no_hit_count = sum(1 for r in results if r["status"].endswith("NO_HIT"))

    if technical_unknown_count > 0:
        classification = "SEONGNAM_CITY_COUNCIL_UQQ700_BOUNDED_TARGET_SEARCH_TECHNICAL_UNKNOWN"
        semantic = "ONE_OR_MORE_QUALIFIED_COUNCIL_TARGET_SEARCH_REQUESTS_REMAIN_TECHNICALLY_UNRESOLVED"
        next_action = "HARDEN_ONLY_TECHNICALLY_UNRESOLVED_COUNCIL_REQUESTS_WITHOUT_LEGAL_ABSENCE_INFERENCE"
    elif exact_hit_count > 0 or variant_hit_count > 0:
        classification = "SEONGNAM_CITY_COUNCIL_UQQ700_BOUNDED_TARGET_SEARCH_EXACT_OR_VARIANT_ANCHOR_OBSERVED"
        semantic = "ONE_OR_MORE_EXACT_OR_VARIANT_COUNCIL_RECORD_ANCHORS_WERE_OBSERVED_WITHOUT_DESIGNATION_OR_VALIDITY_PROMOTION"
        next_action = "REVIEW_MATCH_CONTEXT_AND_REVERSE_LOOKUP_ANY_LITERAL_OFFICIAL_NOTICE_IDENTITY_IN_THE_ORIGINAL_OFFICIAL_NOTICE_SOURCE"
    elif weak_hit_count > 0:
        classification = "SEONGNAM_CITY_COUNCIL_UQQ700_BOUNDED_TARGET_SEARCH_WEAK_CONTEXT_ONLY"
        semantic = "ONLY_WEAK_DEVELOPMENT_DENSITY_COUNCIL_CONTEXT_WAS_OBSERVED_WITHOUT_DESIGNATION_IDENTITY"
        next_action = "REVIEW_WEAK_CONTEXT_ONLY_FOR_LITERAL_NOTICE_IDENTITIES_AND_DO_NOT_PROMOTE_LEGAL_OR_SITE_STATE"
    else:
        classification = "SEONGNAM_CITY_COUNCIL_UQQ700_BOUNDED_TARGET_SEARCH_NO_TARGET_ANCHOR_OBSERVED"
        semantic = "QUALIFIED_COUNCIL_MINUTES_AND_AGENDA_TARGET_SEARCHES_COMPLETED_WITHOUT_AN_EXACT_VARIANT_OR_WEAK_TARGET_ANCHOR"
        next_action = "OPERATIONALLY_RECONCILE_COUNCIL_SOURCE_FAMILY_NON_NEGATIVELY_AND_KEEP_UQQ700_UNKNOWN"

    out = {
        "step": "STEP 17-21-C-16-8-T-160-S228D",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "contracts_used": [
            {"family": c["family"], "url": c["url"], "query_field": c["query_field"]}
            for c in CONTRACTS
        ],
        "queries": QUERIES,
        "request_count": request_count,
        "results": results,
        "counts": {
            "exact_hit": exact_hit_count,
            "variant_hit": variant_hit_count,
            "weak_hit": weak_hit_count,
            "total_hit": hit_count,
            "no_hit": no_hit_count,
            "technical_unknown": technical_unknown_count,
            "notice_identity_candidate": len(notice_identity_candidates),
        },
        "notice_identity_candidates": notice_identity_candidates,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "target_search_executed": True,
            "target_search_bounded": True,
            "qualified_contracts_only": True,
            "weak_query_is_context_only": True,
            "council_record_hit_equals_designation_notice": False,
            "council_record_hit_equals_current_validity": False,
            "council_record_hit_equals_site_inclusion": False,
            "council_record_no_hit_equals_legal_absence": False,
            "search_failure_equals_legal_absence": False,
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

    print("\n" + "=" * 78)
    print("RESULT SUMMARY")
    print("=" * 78)
    print(f"REQUEST COUNT: {request_count}")
    print(f"EXACT HIT COUNT: {exact_hit_count}")
    print(f"VARIANT HIT COUNT: {variant_hit_count}")
    print(f"WEAK HIT COUNT: {weak_hit_count}")
    print(f"NO HIT COUNT: {no_hit_count}")
    print(f"TECHNICAL UNKNOWN COUNT: {technical_unknown_count}")
    print(f"NOTICE IDENTITY CANDIDATE COUNT: {len(notice_identity_candidates)}")

    if notice_identity_candidates:
        print("\nNOTICE IDENTITY CANDIDATES")
        print("-" * 78)
        for n in notice_identity_candidates:
            print(json.dumps(n, ensure_ascii=False))

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Council record hit == designation notice: False")
    print("Council record hit == current validity: False")
    print("Council record hit == site inclusion: False")
    print("Council record no-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    allowed_contracts = {(r["family"], r["query_field"]) for r in results}
    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "exact two hardened contracts only": allowed_contracts == {("MINUTES", "keyword"), ("AGENDA", "subject")},
        "exact six bounded requests": request_count == 6,
        "exact variant weak queries only": {r["query_class"] for r in results} == {"EXACT", "VARIANT", "WEAK"},
        "target search executed": out["summary"]["target_search_executed"] is True,
        "target search bounded": out["summary"]["target_search_bounded"] is True,
        "qualified contracts only": out["summary"]["qualified_contracts_only"] is True,
        "weak query context only": out["summary"]["weak_query_is_context_only"] is True,
        "council hit not designation": out["summary"]["council_record_hit_equals_designation_notice"] is False,
        "council hit not validity": out["summary"]["council_record_hit_equals_current_validity"] is False,
        "council hit not site inclusion": out["summary"]["council_record_hit_equals_site_inclusion"] is False,
        "council no-hit not legal absence": out["summary"]["council_record_no_hit_equals_legal_absence"] is False,
        "search failure not legal absence": out["summary"]["search_failure_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "SEONGNAM_CITY_COUNCIL_UQQ700_BOUNDED_TARGET_SEARCH_TECHNICAL_UNKNOWN",
            "SEONGNAM_CITY_COUNCIL_UQQ700_BOUNDED_TARGET_SEARCH_EXACT_OR_VARIANT_ANCHOR_OBSERVED",
            "SEONGNAM_CITY_COUNCIL_UQQ700_BOUNDED_TARGET_SEARCH_WEAK_CONTEXT_ONLY",
            "SEONGNAM_CITY_COUNCIL_UQQ700_BOUNDED_TARGET_SEARCH_NO_TARGET_ANCHOR_OBSERVED",
        },
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
        raise AssertionError("S228D validation failed")


if __name__ == "__main__":
    main()
