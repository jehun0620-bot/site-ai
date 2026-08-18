import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from regulations.residential_zones import RESIDENTIAL_ZONE_REGULATIONS


def main():

    zoning = "제3종일반주거지역"

    regulation = RESIDENTIAL_ZONE_REGULATIONS.get(zoning)

    print("=== 법규 데이터 테스트 ===")

    print("용도지역:", zoning)

    if regulation is None:
        print("법규 데이터를 찾을 수 없습니다.")
        return

    print("기본 건폐율 상한:", regulation["building_coverage_ratio"], "%")
    print("기본 용적률 상한:", regulation["floor_area_ratio"], "%")
    print("출처:", regulation["source"])
    print("법적 근거:", regulation["legal_basis"])
    print("우선순위:", regulation["priority"])


if __name__ == "__main__":
    main()