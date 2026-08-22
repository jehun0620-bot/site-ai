# -*- coding: utf-8 -*-

"""
STEP 17-21-C-13-1
Multi-SITE Readiness / Single-SITE State Leakage Audit

목표
======================================================================
현재 C-12까지 완성된 SITE Analysis Engine이
다른 SITE 입력을 받았을 때 개포동 12번지의 고정 snapshot을
재사용하는지 확인한다.

주의
======================================================================
이번 테스트의 두 번째 SITE는 실제 규제값을 검증하기 위한 것이 아니다.

오직 다음을 확인하기 위한 synthetic input이다.

- SITE identity가 입력에 따라 바뀌는가
- Parcel PNU가 SITE와 같이 바뀌는가
- Polygon이 기존 개포동 12번지에 고정되어 있는가
- numeric baseline이 기존 SITE에 고정되어 있는가
- rule summary가 입력 SITE와 무관하게 동일한가

따라서 이번 probe는 실제 법적 BCR/FAR 정답을 판단하지 않는다.
"""

from __future__ import annotations

from typing import Any, Dict


from site_data.site_data_model import (
    Land,
    Site,
)

from site_data.site_analysis_service import (
    analyze_site_object,
)


# ============================================================
# BASE SITE
# ============================================================

BASE_SITE_ID = (
    "11680-10300-0012-0000"
)

BASE_PNU = (
    "1168010300100120000"
)


# ============================================================
# helper
# ============================================================

def build_base_site() -> Site:

    site = Site(
        site_id=(
            "11680-10300-0012-0000"
        ),

        address=(
            "서울특별시 강남구 개포동 12번지"
        ),

        road_address=(
            "서울특별시 강남구 개포로109길 21 (개포동)"
        ),

        sigungu_cd=(
            "11680"
        ),

        bjdong_cd=(
            "10300"
        ),

        bun=(
            "0012"
        ),

        ji=(
            "0000"
        ),
    )

    site.land = Land(
        land_area=(
            121040.4
        ),

        land_category=(
            "대"
        ),

        zoning=(
            "제3종일반주거지역"
        ),
    )

    return site


def build_alternate_site() -> Site:

    """
    실제 법규 검증용 SITE가 아니라 state leakage 검사용 synthetic SITE.

    개포동 12번지와 명백하게 다른 identity와 zone을 사용한다.
    """

    site = Site(
        site_id=(
            "11680-10300-0013-0000"
        ),

        address=(
            "SYNTHETIC TEST SITE"
        ),

        road_address=(
            "SYNTHETIC ROAD ADDRESS"
        ),

        sigungu_cd=(
            "11680"
        ),

        bjdong_cd=(
            "10300"
        ),

        bun=(
            "0013"
        ),

        ji=(
            "0000"
        ),
    )

    site.land = Land(
        land_area=(
            1000.0
        ),

        land_category=(
            "대"
        ),

        zoning=(
            "일반상업지역"
        ),
    )

    return site


def extract_snapshot(
    result: Dict[str, Any],
) -> Dict[str, Any]:

    site = (
        result.get(
            "site",
            {},
        )
    )

    parcel = (
        site.get(
            "spatial",
            {},
        ).get(
            "parcel",
            {},
        )
    )

    regulation = (
        result.get(
            "regulation",
            {},
        )
    )

    rules = (
        result.get(
            "rule_evaluation",
            {},
        )
    )

    land_area = (
        result.get(
            "land_area",
            {},
        )
    )

    return {

        "site_id": (
            site.get(
                "site_id"
            )
        ),

        "address": (
            site.get(
                "address"
            )
        ),

        "pnu": (
            site.get(
                "pnu"
            )
        ),

        "zone": (
            site.get(
                "zone"
            )
        ),

        "parcel_pnu": (
            parcel.get(
                "pnu"
            )
        ),

        "parcel_geometry_type": (
            parcel.get(
                "geometry_type"
            )
        ),

        "parcel_bounds": (
            parcel.get(
                "bounds"
            )
        ),

        "parcel_geometry_loaded": (
            parcel.get(
                "geometry_loaded"
            )
        ),

        "official_area": (
            land_area.get(
                "official",
                {},
            ).get(
                "value"
            )
        ),

        "spatial_area": (
            land_area.get(
                "spatial",
                {},
            ).get(
                "value"
            )
        ),

        "bcr": (
            regulation.get(
                "building_coverage_ratio",
                {},
            ).get(
                "value"
            )
        ),

        "far": (
            regulation.get(
                "floor_area_ratio",
                {},
            ).get(
                "value"
            )
        ),

        "numeric_resolution": (
            regulation.get(
                "numeric_resolution"
            )
        ),

        "rules": (
            rules
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    project_profile = {
        "공동주택": (
            "TRUE"
        ),
    }

    procedure_profile = {
        "도시계획위원회심의": (
            "TRUE"
        ),
    }

    # ========================================================
    # BASE evaluation
    # ========================================================

    base_result = (
        analyze_site_object(
            site=(
                build_base_site()
            ),

            project_profile=(
                project_profile
            ),

            procedure_profile=(
                procedure_profile
            ),
        )
    )

    base = extract_snapshot(
        base_result
    )

    # ========================================================
    # ALTERNATE evaluation
    # ========================================================

    alternate_result = (
        analyze_site_object(
            site=(
                build_alternate_site()
            ),

            project_profile=(
                project_profile
            ),

            procedure_profile=(
                procedure_profile
            ),
        )
    )

    alternate = extract_snapshot(
        alternate_result
    )

    # ========================================================
    # identity
    # ========================================================

    identity_changed = (
        base[
            "site_id"
        ]
        != alternate[
            "site_id"
        ]
    )

    pnu_changed = (
        base[
            "pnu"
        ]
        != alternate[
            "pnu"
        ]
    )

    zone_changed = (
        base[
            "zone"
        ]
        != alternate[
            "zone"
        ]
    )

    official_area_changed = (
        base[
            "official_area"
        ]
        != alternate[
            "official_area"
        ]
    )

    # ========================================================
    # spatial contamination
    # ========================================================

    parcel_pnu_matches_site = (
        alternate[
            "parcel_pnu"
        ]
        == alternate[
            "pnu"
        ]
    )

    parcel_still_base_pnu = (
        alternate[
            "parcel_pnu"
        ]
        == BASE_PNU
    )

    same_parcel_bounds = (
        base[
            "parcel_bounds"
        ]
        == alternate[
            "parcel_bounds"
        ]
    )

    same_spatial_area = (
        base[
            "spatial_area"
        ]
        == alternate[
            "spatial_area"
        ]
    )

    # ========================================================
    # numeric / rule contamination indicators
    #
    # 이것 자체가 오류라고 단정하지 않는다.
    # 서로 다른 zone인데 완전히 동일한 결과라면
    # multi-site refactor가 필요한 강한 evidence로만 본다.
    # ========================================================

    same_numeric = (
        base[
            "bcr"
        ]
        == alternate[
            "bcr"
        ]
        and base[
            "far"
        ]
        == alternate[
            "far"
        ]
    )

    same_rule_summary = (
        base[
            "rules"
        ]
        == alternate[
            "rules"
        ]
    )

    # ========================================================
    # leakage classification
    # ========================================================

    spatial_leakage = (
        parcel_still_base_pnu
        or same_parcel_bounds
        or (
            same_spatial_area
            and not parcel_pnu_matches_site
        )
    )

    numeric_leakage_suspected = (
        zone_changed
        and same_numeric
    )

    rule_leakage_suspected = (
        zone_changed
        and same_rule_summary
    )

    leakage_signals = []

    if spatial_leakage:

        leakage_signals.append(
            "SPATIAL_SNAPSHOT_FIXED_TO_BASE_SITE"
        )

    if numeric_leakage_suspected:

        leakage_signals.append(
            "NUMERIC_BASELINE_SINGLE_SITE_SUSPECTED"
        )

    if rule_leakage_suspected:

        leakage_signals.append(
            "RULE_EVALUATION_SINGLE_SITE_SUSPECTED"
        )

    multi_site_ready = (
        not leakage_signals
    )

    resolution = (
        "MULTI_SITE_READY"
        if multi_site_ready
        else "MULTI_SITE_REFACTOR_REQUIRED"
    )

    # probe 자체가 성공적으로 state 차이를 읽었는지
    probe_pass = (
        identity_changed
        and pnu_changed
        and zone_changed
        and official_area_changed
    )

    # ========================================================
    # console
    # ========================================================

    print(
        "=== BASE SITE ==="
    )

    print(
        "SITE ID:",
        base[
            "site_id"
        ],
    )

    print(
        "PNU:",
        base[
            "pnu"
        ],
    )

    print(
        "Zone:",
        base[
            "zone"
        ],
    )

    print(
        "Parcel PNU:",
        base[
            "parcel_pnu"
        ],
    )

    print(
        "Official area:",
        base[
            "official_area"
        ],
    )

    print(
        "Spatial area:",
        base[
            "spatial_area"
        ],
    )

    print(
        "BCR/FAR:",
        (
            base[
                "bcr"
            ],
            base[
                "far"
            ],
        ),
    )

    print(
        "Rules:",
        base[
            "rules"
        ],
    )

    print()

    print(
        "=== ALTERNATE SITE ==="
    )

    print(
        "SITE ID:",
        alternate[
            "site_id"
        ],
    )

    print(
        "Address:",
        alternate[
            "address"
        ],
    )

    print(
        "PNU:",
        alternate[
            "pnu"
        ],
    )

    print(
        "Zone:",
        alternate[
            "zone"
        ],
    )

    print(
        "Parcel PNU:",
        alternate[
            "parcel_pnu"
        ],
    )

    print(
        "Parcel loaded:",
        alternate[
            "parcel_geometry_loaded"
        ],
    )

    print(
        "Parcel bounds:",
        alternate[
            "parcel_bounds"
        ],
    )

    print(
        "Official area:",
        alternate[
            "official_area"
        ],
    )

    print(
        "Spatial area:",
        alternate[
            "spatial_area"
        ],
    )

    print(
        "BCR/FAR:",
        (
            alternate[
                "bcr"
            ],
            alternate[
                "far"
            ],
        ),
    )

    print(
        "Rules:",
        alternate[
            "rules"
        ],
    )

    print()

    print(
        "=== LEAKAGE AUDIT ==="
    )

    print(
        "Identity changed:",
        identity_changed,
    )

    print(
        "PNU changed:",
        pnu_changed,
    )

    print(
        "Zone changed:",
        zone_changed,
    )

    print(
        "Official area changed:",
        official_area_changed,
    )

    print()

    print(
        "Parcel PNU matches SITE:",
        parcel_pnu_matches_site,
    )

    print(
        "Parcel still base PNU:",
        parcel_still_base_pnu,
    )

    print(
        "Same parcel bounds:",
        same_parcel_bounds,
    )

    print(
        "Same spatial area:",
        same_spatial_area,
    )

    print()

    print(
        "Same numeric:",
        same_numeric,
    )

    print(
        "Same rule summary:",
        same_rule_summary,
    )

    print()

    print(
        "Leakage signals:",
        leakage_signals,
    )

    print()

    print(
        "Multi-SITE ready:",
        multi_site_ready,
    )

    print(
        "Resolution:",
        resolution,
    )

    print()

    print(
        "probe_pass:",
        probe_pass,
    )

    # ========================================================
    # 이번 단계는 audit이므로 leakage 발견 자체가
    # script failure가 아니다.
    #
    # identity input을 실제로 구분해서 읽었다면 probe 성공.
    # ========================================================

    return (
        0
        if probe_pass
        else 1
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )