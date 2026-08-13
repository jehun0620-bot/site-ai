from site_builder import create_site


api_items = [

    {
        "mgmBldrgstPk": 10241936,
        "sigunguCd": "11680",
        "bjdongCd": "10300",
        "bun": "0012",
        "ji": "0000",

        "platPlc": "서울특별시 강남구 개포동 12번지",
        "newPlatPlc": "서울특별시 강남구 개포로109길 21",

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
    },

    {
        "mgmBldrgstPk": 10241937,
        "sigunguCd": "11680",
        "bjdongCd": "10300",
        "bun": "0012",
        "ji": "0000",

        "platPlc": "서울특별시 강남구 개포동 12번지",
        "newPlatPlc": "서울특별시 강남구 개포로109길 21",

        "dongNm": "303",
        "bldNm": "대청아파트303동",

        "mainPurpsCdNm": "공동주택",

        "platArea": 0,
        "archArea": 500,
        "totArea": 8000,

        "bcRat": 15,
        "vlRat": 200,

        "grndFlrCnt": 15,
        "ugrndFlrCnt": 1,

        "hhldCnt": 120,

        "useAprDay": "19921014",
    },
]


site = create_site(api_items)


print("SITE 정보")
print("--------------------------------")

print("SITE ID:", site.site_id)

print("주소:", site.address)

print("도로명주소:", site.road_address)

print("건축물 수:", len(site.buildings))


print()
print("건축물 목록")
print("--------------------------------")


for i, building in enumerate(site.buildings, start=1):

    print(
        i,
        "|",
        building.dong_name,
        "|",
        building.building_name,
        "|",
        building.main_use
    )