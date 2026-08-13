from building_converter import convert_building


# 건축HUB에서 받은 데이터와 동일한 형태의 테스트 데이터
api_data = {

    "mgmBldrgstPk": 10241936,

    "dongNm": "304",

    "bldNm": "대청아파트304동",

    "mainPurpsCdNm": "공동주택",

    "platArea": 0,

    "archArea": 592.93,

    "totArea": 8969.43,

    "bcRat": 15.96,

    "vlRat": 201.85,

    "grndFlrCnt": 15,

    "ugrndFlrCnt": 1,

    "hhldCnt": 131,

    "useAprDay": "19921014",
}


building = convert_building(api_data)


print("변환 결과")
print("--------------------------------")

print("관리번호:", building.management_id)

print("동명:", building.dong_name)

print("건물명:", building.building_name)

print("주용도:", building.main_use)

print("대지면적:", building.land_area)

print("건축면적:", building.building_area)

print("연면적:", building.total_floor_area)

print("건폐율:", building.building_coverage_ratio)

print("용적률:", building.floor_area_ratio)

print("지상층수:", building.ground_floor_count)

print("지하층수:", building.underground_floor_count)

print("세대수:", building.household_count)

print("사용승인일:", building.approval_date)