from site_data_model import Site
from regulation_model import Regulation


def main():

    regulation = Regulation(
        zoning="제3종일반주거지역"
    )

    site = Site(
        site_id="11680-10300-0012-0000",
        address="서울특별시 강남구 개포동 12번지",
        regulation=regulation
    )

    print("=== Site + Regulation 테스트 ===")

    print("Site ID:", site.site_id)
    print("주소:", site.address)

    print("용도지역:", site.regulation.zoning)
    print("법정 건폐율:", site.regulation.building_coverage_ratio)
    print("법정 용적률:", site.regulation.floor_area_ratio)


if __name__ == "__main__":
    main()