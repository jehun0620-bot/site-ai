# -*- coding: utf-8 -*-
"""Contract test for the fail-closed Annex 1 semantic model.

The examples here are limited to source paths already verified by the
structural-parser work. This test does not claim full 188-node semantics.
"""

from __future__ import annotations

from law_data.building_use_annex1_semantic_model import (
    ACTIVE,
    DELETED,
    BuildingUseQualification,
    CanonicalBuildingUse,
    SourcePath,
    qualification_paths,
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
    print("Unresolved example:", unresolved)
    print("Not proven: full Annex 1 semantic coverage or Rule Engine integration.")


if __name__ == "__main__":
    main()
