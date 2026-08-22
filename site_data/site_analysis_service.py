# -*- coding: utf-8 -*-

"""
STEP 17-21-C-12-1
SITE Analysis Service Integration

목표
======================================================================
site_data.site_builder.create_site()가 생성한 Site 객체를
law_data.site_analysis_builder.build_site_analysis()에 연결한다.

흐름
======================================================================
건축HUB API
    ↓
create_site()
    ↓
Site dataclass
    ↓
site_to_analysis_input()
    ↓
build_site_analysis()
    ↓
Final SITE Analysis Object

이 모듈은 site_data와 law_data 사이의 service adapter 역할을 한다.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


# ============================================================
# law_data import
# ============================================================

from law_data.site_analysis_builder import (
    build_site_analysis,
)


# ============================================================
# helpers
# ============================================================

def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(
        value
    ).strip()


# ============================================================
# Site -> analysis input
# ============================================================

def site_to_analysis_input(
    site: Any,
) -> Dict[str, Any]:

    """
    site_data.site_data_model.Site 객체를
    build_site_analysis()의 site_input 형식으로 변환한다.

    Site dataclass 자체에 강하게 결합하지 않기 위해
    getattr 기반으로 읽는다.
    """

    if site is None:

        raise ValueError(
            "Site 객체가 없습니다."
        )

    site_id = safe_string(
        getattr(
            site,
            "site_id",
            "",
        )
    )

    address = safe_string(
        getattr(
            site,
            "address",
            "",
        )
    )

    road_address = safe_string(
        getattr(
            site,
            "road_address",
            "",
        )
    )

    sigungu_cd = safe_string(
        getattr(
            site,
            "sigungu_cd",
            "",
        )
    )

    bjdong_cd = safe_string(
        getattr(
            site,
            "bjdong_cd",
            "",
        )
    )

    bun = safe_string(
        getattr(
            site,
            "bun",
            "",
        )
    )

    ji = safe_string(
        getattr(
            site,
            "ji",
            "",
        )
    )

        # ========================================================
    # canonical identity
    # ========================================================

    pnu = ""

    if (
        len(sigungu_cd) == 5
        and len(bjdong_cd) == 5
        and len(bun) == 4
        and len(ji) == 4
    ):

        # PNU:
        #
        # 시군구 5
        # + 법정동 5
        # + 토지구분 1
        # + 본번 4
        # + 부번 4
        #
        # 현재 Site 모델에는 산 여부가 별도로 없으므로
        # 일반 필지 land_gbn = "1"을 사용한다.
        #
        # 산번지 지원은 이후 SITE identity schema에서
        # 별도 필드로 일반화한다.

        pnu = (
            sigungu_cd
            + bjdong_cd
            + "1"
            + bun
            + ji
        )

    result = {

        # ----------------------------------------------------
        # original Site model keys
        # ----------------------------------------------------

        "site_id": (
            site_id
        ),

        "address": (
            address
        ),

        "road_address": (
            road_address
        ),

        "sigungu_cd": (
            sigungu_cd
        ),

        "bjdong_cd": (
            bjdong_cd
        ),

        "bun": (
            bun
        ),

        "ji": (
            ji
        ),

        # ----------------------------------------------------
        # canonical SITE Analysis keys
        # ----------------------------------------------------

        "sigungu_code": (
            sigungu_cd
        ),

        "bjdong_code": (
            bjdong_cd
        ),

        "main_no": (
            bun
        ),

        "sub_no": (
            ji
        ),

        "pnu": (
            pnu
        ),
    }

    # ========================================================
    # Land 정보가 있으면 보강
    # ========================================================

    land = getattr(
        site,
        "land",
        None,
    )

    if land is not None:

        zoning = safe_string(
            getattr(
                land,
                "zoning",
                "",
            )
        )

        land_area = getattr(
            land,
            "land_area",
            None,
        )

        land_category = safe_string(
            getattr(
                land,
                "land_category",
                "",
            )
        )

        district = safe_string(
            getattr(
                land,
                "district",
                "",
            )
        )

        land_use_regulation = safe_string(
            getattr(
                land,
                "land_use_regulation",
                "",
            )
        )

        if zoning:

            result[
                "zone"
            ] = (
                zoning
            )

            result[
                "land_use_zone"
            ] = (
                zoning
            )

        if (
            land_area
            is not None
        ):

            result[
                "land_area"
            ] = (
                land_area
            )

        if land_category:

            result[
                "land_category"
            ] = (
                land_category
            )

        if district:

            result[
                "district"
            ] = (
                district
            )

        if land_use_regulation:

            result[
                "land_use_regulation"
            ] = (
                land_use_regulation
            )

    return result


# ============================================================
# service API
# ============================================================

def analyze_site_object(
    site: Any,
    project_profile: Optional[
        Dict[str, str]
    ] = None,
    procedure_profile: Optional[
        Dict[str, str]
    ] = None,
) -> Dict[str, Any]:

    """
    Site 객체를 최종 SITE Analysis Object로 변환한다.
    """

    site_input = (
        site_to_analysis_input(
            site
        )
    )

    return build_site_analysis(
        site_input=(
            site_input
        ),

        project_profile=(
            project_profile
            or {}
        ),

        procedure_profile=(
            procedure_profile
            or {}
        ),
    )