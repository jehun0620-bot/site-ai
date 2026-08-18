from site_analyzer import analyze_site
from site_builder import create_site


# --------------------------------------------------
# 테스트용 건축물 데이터
# --------------------------------------------------

api_items = [

    {
        "sigunguCd": "11680",
        "bjdongCd": "10300",
        "bun": "0012",
        "ji": "0000",

        "platPlc": "서울특별시 강남구 개포동 12번지",
        "newPlatPlc": "서울특별시 강남구 개포로109길 21",

        "mainPurpsCdNm": "공동주택",

        "archArea": "500",
        "totArea": "6000",

        "grndFlrCnt": "15",
        "ugrndFlrCnt": "1",

        "hhldCnt": "80",
    },

    {
        "sigunguCd": "11680",
        "bjdongCd": "10300",
        "bun": "0012",
        "ji": "0000",

        "platPlc": "서울특별시 강남구 개포동 12번지",
        "newPlatPlc": "서울특별시 강남구 개포로109길 21",

        "mainPurpsCdNm": "판매시설",

        "archArea": "200",
        "totArea": "2100",

        "grndFlrCnt": "3",
        "ugrndFlrCnt": "1",

        "hhldCnt": "20",
    },
]


# --------------------------------------------------
# Site 생성
# --------------------------------------------------

site = create_site(api_items)


# --------------------------------------------------
# Site 분석
# --------------------------------------------------

result = analyze_site(site)


# --------------------------------------------------
# 결과 출력
# --------------------------------------------------

print()
print("통합 대지분석 결과")
print("========================================")

print()
print("대지 정보")
print("----------------------------------------")
print(f"대지면적: {result['land_area']}")
print(f"지목: {result['land_category']}")
print(f"용도지역: {result['zoning']}")
print(f"지구: {result['district']}")
print(f"토지이용규제: {result['land_use_regulation']}")

print()
print("건축물 정보")
print("----------------------------------------")
print(f"총 건축물 수: {result['building_count']}")
print(f"총 건축면적: {result['total_building_area']}")
print(f"총 연면적: {result['total_floor_area']}")
print(f"최고 지상층수: {result['max_ground_floor_count']}")
print(f"최대 지하층수: {result['max_underground_floor_count']}")
print(f"총 세대수: {result['total_household_count']}")

print()
print("용도별 건축물 수")
print("----------------------------------------")

for use, count in result["use_count"].items():

    print(f"{use} : {count}")