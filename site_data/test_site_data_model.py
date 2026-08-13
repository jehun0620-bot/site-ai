from site_data_model import Site, Building


site = Site(
    site_id="11680-10300-0012-0000",

    address="서울특별시 강남구 개포동 12번지",

    road_address="서울특별시 강남구 개포로109길 21",

    sigungu_cd="11680",
    bjdong_cd="10300",
    bun="0012",
    ji="0000",
)


building = Building(
    building_id="BUILDING-001",

    management_id=10241936,

    dong_name="304",

    building_name="대청아파트304동",

    main_use="공동주택",

    building_area=592.93,

    total_floor_area=8969.43,

    building_coverage_ratio=15.96,

    floor_area_ratio=201.85,

    ground_floor_count=15,

    underground_floor_count=1,

    household_count=131,

    approval_date="19921014",
)


site.buildings.append(building)


print("대지 정보")
print("--------------------------------")

print("SITE ID:", site.site_id)
print("주소:", site.address)
print("도로명주소:", site.road_address)

print()
print("건축물 수:", len(site.buildings))

print()
print("첫 번째 건축물")
print("--------------------------------")

b = site.buildings[0]

print("관리번호:", b.management_id)
print("동명:", b.dong_name)
print("건물명:", b.building_name)
print("주용도:", b.main_use)
print("건축면적:", b.building_area)
print("연면적:", b.total_floor_area)
print("건폐율:", b.building_coverage_ratio)
print("용적률:", b.floor_area_ratio)
print("지상층수:", b.ground_floor_count)
print("지하층수:", b.underground_floor_count)
print("세대수:", b.household_count)