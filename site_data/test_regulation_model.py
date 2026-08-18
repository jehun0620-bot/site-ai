from regulation_model import Regulation


def main():

    regulation = Regulation(
        zoning="제3종일반주거지역"
    )

    print("=== Regulation 테스트 ===")

    print("용도지역:", regulation.zoning)
    print("법정 건폐율:", regulation.building_coverage_ratio)
    print("법정 용적률:", regulation.floor_area_ratio)
    print("높이 제한:", regulation.height_limit)
    print("용도 제한:", regulation.use_restriction)
    print("출처:", regulation.source)
    print("법적 근거:", regulation.legal_basis)
    print("우선순위:", regulation.priority)


if __name__ == "__main__":
    main()