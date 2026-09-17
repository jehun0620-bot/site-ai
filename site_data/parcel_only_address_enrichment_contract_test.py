# -*- coding: utf-8 -*-
"""Contract for PNU-bound parcel-only address enrichment."""
from site_data.site_analysis_orchestrator import _parcel_address_from_land_record


def main():
    mountain_pnu="1159010600200290003"
    mountain={"pnu":mountain_pnu,"ldCodeNm":"서울특별시 동작구 동작동","regstrSeCode":"2","mnnmSlno":"29-3"}
    assert _parcel_address_from_land_record(mountain,mountain_pnu)=="서울특별시 동작구 동작동 산 29-3"

    ordinary_pnu="1168010300100120000"
    ordinary={"pnu":ordinary_pnu,"ldCodeNm":"서울특별시 강남구 개포동","regstrSeCode":"1","mnnmSlno":"12"}
    assert _parcel_address_from_land_record(ordinary,ordinary_pnu)=="서울특별시 강남구 개포동 12"

    cross_pnu=dict(mountain); cross_pnu["pnu"]="1168010300100120000"
    assert _parcel_address_from_land_record(cross_pnu,mountain_pnu)==""
    assert _parcel_address_from_land_record({"pnu":mountain_pnu,"ldCodeNm":"서울특별시 동작구 동작동","regstrSeCode":"2"},mountain_pnu)==""
    assert _parcel_address_from_land_record({"pnu":mountain_pnu,"ldCodeNm":"서울특별시 동작구 동작동","regstrSeCode":"9","mnnmSlno":"29-3"},mountain_pnu)==""

    print("PARCEL_ONLY_ADDRESS_ENRICHMENT_CONTRACT_PASS")

if __name__=="__main__": main()
