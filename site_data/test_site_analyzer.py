import sys
from pathlib import Path
from site_analyzer import analyze_site

# 프로젝트 루트 경로
BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.append(str(BASE_DIR / "site_data"))

from site_analyzer import analyze_site


# --------------------------------------------------
# 테스트용 Site 생성
# --------------------------------------------------

from site_builder import create_site


api_items = [

    {
        "mgmBldrgstPk": 1,
        "sigunguCd": "11680",
        "bjdongCd": "10300",
        "bun": "0012",
        "ji": "0000",

        "platPlc": "서울특별시 강남구 개포동 12번지",
        "newPlatPlc": "서울특별시 강남구 개포로109길 21",

        "dongNm": "101",
        "bldNm": "테스트아파트101동",

        "mainPurpsCdNm": "공동주택",

        "platArea": 0,
        "archArea": 500,
        "totArea": 7500,

        "bcRat": 15,
        "vlRat": 200,

        "grndFlrCnt": 15,
        "ugrndFlrCnt": 1,

        "hhldCnt": 100,

        "useAprDay": "19921014",
    },

    {
        "mgmBldrgstPk": 2,
        "sigunguCd": "11680",
        "bjdongCd": "10300",
        "bun": "0012",
        "ji": "0000",

        "platPlc": "서울특별시 강남구 개포동 12번지",
        "newPlatPlc": "서울특별시 강남구 개포로109길 21",

        "dongNm": "상가",
        "bldNm": "단지내상가",

        "mainPurpsCdNm": "판매시설",

        "platArea": 0,
        "archArea": 200,
        "totArea": 600,

        "bcRat": 10,
        "vlRat": 30,

        "grndFlrCnt": 3,
        "ugrndFlrCnt": 0,

        "hhldCnt": 0,

        "useAprDay": "19921014",
    },
]


site = create_site(api_items)
analysis = analyze_site(site)


# --------------------------------------------------
# Site 분석
# --------------------------------------------------

result = analyze_site(site)


# --------------------------------------------------
# 결과 출력
# --------------------------------------------------

print()
print("대지 분석 결과")
print("=" * 40)

print(
    "총 건축물 수:",
    result["building_count"]
)

print(
    "총 건축면적:",
    result["total_building_area"]
)

print(
    "총 연면적:",
    result["total_floor_area"]
)

print(
    "최고 지상층수:",
    result["max_ground_floor_count"]
)

print(
    "최대 지하층수:",
    result["max_underground_floor_count"]
)

print(
    "총 세대수:",
    result["total_household_count"]
)


print()
print("용도별 건축물 수")
print("-" * 40)


for use, count in result["use_count"].items():

    print(
        use,
        ":",
        count
    )