# -*- coding: utf-8 -*-
"""Fail-closed semantic inventory for current official Annex 1.

Every structural source node is inventoried. Semantic labels are assigned only
to paths already verified by preceding tests; all other paths remain
UNRESOLVED. No JSON or production rule data is written.
"""

from __future__ import annotations

from law_data.building_act_enforcement_decree_annex1_source_probe_test import (
    find_annex1,
    search_current_target,
    text_value,
)
from law_data.building_use_annex1_semantic_model import (
    ACTIVE,
    DELETED,
    UNRESOLVED,
    USE,
    QUALIFICATION,
    DELETED_ROLE,
    UNRESOLVED_ROLE,
    BuildingUseSemanticNode,
    SourcePath,
)
from law_data.building_use_annex1_structural_parser_test import (
    parse_structure,
    reconstruct_body_units,
    split_annex_sections,
)
from law_data.law_detail_normalize_test import normalize_detail, request_detail


EXPECTED_STRUCTURAL_UNITS = 188
EXPECTED_MAJOR_COUNT = 30


# Only paths whose semantic meaning has already been verified in preceding
# tests are admitted here. Structural shape alone never creates semantics.
VERIFIED_SEMANTICS: dict[str, BuildingUseSemanticNode] = {
    "1/나": BuildingUseSemanticNode(SourcePath("1", "나"), ACTIVE, USE, "다중주택"),
    "1/나/1": BuildingUseSemanticNode(SourcePath("1", "나", 1), ACTIVE, QUALIFICATION),
    "1/나/2": BuildingUseSemanticNode(SourcePath("1", "나", 2), ACTIVE, QUALIFICATION),
    "1/나/3": BuildingUseSemanticNode(SourcePath("1", "나", 3), ACTIVE, QUALIFICATION),
    "1/나/4": BuildingUseSemanticNode(SourcePath("1", "나", 4), ACTIVE, QUALIFICATION),
    "1/다": BuildingUseSemanticNode(SourcePath("1", "다"), ACTIVE, USE, "다가구주택"),
    "1/다/1": BuildingUseSemanticNode(SourcePath("1", "다", 1), ACTIVE, QUALIFICATION),
    "1/다/2": BuildingUseSemanticNode(SourcePath("1", "다", 2), ACTIVE, QUALIFICATION),
    "1/다/3": BuildingUseSemanticNode(SourcePath("1", "다", 3), ACTIVE, QUALIFICATION),
    "2/라/2": BuildingUseSemanticNode(SourcePath("2", "라", 2), ACTIVE, USE, "임대형기숙사"),
    "2/가": BuildingUseSemanticNode(SourcePath("2", "가"), ACTIVE, USE, "아파트"),
    "2/나": BuildingUseSemanticNode(SourcePath("2", "나"), ACTIVE, USE, "연립주택"),
    "2/다": BuildingUseSemanticNode(SourcePath("2", "다"), ACTIVE, USE, "다세대주택"),
    "2/라": BuildingUseSemanticNode(SourcePath("2", "라"), ACTIVE, USE, "기숙사"),
    "2/라/1": BuildingUseSemanticNode(SourcePath("2", "라", 1), ACTIVE, USE, "일반기숙사"),
    "4/너/1": BuildingUseSemanticNode(SourcePath("4", "너", 1), ACTIVE, QUALIFICATION),
    "4/너/2": BuildingUseSemanticNode(SourcePath("4", "너", 2), ACTIVE, QUALIFICATION),
    "7/다/1": BuildingUseSemanticNode(SourcePath("7", "다", 1), ACTIVE, QUALIFICATION),
    "7/다/2": BuildingUseSemanticNode(SourcePath("7", "다", 2), ACTIVE, QUALIFICATION),
    "16/라": BuildingUseSemanticNode(SourcePath("16", "라"), DELETED, DELETED_ROLE),
    "17": BuildingUseSemanticNode(SourcePath("17"), ACTIVE, USE, "공장"),
    "25": BuildingUseSemanticNode(SourcePath("25"), ACTIVE, USE, "발전시설"),
    "29": BuildingUseSemanticNode(SourcePath("29"), ACTIVE, USE, "야영장 시설"),
    "14/나/2": BuildingUseSemanticNode(SourcePath("14", "나", 2), ACTIVE, USE, "오피스텔"),
    "23/라": BuildingUseSemanticNode(SourcePath("23", "라"), DELETED, DELETED_ROLE),
    "23의2": BuildingUseSemanticNode(SourcePath("23의2"), ACTIVE, USE, "국방ㆍ군사시설"),
}

def flatten_inventory(majors: list[dict]) -> list[dict]:
    rows: list[dict] = []

    for major in majors:
        major_path = major["source_label"]
        rows.append(
            make_row(
                source_path=major_path,
                structure_kind="MAJOR",
                source_text=major["text"],
                raw_lines=major["raw_lines"],
            )
        )

        for direct in major["direct_text"]:
            # The current structural model can represent direct detail nodes,
            # but SourcePath deliberately does not invent a semantic path for
            # them. Preserve a structural display path only.
            direct_path = f'{major_path}/DETAIL-{direct["number"]}'
            rows.append(
                make_row(
                    source_path=direct_path,
                    structure_kind="DETAIL",
                    source_text=direct["text"],
                    raw_lines=direct["raw_lines"],
                )
            )

        for subitem in major["subitems"]:
            subitem_path = f'{major_path}/{subitem["code"]}'
            rows.append(
                make_row(
                    source_path=subitem_path,
                    structure_kind="SUBITEM",
                    source_text=subitem["text"],
                    raw_lines=subitem["raw_lines"],
                )
            )

            for detail in subitem["details"]:
                detail_path = f'{subitem_path}/{detail["number"]}'
                rows.append(
                    make_row(
                        source_path=detail_path,
                        structure_kind="DETAIL",
                        source_text=detail["text"],
                        raw_lines=detail["raw_lines"],
                    )
                )

    return rows


def make_row(
    *,
    source_path: str,
    structure_kind: str,
    source_text: str,
    raw_lines: list[str],
) -> dict:
    semantic = VERIFIED_SEMANTICS.get(source_path)

    if semantic is None:
        status = UNRESOLVED
        role = UNRESOLVED_ROLE
        canonical_name = None
    else:
        if semantic.source_path.key != source_path:
            raise AssertionError(
                f"Verified semantic key mismatch: {source_path} != "
                f"{semantic.source_path.key}"
            )
        status = semantic.status
        role = semantic.role
        canonical_name = semantic.canonical_name

    return {
        "source_path": source_path,
        "structure_kind": structure_kind,
        "source_text": source_text,
        "semantic_status": status,
        "semantic_role": role,
        "canonical_name": canonical_name,
        "raw_line_count": len(raw_lines),
    }


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
            f"Expected {EXPECTED_STRUCTURAL_UNITS} structural units; "
            f"got {len(units)}."
        )
    if len(majors) != EXPECTED_MAJOR_COUNT:
        raise AssertionError(
            f"Expected {EXPECTED_MAJOR_COUNT} majors; got {len(majors)}."
        )
    if len(rows) != EXPECTED_STRUCTURAL_UNITS:
        raise AssertionError(
            f"Expected {EXPECTED_STRUCTURAL_UNITS} inventory rows; "
            f"got {len(rows)}."
        )

    paths = [row["source_path"] for row in rows]
    if len(paths) != len(set(paths)):
        duplicates = sorted(
            path for path in set(paths)
            if paths.count(path) > 1
        )
        raise AssertionError(f"Duplicate inventory paths: {duplicates}")

    by_path = {row["source_path"]: row for row in rows}
    missing_verified = sorted(
        path for path in VERIFIED_SEMANTICS
        if path not in by_path
    )
    if missing_verified:
        raise AssertionError(
            f"Verified semantic paths missing from source: {missing_verified}"
        )

    for path, semantic in VERIFIED_SEMANTICS.items():
        row = by_path[path]
        if row["semantic_status"] != semantic.status:
            raise AssertionError(f"Status mismatch at {path}")
        if row["semantic_role"] != semantic.role:
            raise AssertionError(f"Role mismatch at {path}")
        if row["canonical_name"] != semantic.canonical_name:
            raise AssertionError(f"Canonical name mismatch at {path}")

    unresolved_rows = [
        row for row in rows
        if row["semantic_status"] == UNRESOLVED
    ]
    resolved_rows = [
        row for row in rows
        if row["semantic_status"] != UNRESOLVED
    ]

    if len(resolved_rows) != len(VERIFIED_SEMANTICS):
        raise AssertionError(
            "Inventory resolved count exceeds or misses explicitly "
            "verified semantics."
        )

    print("Resolved current MST:", target["mst"])
    print("Structural units:", len(units))
    print("Major count:", len(majors))
    print("Inventory rows:", len(rows))
    print("Verified semantic rows:", len(resolved_rows))
    print("Unresolved semantic rows:", len(unresolved_rows))
    print()
    print("source_path | structure | status | role | canonical_name | source_text")

    for row in rows:
        canonical = row["canonical_name"] or "-"
        preview = row["source_text"].replace("\n", " ")[:100]
        print(
            f'{row["source_path"]} | '
            f'{row["structure_kind"]} | '
            f'{row["semantic_status"]} | '
            f'{row["semantic_role"]} | '
            f'{canonical} | '
            f'{preview}'
        )

    print()
    print("RESULT: PASS")
    print(
        "Meaning: all 188 current structural nodes are inventoried exactly "
        "once, and only explicitly verified paths receive semantics."
    )
    print(
        "Not proven: semantic meaning of UNRESOLVED rows, full canonical "
        "coverage, qualification evaluation, PROJECT mapping, or Rule Engine "
        "integration."
    )


if __name__ == "__main__":
    main()
