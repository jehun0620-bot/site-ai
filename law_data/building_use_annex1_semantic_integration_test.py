# -*- coding: utf-8 -*-
"""Live integration test: official Annex 1 -> structural parser -> semantic model.

This test is intentionally fail-closed. It verifies only source paths whose
meaning has already been established by the preceding structural/semantic
work. It does not claim full Annex 1 semantic coverage or Rule Engine
integration.
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
    BuildingUseQualification,
    CanonicalBuildingUse,
    SourcePath,
    qualification_paths,
    unresolved_source_paths,
)
from law_data.building_use_annex1_structural_parser_test import (
    find_detail,
    find_major,
    find_subitem,
    parse_structure,
    reconstruct_body_units,
    split_annex_sections,
)
from law_data.law_detail_normalize_test import normalize_detail, request_detail


EXPECTED_STRUCTURAL_UNITS = 188
EXPECTED_MAJOR_COUNT = 30


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

    if len(units) != EXPECTED_STRUCTURAL_UNITS:
        raise AssertionError(
            f"Expected {EXPECTED_STRUCTURAL_UNITS} structural units; "
            f"got {len(units)}."
        )
    if len(majors) != EXPECTED_MAJOR_COUNT:
        raise AssertionError(
            f"Expected {EXPECTED_MAJOR_COUNT} majors; got {len(majors)}."
        )

    major2 = find_major(majors, 2)
    dormitory = find_subitem(major2, "라")
    rental_node = find_detail(dormitory, 2)
    if not rental_node["text"].startswith("임대형기숙사:"):
        raise AssertionError("Official 2/라/2 is not 임대형기숙사.")

    rental_use = CanonicalBuildingUse(
        canonical_name="임대형기숙사",
        source_path=SourcePath("2", "라", 2),
        major_use="공동주택",
        parent_use="기숙사",
        raw_lines=tuple(rental_node["raw_lines"]),
    )

    major14 = find_major(majors, 14)
    general_office = find_subitem(major14, "나")
    officetel_node = find_detail(general_office, 2)
    if not officetel_node["text"].startswith("오피스텔("):
        raise AssertionError("Official 14/나/2 is not 오피스텔.")

    officetel_use = CanonicalBuildingUse(
        canonical_name="오피스텔",
        source_path=SourcePath("14", "나", 2),
        raw_lines=tuple(officetel_node["raw_lines"]),
    )

    major1 = find_major(majors, 1)

    multi_house_node = find_subitem(major1, "나")
    multi_house_details = [
        find_detail(multi_house_node, number)
        for number in range(1, 5)
    ]
    multi_house = CanonicalBuildingUse(
        canonical_name="다중주택",
        source_path=SourcePath("1", "나"),
        qualifications=tuple(
            BuildingUseQualification(
                source_path=SourcePath("1", "나", number),
                text=node["text"],
            )
            for number, node in enumerate(multi_house_details, start=1)
        ),
        raw_lines=tuple(multi_house_node["raw_lines"]),
    )

    multi_family_node = find_subitem(major1, "다")
    multi_family_details = [
        find_detail(multi_family_node, number)
        for number in range(1, 4)
    ]
    multi_family = CanonicalBuildingUse(
        canonical_name="다가구주택",
        source_path=SourcePath("1", "다"),
        qualifications=tuple(
            BuildingUseQualification(
                source_path=SourcePath("1", "다", number),
                text=node["text"],
            )
            for number, node in enumerate(multi_family_details, start=1)
        ),
        raw_lines=tuple(multi_family_node["raw_lines"]),
    )

    major23 = find_major(majors, 23)
    deleted_node = find_subitem(major23, "라")
    if not deleted_node["text"].startswith("삭제"):
        raise AssertionError("Official 23/라 is not deleted.")

    deleted_use = CanonicalBuildingUse(
        canonical_name="삭제",
        source_path=SourcePath("23", "라"),
        status=DELETED,
        raw_lines=tuple(deleted_node["raw_lines"]),
    )

    military_node = find_major(majors, 23, 2)
    if not military_node["text"].startswith("국방ㆍ군사시설("):
        raise AssertionError("Official 23의2 is not 국방ㆍ군사시설.")

    military_use = CanonicalBuildingUse(
        canonical_name="국방ㆍ군사시설",
        source_path=SourcePath("23의2"),
        status=ACTIVE,
        raw_lines=tuple(military_node["raw_lines"]),
    )

    if qualification_paths(multi_house) != (
        "1/나/1", "1/나/2", "1/나/3", "1/나/4"
    ):
        raise AssertionError("다중주택 qualification binding changed.")

    if qualification_paths(multi_family) != (
        "1/다/1", "1/다/2", "1/다/3"
    ):
        raise AssertionError("다가구주택 qualification binding changed.")

    unresolved = unresolved_source_paths(
        [
            SourcePath("2", "라", 2),
            SourcePath("14", "나", 2),
            SourcePath("4", "너", 1),
        ],
        [rental_use, officetel_use],
    )
    if unresolved != ("4/너/1",):
        raise AssertionError(
            f"Fail-closed unresolved behavior changed: {unresolved}"
        )

    print("Resolved current MST:", target["mst"])
    print("Structural units:", len(units))
    print("Major count:", len(majors))
    print("2/라/2:", rental_use.canonical_name)
    print("14/나/2:", officetel_use.canonical_name)
    print("1/나 qualifications:", qualification_paths(multi_house))
    print("1/다 qualifications:", qualification_paths(multi_family))
    print("23/라 status:", deleted_use.status)
    print("23의2:", military_use.canonical_name)
    print("Unresolved example:", unresolved)
    print("RESULT: PASS")
    print(
        "Meaning: verified official Annex 1 source nodes can be bound to "
        "the fail-closed semantic model without changing structural meaning."
    )
    print(
        "Not proven: full 188-node semantic coverage, qualification "
        "evaluation, PROJECT mapping, or Rule Engine integration."
    )


if __name__ == "__main__":
    main()
