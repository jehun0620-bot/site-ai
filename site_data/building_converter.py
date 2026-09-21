from .site_data_model import Building


def _optional_float(value):
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def _optional_int(value):
    if value is None or str(value).strip() == "":
        return None
    return int(value)


def convert_building(api_data):
    """
    건축HUB API의 건축물 데이터 1건을
    우리 시스템의 Building 객체로 변환한다.

    숫자 필드의 결측값은 None으로 보존하고,
    원천 API가 실제 0을 제공한 경우에만 0으로 변환한다.
    """

    building = Building(

        # 건축물 식별정보
        management_id=api_data.get("mgmBldrgstPk"),

        # 동 / 건물명
        dong_name=str(
            api_data.get("dongNm") or ""
        ).strip(),

        building_name=str(
            api_data.get("bldNm") or ""
        ).strip(),

        # 주용도
        main_use=str(
            api_data.get("mainPurpsCdNm") or ""
        ).strip(),

        # 면적
        land_area=_optional_float(
            api_data.get("platArea")
        ),

        building_area=_optional_float(
            api_data.get("archArea")
        ),

        total_floor_area=_optional_float(
            api_data.get("totArea")
        ),

        # 건폐율 / 용적률
        building_coverage_ratio=_optional_float(
            api_data.get("bcRat")
        ),

        floor_area_ratio=_optional_float(
            api_data.get("vlRat")
        ),

        # 층수
        ground_floor_count=_optional_int(
            api_data.get("grndFlrCnt")
        ),

        underground_floor_count=_optional_int(
            api_data.get("ugrndFlrCnt")
        ),

        # 세대수
        household_count=_optional_int(
            api_data.get("hhldCnt")
        ),

        # 사용승인일
        approval_date=str(
            api_data.get("useAprDay") or ""
        ).strip()
    )

    return building
