# -*- coding: utf-8 -*-
"""Contract test for the fail-closed Annex 1 semantic model.

The examples here are limited to source paths already verified by the
structural-parser work. This test does not claim full 188-node semantics.
"""

from __future__ import annotations

from law_data.building_use_annex1_semantic_model import (
    ACTIVE,
    DELETED,
    UNRESOLVED,
    USE,
    MULTI_USE,
    CATEGORY,
    QUALIFICATION,
    SIMILAR_USE,
    OTHER_USE,
    ANCILLARY_USE,
    DELETED_ROLE,
    UNRESOLVED_ROLE,
    BuildingUseQualification,
    BuildingUseSemanticNode,
    CanonicalBuildingUse,
    SourcePath,
    qualification_paths,
    canonical_uses_for_source_path,
    canonical_uses_for_name,
    unresolved_source_paths,
)


def main() -> None:
    rental_dormitory = CanonicalBuildingUse(
        canonical_name="임대형기숙사",
        source_path=SourcePath("2", "라", 2),
        major_use="공동주택",
        parent_use="기숙사",
    )
    officetel = CanonicalBuildingUse(
        canonical_name="오피스텔",
        source_path=SourcePath("14", "나", 2),
    )

    multi_house = CanonicalBuildingUse(
        canonical_name="다중주택",
        source_path=SourcePath("1", "나"),
        qualifications=tuple(
            BuildingUseQualification(
                source_path=SourcePath("1", "나", number),
                text=f"verified source qualification {number}",
            )
            for number in range(1, 5)
        ),
    )
    multi_family_house = CanonicalBuildingUse(
        canonical_name="다가구주택",
        source_path=SourcePath("1", "다"),
        qualifications=tuple(
            BuildingUseQualification(
                source_path=SourcePath("1", "다", number),
                text=f"verified source qualification {number}",
            )
            for number in range(1, 4)
        ),
    )

    deleted_23_ra = CanonicalBuildingUse(
        canonical_name="삭제",
        source_path=SourcePath("23", "라"),
        status=DELETED,
    )
    military = CanonicalBuildingUse(
        canonical_name="국방ㆍ군사시설",
        source_path=SourcePath("23의2"),
        status=ACTIVE,
    )

    assert rental_dormitory.source_path.key == "2/라/2"
    assert officetel.source_path.key == "14/나/2"
    assert qualification_paths(multi_house) == (
        "1/나/1", "1/나/2", "1/나/3", "1/나/4"
    )
    assert qualification_paths(multi_family_house) == (
        "1/다/1", "1/다/2", "1/다/3"
    )
    assert deleted_23_ra.status == DELETED
    assert military.source_path.key == "23의2"

    academy = CanonicalBuildingUse(
        canonical_name="학원",
        source_path=SourcePath("10", "라"),
        major_use="교육연구시설",
    )
    tutoring_school = CanonicalBuildingUse(
        canonical_name="교습소",
        source_path=SourcePath("10", "라"),
        major_use="교육연구시설",
    )
    shared_source_uses = canonical_uses_for_source_path(
        (academy, tutoring_school, officetel),
        SourcePath("10", "라"),
    )
    assert tuple(use.canonical_name for use in shared_source_uses) == ("학원", "교습소")
    assert tuple(use.source_path.key for use in shared_source_uses) == ("10/라", "10/라")

    table_tennis_neighborhood = CanonicalBuildingUse(
        canonical_name="탁구장",
        source_path=SourcePath("3", "마"),
        major_use="제1종 근린생활시설",
    )
    table_tennis_sports = CanonicalBuildingUse(
        canonical_name="탁구장",
        source_path=SourcePath("13", "가"),
        major_use="운동시설",
    )
    shared_name_uses = canonical_uses_for_name(
        (table_tennis_neighborhood, table_tennis_sports, officetel),
        "탁구장",
    )
    assert tuple(use.canonical_name for use in shared_name_uses) == ("탁구장", "탁구장")
    assert tuple(use.source_path.key for use in shared_name_uses) == ("3/마", "13/가")


    semantic_nodes = (
        BuildingUseSemanticNode(SourcePath("8"), ACTIVE, CATEGORY, "운수시설"),
        BuildingUseSemanticNode(SourcePath("23의2"), ACTIVE, USE, "국방ㆍ군사시설"),
        BuildingUseSemanticNode(SourcePath("15", "가"), ACTIVE, MULTI_USE),
        BuildingUseSemanticNode(SourcePath("1", "나"), ACTIVE, USE, "다중주택"),
        BuildingUseSemanticNode(SourcePath("2", "라", 2), ACTIVE, USE, "임대형기숙사"),
        BuildingUseSemanticNode(SourcePath("1", "나", 1), ACTIVE, QUALIFICATION),
        BuildingUseSemanticNode(SourcePath("23", "라"), DELETED, DELETED_ROLE),
        BuildingUseSemanticNode(SourcePath("8", "바"), ACTIVE, SIMILAR_USE),
        BuildingUseSemanticNode(SourcePath("11", "다"), ACTIVE, OTHER_USE),
        BuildingUseSemanticNode(SourcePath("26", "다"), ACTIVE, ANCILLARY_USE),
        BuildingUseSemanticNode(SourcePath("4", "너", 1), UNRESOLVED, UNRESOLVED_ROLE),
    )
    assert tuple(node.source_path.key for node in semantic_nodes) == (
        "8", "23의2", "15/가", "1/나", "2/라/2", "1/나/1", "23/라", "8/바", "11/다", "26/다", "4/너/1"
    )
    assert tuple(node.role for node in semantic_nodes) == (
        CATEGORY, USE, MULTI_USE, USE, USE, QUALIFICATION, DELETED_ROLE, SIMILAR_USE, OTHER_USE, ANCILLARY_USE, UNRESOLVED_ROLE
    )

    for invalid in (
        (ACTIVE, CATEGORY, None),
        (UNRESOLVED, MULTI_USE, None),
        (ACTIVE, MULTI_USE, "invalid canonical"),
        (ACTIVE, QUALIFICATION, "잘못된 이름"),
        (UNRESOLVED, SIMILAR_USE, None),
        (DELETED, OTHER_USE, None),
        (UNRESOLVED, ANCILLARY_USE, None),
        (ACTIVE, SIMILAR_USE, "invalid canonical"),
    ):
        try:
            BuildingUseSemanticNode(SourcePath("99"), *invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected fail-closed rejection: {invalid}")

    # Fail closed: an unregistered structural path stays unresolved.
    unresolved = unresolved_source_paths(
        [SourcePath("2", "라", 2), SourcePath("4", "너", 1)],
        [rental_dormitory],
    )
    assert unresolved == ("4/너/1",)

    print("RESULT: PASS")
    print("2/라/2:", rental_dormitory.canonical_name)
    print("14/나/2:", officetel.canonical_name)
    print("1/나 qualifications:", qualification_paths(multi_house))
    print("1/다 qualifications:", qualification_paths(multi_family_house))
    print("23/라 status:", deleted_23_ra.status)
    print("23의2:", military.canonical_name)
    print("10/라 canonical uses:", tuple(use.canonical_name for use in shared_source_uses))
    print("탁구장 source paths:", tuple(use.source_path.key for use in shared_name_uses))
    print("Semantic role examples:", tuple(
        (node.source_path.key, node.status, node.role)
        for node in semantic_nodes
    ))
    print("Unresolved example:", unresolved)
    print("Not proven: full Annex 1 semantic coverage or Rule Engine integration.")


if __name__ == "__main__":
    main()
