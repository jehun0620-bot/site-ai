# -*- coding: utf-8 -*-
"""Fail-closed candidate-set completeness audit for Annex 1 final-ready uses.

This audit proves structural accounting only. It deliberately does NOT claim
legal candidate-set completeness from name matching or from the absence of an
extra catalog entry. Broad semantic roles such as SIMILAR_USE remain an
explicit reason that legal completeness requires separate source review.
"""

from __future__ import annotations

from collections import defaultdict

from law_data.building_use_annex1_canonical_catalog import build_canonical_catalog
from law_data.building_use_annex1_semantic_model import (
    ANCILLARY_USE,
    OTHER_USE,
    SIMILAR_USE,
)
from law_data.building_use_annex1_semantic_registry import VERIFIED_SEMANTICS


FINAL_READINESS_NAMES = (
    "공연장",
    "단란주점",
    "동물미용실",
    "동물병원",
    "동물위탁관리업 시설",
    "방송국",
    "전기자동차 충전소",
    "종교집회장",
    "통신용 시설",
    "금융업소",
    "부동산중개사무소",
    "사무소",
    "출판사",
)

EXPECTED_PATHS = {
    "공연장": ("4/가", "5/가"),
    "단란주점": ("4/더", "16/가"),
    "동물미용실": ("3/카", "4/차"),
    "동물병원": ("3/카", "4/차"),
    "동물위탁관리업 시설": ("3/카", "4/차"),
    "방송국": ("3/바", "24/가"),
    "전기자동차 충전소": ("3/차", "20/자"),
    "종교집회장": ("4/나", "6/가"),
    "통신용 시설": ("3/아", "24/라"),
    "금융업소": ("3/자", "4/하", "14/나/1"),
    "부동산중개사무소": ("3/자", "4/하", "14/나/1"),
    "사무소": ("3/자", "4/하", "14/나/1"),
    "출판사": ("3/자", "4/하", "14/나/1"),
}


def main() -> None:
    catalog = build_canonical_catalog()
    by_name = defaultdict(list)
    for entry in catalog:
        by_name[entry.canonical_name].append(entry)

    assert len(VERIFIED_SEMANTICS) == 188
    assert set(FINAL_READINESS_NAMES) == set(EXPECTED_PATHS)

    rows = []
    for name in FINAL_READINESS_NAMES:
        entries = by_name[name]
        actual_paths = tuple(sorted(entry.source_path.key for entry in entries))
        expected_paths = tuple(sorted(EXPECTED_PATHS[name]))
        assert actual_paths == expected_paths

        semantic_rows = []
        for entry in entries:
            key = entry.source_path.key
            semantic = VERIFIED_SEMANTICS.get(key)
            assert semantic is not None
            semantic_rows.append(
                (key, entry.major_use, semantic.status, semantic.role)
            )

        rows.append((name, actual_paths, tuple(semantic_rows)))

    broad_roles = tuple(
        sorted(
            (key, node.role)
            for key, node in VERIFIED_SEMANTICS.items()
            if node.role in {SIMILAR_USE, OTHER_USE, ANCILLARY_USE}
        )
    )
    assert broad_roles == (
        ("11/다", "OTHER_USE"),
        ("15/라", "SIMILAR_USE"),
        ("19/차", "SIMILAR_USE"),
        ("21/아", "SIMILAR_USE"),
        ("24/바", "SIMILAR_USE"),
        ("26/다", "ANCILLARY_USE"),
        ("27/바", "ANCILLARY_USE"),
        ("8/바", "SIMILAR_USE"),
    )

    print("RESULT: PASS")
    print("Verified semantic node count:", len(VERIFIED_SEMANTICS))
    print("Final-readiness canonical name count:", len(FINAL_READINESS_NAMES))
    print("Structurally accounted canonical name count:", len(rows))

    print("\nCANDIDATE STRUCTURAL ACCOUNTING")
    for name, paths, semantic_rows in rows:
        print(f"- {name}: STRUCTURALLY_ACCOUNTED")
        print(f"  catalog_paths={paths}")
        for key, major_use, status, role in semantic_rows:
            print(
                f"  {key} | {major_use} | semantic_status={status} | "
                f"semantic_role={role}"
            )
        print("  legal_completeness=NOT_PROVEN")

    print("\nBROAD SEMANTIC ROLES REQUIRING FAIL-CLOSED REVIEW")
    for key, role in broad_roles:
        print(f"- {key} | {role}")

    print(
        "\nAUDIT CONCLUSION: all 13 current candidate sets are structurally "
        "accounted for in the verified 188-node semantic registry, but legal "
        "candidate-set completeness is NOT_PROVEN by structure/name matching "
        "alone."
    )
    print(
        "Not proven: absence of an additional legally equivalent candidate, "
        "scope of similar/other/ancillary-use clauses, automatic final "
        "classification, frontend integration, PROJECT mapping, or Rule Engine "
        "end-to-end integration."
    )


if __name__ == "__main__":
    main()
