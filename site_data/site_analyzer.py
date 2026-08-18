from collections import Counter


def analyze_site(site):
    """
    Site에 포함된 Building 데이터를 분석하여
    대지분석용 기초 지표를 반환한다.
    """

    buildings = site.buildings

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

        "building_count": building_count,

        "use_count": dict(use_counter),

        "total_building_area":
            total_building_area,

        "total_floor_area":
            total_floor_area,

        "max_ground_floor_count":
            max_ground_floor_count,

        "max_underground_floor_count":
            max_underground_floor_count,

        "total_household_count":
            total_household_count,
    }

    return result