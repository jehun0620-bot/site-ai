# -*- coding: utf-8 -*-
"""
Building Act Enforcement Decree Annex 1 source probe.

Purpose
-------
Read-only probe for the existing National Law Information API path.

This test does not modify production rule data or generated JSON files.
It verifies that the current API/normalization infrastructure can:

1. search the current "건축법 시행령",
2. resolve its current MST dynamically,
3. fetch the law detail through the existing request_detail() helper,
4. normalize appendices through the existing normalize_detail() helper,
5. find Annex 1 and confirm that its normalized content is non-empty.

This is source availability verification only.
It does not parse or approve Canonical Building Use semantics.
"""

from __future__ import annotations

import requests

from law_data.law_detail_normalize_test import (
    API_URL,
    HEADERS,
    SERVICE_KEY,
    normalize_detail,
    request_detail,
)


SEARCH_URL = "http://www.law.go.kr/DRF/lawSearch.do"
LAW_NAME = "건축법 시행령"


def normalize_to_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def text_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("content", "#text"):
            if key in value:
                return text_value(value.get(key))
        return ""
    return str(value).strip()


def search_current_target() -> dict:
    params = {
        "OC": SERVICE_KEY,
        "target": "law",
        "type": "JSON",
        "query": LAW_NAME,
        "display": 20,
    }

    response = requests.get(
        SEARCH_URL,
        params=params,
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    law_search = data.get("LawSearch")
    if not isinstance(law_search, dict):
        raise AssertionError("LawSearch response structure is missing.")

    candidates = normalize_to_list(law_search.get("law"))

    exact_matches = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue

        name = text_value(
            candidate.get("법령명한글")
            or candidate.get("법령명")
        )
        if name == LAW_NAME:
            exact_matches.append(candidate)

    if not exact_matches:
        raise AssertionError(
            f"Exact law search result not found: {LAW_NAME}"
        )

    candidate = exact_matches[0]
    mst = text_value(
        candidate.get("법령일련번호")
        or candidate.get("MST")
        or candidate.get("mst")
    )
    law_id = text_value(
        candidate.get("법령ID")
        or candidate.get("ID")
        or candidate.get("id")
    )

    if not mst:
        raise AssertionError("Current MST is missing from search result.")

    return {
        "level": 5,
        "type_name": "국가 시행령",
        "name": LAW_NAME,
        "target": "law",
        "mst": mst,
        "id": law_id,
    }


def normalize_numeric_code(value) -> int | None:
    text = text_value(value)

    if not text:
        return 0

    if not text.isdigit():
        return None

    return int(text)


def find_annex1(appendices: list[dict]) -> dict:
    matches = []

    for appendix in appendices:
        number = normalize_numeric_code(
            appendix.get("number")
        )
        branch_number = normalize_numeric_code(
            appendix.get("branch_number")
        )

        if number == 1 and branch_number == 0:
            matches.append(appendix)

    if len(matches) != 1:
        raise AssertionError(
            "Expected exactly one Annex 1; "
            f"found {len(matches)}."
        )

    return matches[0]


def main() -> None:
    print("=" * 70)
    print("BUILDING ACT ENFORCEMENT DECREE ANNEX 1 SOURCE PROBE")
    print("=" * 70)

    target = search_current_target()

    print("Law:", target["name"])
    print("Resolved current MST:", target["mst"])

    data = request_detail(target)
    if data is None:
        raise AssertionError("Law detail API returned no usable data.")

    normalized = normalize_detail(data, target)
    if normalized is None:
        raise AssertionError("Law detail normalization failed.")

    appendices = normalized.get("appendices", [])
    annex1 = find_annex1(appendices)

    title = text_value(annex1.get("title"))
    content = text_value(annex1.get("content"))

    print("Appendix count:", len(appendices))
    print("Annex 1 number:", annex1.get("number"))
    print("Annex 1 title:", title)
    print("Annex 1 content length:", len(content))
    print("Annex 1 PDF present:", bool(annex1.get("pdf_file") or annex1.get("pdf_link")))
    print("Annex 1 HWP present:", bool(annex1.get("hwp_file") or annex1.get("file_link")))

    if not title:
        raise AssertionError("Annex 1 title is empty.")

    if not content:
        raise AssertionError(
            "Annex 1 normalized content is empty. "
            "A file/link fallback may be required."
        )

    print("RESULT: PASS")
    print(
        "Meaning: existing API + appendix normalization can supply "
        "non-empty Annex 1 text."
    )
    print(
        "Not proven: Annex 1 internal hierarchy parsing or "
        "Canonical Building Use semantics."
    )


if __name__ == "__main__":
    main()
