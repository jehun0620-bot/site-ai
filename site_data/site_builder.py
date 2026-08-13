from site_data_model import Site
from building_converter import convert_building


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

    # 건축물 1개씩 변환
    for api_data in api_items:

        building = convert_building(api_data)

        site.buildings.append(building)

    return site