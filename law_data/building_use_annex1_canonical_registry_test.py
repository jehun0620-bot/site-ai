# -*- coding: utf-8 -*-
"""Contract test for the explicit Annex 1 canonical-use registry."""

from __future__ import annotations

from law_data.building_use_annex1_canonical_registry import (
    CANONICAL_BUILDING_USES,
    canonical_uses_for_path,
)
from law_data.building_use_annex1_semantic_model import SourcePath


def names_for(source_path: SourcePath) -> tuple[str, ...]:
    return tuple(use.canonical_name for use in canonical_uses_for_path(source_path))


def main() -> None:
    assert len(CANONICAL_BUILDING_USES) == 6

    assert names_for(SourcePath("10", "라")) == ("학원", "교습소")
    assert names_for(SourcePath("4", "바")) == ("사진관", "표구점")
    assert names_for(SourcePath("4", "러")) == ("안마시술소", "노래연습장")

    assert names_for(SourcePath("99")) == ()

    assert all(use.source_path.key in {"10/라", "4/바", "4/러"} for use in CANONICAL_BUILDING_USES)
    assert all(use.major_use for use in CANONICAL_BUILDING_USES)

    print("RESULT: PASS")
    print("Canonical use count:", len(CANONICAL_BUILDING_USES))
    print("10/라:", names_for(SourcePath("10", "라")))
    print("4/바:", names_for(SourcePath("4", "바")))
    print("4/러:", names_for(SourcePath("4", "러")))
    print("Unknown path:", names_for(SourcePath("99")))
    print("Not proven: full canonical coverage, UI integration, PROJECT mapping, or Rule Engine integration.")


if __name__ == "__main__":
    main()
