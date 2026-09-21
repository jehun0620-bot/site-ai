from .site_data_model import Site
from .building_converter import convert_building
from .land_converter import (
    hydrate_land_from_records,
)
from .vworld_api import (
    create_pnu,
    get_latest_land_characteristics,
)


def create_site(api_items):
    """건축HUB API에서 받은 여러 건축물 데이터를 하나의 Site 객체로 변환한다."""
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
        address=str(first.get("platPlc") or "").strip(),
        road_address=str(first.get("newPlatPlc") or "").strip(),
        sigungu_cd=str(first.get("sigunguCd") or "").strip(),
        bjdong_cd=str(first.get("bjdongCd") or "").strip(),
        plat_gb_cd=str(first.get("platGbCd") or "").strip(),
        bun=str(first.get("bun") or "").strip(),
        ji=str(first.get("ji") or "").strip(),
    )

    for api_data in api_items:
        site.buildings.append(convert_building(api_data))

    try:
        pnu = create_pnu(
            site.sigungu_cd,
            site.bjdong_cd,
            site.bun,
            site.ji,
            site.plat_gb_cd,
        )
        land_year, land_records = get_latest_land_characteristics(pnu)
        site.land, _ = hydrate_land_from_records(
            land_records,
            reference_year=land_year,
        )
    except Exception as e:
        print()
        print("WARNING: 토지정보를 가져오지 못했습니다.")
        print(f"오류 내용: {e}")

    return site
