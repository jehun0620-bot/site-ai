# -*- coding: utf-8 -*-
"""Regression checks for the derived Annex 1 canonical UI catalog."""

from __future__ import annotations

from law_data.building_use_annex1_canonical_catalog import (
    build_canonical_catalog,
    catalog_entries_for_name,
)
from law_data.building_use_annex1_semantic_model import (
    ANCILLARY_USE,
    DELETED_ROLE,
    MULTI_USE,
    OTHER_USE,
    SIMILAR_USE,
    USE,
)
from law_data.building_use_annex1_semantic_registry import VERIFIED_SEMANTICS


def main() -> None:
    catalog = build_canonical_catalog()

    assert catalog
    assert all(entry.selectable is True for entry in catalog)

    by_path: dict[str, tuple[str, ...]] = {}
    for entry in catalog:
        key = entry.source_path.key
        by_path[key] = by_path.get(key, ()) + (entry.canonical_name,)

    assert by_path["2/가"] == ("아파트",)
    assert by_path["10/라"] == ("학원", "교습소")
    assert by_path["4/파"] == (
        "테니스장",
        "체력단련장",
        "에어로빅장",
        "당구장",
        "실내낚시터",
        "골프연습장",
        "볼링장",
        "놀이형시설",
    )
    assert by_path["14/나/1"] == (
        "금융업소",
        "사무소",
        "부동산중개사무소",
        "출판사",
        "신문사",
    )

    table_tennis = catalog_entries_for_name("탁구장")
    assert tuple(item.source_path.key for item in table_tennis) == ("3/마", "13/가")
    assert tuple(item.major_use for item in table_tennis) == (
        "제1종 근린생활시설",
        "운동시설",
    )

    factory = catalog_entries_for_name("공장")
    assert tuple(item.source_path.key for item in factory) == ("17",)
    assert factory[0].semantic_role == USE
    assert factory[0].major_use == "공장"

    forbidden_roles = {SIMILAR_USE, OTHER_USE, ANCILLARY_USE, DELETED_ROLE}
    forbidden_paths = {
        node.source_path.key
        for node in VERIFIED_SEMANTICS.values()
        if node.role in forbidden_roles
    }
    assert forbidden_paths.isdisjoint(by_path)

    multi_use_paths = {
        node.source_path.key
        for node in VERIFIED_SEMANTICS.values()
        if node.role == MULTI_USE
    }
    catalog_multi_use_paths = {
        entry.source_path.key
        for entry in catalog
        if entry.semantic_role == MULTI_USE
    }
    assert catalog_multi_use_paths == multi_use_paths

    print("RESULT: PASS")
    print("Catalog entry count:", len(catalog))
    print("Catalog source path count:", len(by_path))
    print("탁구장 source paths:", tuple(item.source_path.key for item in table_tennis))
    print("공장 source paths:", tuple(item.source_path.key for item in factory))
    print(
        "Excluded semantic roles:",
        tuple(sorted(forbidden_roles)),
    )
    print(
        "Not proven: qualification evaluation, frontend integration, "
        "PROJECT mapping, or Rule Engine integration."
    )


if __name__ == "__main__":
    main()
