from .site_data_model import Site
from .building_converter import convert_building
from .land_converter import (
    select_latest_land_record,
    convert_land_record,
)
from .vworld_api import (
    create_pnu,
    get_land_characteristics,
)


def create_site(api_items):
    """
    건축HUB API에서 받은 여러 건축물 데이터를
    하나의 Site 객체로 변환한다.
    """

    if not api_items:
        return None

    first = api_items[0]

    site = Site(

        site_id=(
            f"{first.get('sigunguCd', '')}-"
            f"{first.get('bjdongCd', '')}-"
            f"{first.get('bun', '')}-"
            f"{first.get('ji', '')}"
        ),

        address=str(
            first.get("platPlc") or ""
        ).strip(),

        road_address=str(
            first.get("newPlatPlc") or ""
        ).strip(),

        sigungu_cd=str(
            first.get("sigunguCd") or ""
        ).strip(),

        bjdong_cd=str(
            first.get("bjdongCd") or ""
        ).strip(),

        bun=str(
            first.get("bun") or ""
        ).strip(),

        ji=str(
            first.get("ji") or ""
        ).strip(),
    )

    # ========================================================
    # 건축물 변환
    # ========================================================

    for api_data in api_items:

        building = convert_building(api_data)

        site.buildings.append(building)

    # ========================================================
    # 토지 PNU 생성
    # ========================================================

    try:

        pnu = create_pnu(
            site.sigungu_cd,
            site.bjdong_cd,
            site.bun,
            site.ji,
        )

        # ====================================================
        # VWorld 토지특성정보 조회
        # ====================================================

        land_records = get_land_characteristics(pnu)

        # ====================================================
        # 최신 토지정보 선택
        # ====================================================

        latest_land_record = select_latest_land_record(
            land_records
        )

        # ====================================================
        # Land 객체 생성
        # ====================================================

        if latest_land_record:

            site.land = convert_land_record(
                latest_land_record
            )

    except Exception as e:

        print()
        print("WARNING: 토지정보를 가져오지 못했습니다.")
        print(f"오류 내용: {e}")

    return site