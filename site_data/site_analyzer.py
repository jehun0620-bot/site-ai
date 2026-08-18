from collections import Counter


def analyze_site(site):
    """
    Site에 포함된 Land 및 Building 데이터를 분석하여
    대지분석용 기초 지표를 반환한다.
    """

    buildings = site.buildings
    land = site.land

    # --------------------------------------------------
    # 대지 정보
    # --------------------------------------------------

    if land:

        land_area = land.land_area
        land_category = land.land_category
        zoning = land.zoning
        district = land.district
        land_use_regulation = land.land_use_regulation

    else:

        land_area = 0.0
        land_category = ""
        zoning = ""
        district = ""
        land_use_regulation = ""

    # --------------------------------------------------
    # 건축물 수
    # --------------------------------------------------

    building_count = len(buildings)

    # --------------------------------------------------
    # 용도별 건축물 수
    # --------------------------------------------------

    use_counter = Counter(
        building.main_use
        for building in buildings
    )

    # --------------------------------------------------
    # 면적
    # --------------------------------------------------

    total_building_area = sum(
        building.building_area
        for building in buildings
    )

    total_floor_area = sum(
        building.total_floor_area
        for building in buildings
    )

    # --------------------------------------------------
    # 현황 건폐율 / 용적률
    # --------------------------------------------------

    if land_area > 0:

        current_building_coverage_ratio = (
            total_building_area / land_area * 100
        )

        current_floor_area_ratio = (
            total_floor_area / land_area * 100
        )

    else:

        current_building_coverage_ratio = 0.0

        current_floor_area_ratio = 0.0


    # --------------------------------------------------
    # 층수
    # --------------------------------------------------

    max_ground_floor_count = max(
        (
            building.ground_floor_count
            for building in buildings
        ),
        default=0
    )

    max_underground_floor_count = max(
        (
            building.underground_floor_count
            for building in buildings
        ),
        default=0
    )

    # --------------------------------------------------
    # 세대수
    # --------------------------------------------------

    total_household_count = sum(
        building.household_count
        for building in buildings
    )

    # --------------------------------------------------
    # 결과
    # --------------------------------------------------

    result = {

        # ==============================================
        # 대지 정보
        # ==============================================

        "land_area":
            land_area,

        "land_category":
            land_category,

        "zoning":
            zoning,

        "district":
            district,

        "land_use_regulation":
            land_use_regulation,

        # ==============================================
        # 건축물 정보
        # ==============================================

        "building_count":
            building_count,

        "use_count":
            dict(use_counter),

        "total_building_area":
            total_building_area,

        "total_floor_area":
            total_floor_area,

        "current_building_coverage_ratio":
            current_building_coverage_ratio,

        "current_floor_area_ratio":
            current_floor_area_ratio,

        "max_ground_floor_count":
            max_ground_floor_count,

        "max_underground_floor_count":
            max_underground_floor_count,

        "total_household_count":
            total_household_count,
    }

    return result