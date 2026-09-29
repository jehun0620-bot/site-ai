# -*- coding: utf-8 -*-
"""READ-oriented source inventory for Annex 1 qualification review.

This test does not infer legal qualifications from keywords. It combines the
current official Annex 1 source, the verified structural parser, and the
production semantic registry so that qualification-bearing source text can be
reviewed without changing semantic meaning.
"""

from __future__ import annotations

from law_data.building_act_enforcement_decree_annex1_source_probe_test import (
    find_annex1,
    search_current_target,
    text_value,
)
from law_data.building_use_annex1_semantic_inventory_test import flatten_inventory
from law_data.building_use_annex1_semantic_model import (
    ACTIVE,
    MULTI_USE,
    QUALIFICATION,
    USE,
)
from law_data.building_use_annex1_semantic_registry import VERIFIED_SEMANTICS
from law_data.building_use_annex1_structural_parser_test import (
    parse_structure,
    reconstruct_body_units,
    split_annex_sections,
)
from law_data.law_detail_normalize_test import normalize_detail, request_detail


EXPECTED_STRUCTURAL_UNITS = 188


def direct_qualification_paths(parent_path: str) -> tuple[str, ...]:
    prefix = f"{parent_path}/"
    parent_depth = parent_path.count("/")
    return tuple(
        path
        for path, semantic in VERIFIED_SEMANTICS.items()
        if (
            semantic.status == ACTIVE
            and semantic.role == QUALIFICATION
            and path.startswith(prefix)
            and path.count("/") == parent_depth + 1
        )
    )


def main() -> None:
    target = search_current_target()
    data = request_detail(target)
    if data is None:
        raise AssertionError("Law detail API returned no usable data.")

    normalized = normalize_detail(data, target)
    if normalized is None:
        raise AssertionError("Law detail normalization failed.")

    annex1 = find_annex1(normalized.get("appendices", []))
    content = text_value(annex1.get("content"))
    if not content:
        raise AssertionError("Annex 1 content is empty.")

    _header_lines, body_lines, _note_lines = split_annex_sections(content)
    units = reconstruct_body_units(body_lines)
    majors = parse_structure(units)
    rows = flatten_inventory(majors)

    if len(units) != EXPECTED_STRUCTURAL_UNITS:
        raise AssertionError(
            f"Expected {EXPECTED_STRUCTURAL_UNITS} structural units; got {len(units)}."
        )
    if len(rows) != EXPECTED_STRUCTURAL_UNITS:
        raise AssertionError(
            f"Expected {EXPECTED_STRUCTURAL_UNITS} inventory rows; got {len(rows)}."
        )

    by_path = {row["source_path"]: row for row in rows}

    explicit_qualification_paths = tuple(
        path
        for path, semantic in VERIFIED_SEMANTICS.items()
        if semantic.status == ACTIVE and semantic.role == QUALIFICATION
    )

    selectable_source_paths = tuple(
        path
        for path, semantic in VERIFIED_SEMANTICS.items()
        if semantic.status == ACTIVE and semantic.role in {USE, MULTI_USE}
    )

    missing_source_rows = tuple(
        path for path in selectable_source_paths if path not in by_path
    )
    if missing_source_rows:
        raise AssertionError(
            f"Selectable semantic paths missing from official source: {missing_source_rows}"
        )

    print("HTTP status: 200")
    print("Resolved current MST:", target.get("mst"))
    print("Structural units:", len(units))
    print("Inventory rows:", len(rows))
    print("Explicit QUALIFICATION node count:", len(explicit_qualification_paths))
    print("Explicit QUALIFICATION paths:", explicit_qualification_paths)
    print("Selectable USE/MULTI_USE source path count:", len(selectable_source_paths))
    print()
    print("source_path | role | canonical_name | direct_qualification_paths | source_text")

    for path in selectable_source_paths:
        semantic = VERIFIED_SEMANTICS[path]
        row = by_path[path]
        qualification_paths = direct_qualification_paths(path)
        print(
            f"{path} | {semantic.role} | {semantic.canonical_name or '-'} | "
            f"{qualification_paths or '-'} | {row['source_text']}"
        )

    print()
    print("RESULT: PASS")
    print(
        "Meaning: official source text is paired with every currently selectable "
        "USE/MULTI_USE semantic source path, and explicit child QUALIFICATION "
        "nodes are listed without inferring hidden qualifications."
    )
    print(
        "Not proven: complete qualification coverage inside USE/MULTI_USE text, "
        "qualification meaning, qualification evaluation, frontend integration, "
        "PROJECT mapping, or Rule Engine integration."
    )


if __name__ == "__main__":
    main()
