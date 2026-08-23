# -*- coding: utf-8 -*-

"""
STEP 17-21-C-14-3
Dual-Source Parcel Spatial Regression

목표
======================================================================
PNU-aware spatial resolver가 SITE에 따라 올바른 Parcel source를
선택하는지 검증한다.

BASE SITE
----------------------------------------------------------------------
서울특별시 강남구 개포동 12번지
PNU: 1168010300100120000

예상:
    provider = MapPlan
    snapshot PNU match = True

LIVE SITE
----------------------------------------------------------------------
서울특별시 강남구 개포동 13번지
PNU: 1168010300100130000

예상:
    provider = VWorld
    snapshot PNU match = False
    live PNU direct verification = True

핵심 안전 원칙
======================================================================
다른 PNU에 대표 SITE snapshot geometry를 재사용하지 않는다.
"""

from __future__ import annotations

from law_data.site_spatial_payload_resolver import (
    resolve_site_spatial_payload,
)


# ============================================================
# SITE fixtures
# ============================================================

BASE_SITE = {
    "site_id": (
        "11680-10300-0012-0000"
    ),

    "pnu": (
        "1168010300100120000"
    ),

    "address": (
        "서울특별시 강남구 개포동 12번지"
    ),
}


LIVE_SITE = {
    "site_id": (
        "11680-10300-0013-0000"
    ),

    "pnu": (
        "1168010300100130000"
    ),

    "address": (
        "서울특별시 강남구 개포동 13번지"
    ),
}


# ============================================================
# main
# ============================================================

def main() -> None:

    base_result = (
        resolve_site_spatial_payload(
            BASE_SITE
        )
    )

    live_result = (
        resolve_site_spatial_payload(
            LIVE_SITE
        )
    )

    base_parcel = (
        base_result.get(
            "parcel",
            {},
        )
    )

    live_parcel = (
        live_result.get(
            "parcel",
            {},
        )
    )

    base_source = (
        base_parcel.get(
            "source",
            {},
        )
    )

    live_source = (
        live_parcel.get(
            "source",
            {},
        )
    )

    live_detail = (
        live_source.get(
            "live",
            {},
        )
    )

    # ========================================================
    # console
    # ========================================================

    print(
        "=== BASE SITE ==="
    )

    print(
        "PNU:",
        base_parcel.get(
            "pnu"
        ),
    )

    print(
        "Provider:",
        base_source.get(
            "provider"
        ),
    )

    print(
        "Snapshot match:",
        base_source.get(
            "pnu_match"
        ),
    )

    print(
        "Geometry:",
        base_parcel.get(
            "geometry_type"
        ),
    )

    print(
        "Loaded:",
        base_parcel.get(
            "geometry_loaded"
        ),
    )

    print(
        "Bounds:",
        base_parcel.get(
            "bounds"
        ),
    )

    print(
        "CRS:",
        base_parcel.get(
            "crs"
        ),
    )

    print()

    print(
        "=== LIVE SITE ==="
    )

    print(
        "PNU:",
        live_parcel.get(
            "pnu"
        ),
    )

    print(
        "Provider:",
        live_source.get(
            "provider"
        ),
    )

    print(
        "Snapshot match:",
        live_source.get(
            "pnu_match"
        ),
    )

    print(
        "Geometry:",
        live_parcel.get(
            "geometry_type"
        ),
    )

    print(
        "Loaded:",
        live_parcel.get(
            "geometry_loaded"
        ),
    )

    print(
        "Bounds:",
        live_parcel.get(
            "bounds"
        ),
    )

    print(
        "CRS:",
        live_parcel.get(
            "crs"
        ),
    )

    print(
        "Resolution:",
        live_source.get(
            "resolution"
        ),
    )

    print(
        "Live feature PNU:",
        live_detail.get(
            "feature_pnu"
        ),
    )

    print(
        "Live query:",
        live_detail.get(
            "query"
        ),
    )

    # ========================================================
    # validations
    # ========================================================

    validations = {

        # ----------------------------------------------------
        # BASE / snapshot
        # ----------------------------------------------------

        "base pnu": (
            base_parcel.get(
                "pnu"
            )
            == BASE_SITE[
                "pnu"
            ]
        ),

        "base provider MapPlan": (
            base_source.get(
                "provider"
            )
            == "MapPlan"
        ),

        "base snapshot match": (
            base_source.get(
                "pnu_match"
            )
            is True
        ),

        "base geometry loaded": (
            base_parcel.get(
                "geometry_loaded"
            )
            is True
        ),

        "base geometry polygon": (
            base_parcel.get(
                "geometry_type"
            )
            in {
                "Polygon",
                "MultiPolygon",
            }
        ),

        "base source verified": (
            base_source.get(
                "verified"
            )
            is True
        ),

        # ----------------------------------------------------
        # LIVE / VWorld
        # ----------------------------------------------------

        "live pnu": (
            live_parcel.get(
                "pnu"
            )
            == LIVE_SITE[
                "pnu"
            ]
        ),

        "live provider VWorld": (
            live_source.get(
                "provider"
            )
            == "VWorld"
        ),

        "live snapshot mismatch": (
            live_source.get(
                "pnu_match"
            )
            is False
        ),

        "live geometry loaded": (
            live_parcel.get(
                "geometry_loaded"
            )
            is True
        ),

        "live multipolygon": (
            live_parcel.get(
                "geometry_type"
            )
            == "MultiPolygon"
        ),

        "live CRS": (
            live_parcel.get(
                "crs"
            )
            == "EPSG:4326"
        ),

        "live CRS confirmed": (
            live_parcel.get(
                "crs_status"
            )
            == "CONFIRMED"
        ),

        "live bounds": (
            isinstance(
                live_parcel.get(
                    "bounds"
                ),
                list,
            )
            and len(
                live_parcel.get(
                    "bounds"
                )
            )
            == 4
        ),

        "live PNU verified": (
            live_detail.get(
                "feature_pnu"
            )
            == LIVE_SITE[
                "pnu"
            ]
        ),

        "live query success": (
            live_detail.get(
                "query",
                {},
            ).get(
                "classification"
            )
            == "QUERY_SUCCESS"
        ),

        "live resolution": (
            live_source.get(
                "resolution"
            )
            == "PNU_POLYGON_VERIFIED"
        ),

        "live source verified": (
            live_source.get(
                "verified"
            )
            is True
        ),

        # ----------------------------------------------------
        # contamination guard
        # ----------------------------------------------------

        "different PNU": (
            base_parcel.get(
                "pnu"
            )
            != live_parcel.get(
                "pnu"
            )
        ),

        "different provider": (
            base_source.get(
                "provider"
            )
            != live_source.get(
                "provider"
            )
        ),

        "different bounds": (
            base_parcel.get(
                "bounds"
            )
            != live_parcel.get(
                "bounds"
            )
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # result
    # ========================================================

    print()

    print(
        "=== VALIDATION ==="
    )

    for name, passed in (
        validations.items()
    ):

        print(
            f"{name}:",
            passed,
        )

    print()

    print(
        "all_pass:",
        all_pass,
    )

    if not all_pass:

        print()

        print(
            "FAILED:"
        )

        for name, passed in (
            validations.items()
        ):

            if not passed:

                print(
                    "-",
                    name,
                )

    raise SystemExit(
        0
        if all_pass
        else 1
    )


if __name__ == "__main__":

    main()