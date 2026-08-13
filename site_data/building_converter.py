from site_data_model import Building


def convert_building(api_data):
    """
    건축HUB API의 건축물 데이터 1건을
    우리 시스템의 Building 객체로 변환한다.
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
        land_area=float(
            api_data.get("platArea") or 0
        ),

        building_area=float(
            api_data.get("archArea") or 0
        ),

        total_floor_area=float(
            api_data.get("totArea") or 0
        ),

        # 건폐율 / 용적률
        building_coverage_ratio=float(
            api_data.get("bcRat") or 0
        ),

        floor_area_ratio=float(
            api_data.get("vlRat") or 0
        ),

        # 층수
        ground_floor_count=int(
            api_data.get("grndFlrCnt") or 0
        ),

        underground_floor_count=int(
            api_data.get("ugrndFlrCnt") or 0
        ),

        # 세대수
        household_count=int(
            api_data.get("hhldCnt") or 0
        ),

        # 사용승인일
        approval_date=str(
            api_data.get("useAprDay") or ""
        ).strip()
    )

    return building