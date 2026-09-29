# -*- coding: utf-8 -*-
"""Contract test for the explicit Annex 1 canonical-use registry."""

from __future__ import annotations

from law_data.building_use_annex1_canonical_registry import (
    CANONICAL_BUILDING_USES,
    canonical_uses_for_path,
    canonical_uses_for_canonical_name,
)
from law_data.building_use_annex1_semantic_model import SourcePath


def names_for(source_path: SourcePath) -> tuple[str, ...]:
    return tuple(use.canonical_name for use in canonical_uses_for_path(source_path))


def main() -> None:
    assert len(CANONICAL_BUILDING_USES) == 80

    assert names_for(SourcePath("10", "라")) == ("학원", "교습소")
    assert names_for(SourcePath("4", "바")) == ("사진관", "표구점")
    assert names_for(SourcePath("4", "러")) == ("안마시술소", "노래연습장")
    assert names_for(SourcePath("4", "타")) == ("독서실", "기원")
    assert names_for(SourcePath("16", "마")) == ("무도장", "무도학원")
    assert names_for(SourcePath("23", "다")) == ("소년원", "소년분류심사원")
    assert names_for(SourcePath("26", "라")) == (
        "동물화장시설", "동물건조장시설", "동물 전용의 납골시설"
    )
    assert names_for(SourcePath("19", "가")) == ("주유소", "석유 판매소")
    assert names_for(SourcePath("19", "나")) == (
        "액화석유가스 충전소", "액화석유가스 판매소", "액화석유가스 저장소"
    )
    assert names_for(SourcePath("19", "다")) == (
        "위험물 제조소", "위험물 저장소", "위험물 취급소"
    )
    assert names_for(SourcePath("19", "라")) == ("액화가스 취급소", "액화가스 판매소")
    assert names_for(SourcePath("19", "바")) == (
        "고압가스 충전소", "고압가스 판매소", "고압가스 저장소"
    )
    assert names_for(SourcePath("15", "가")) == ("일반숙박시설", "생활숙박시설")
    assert tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("탁구장")
    ) == ("3/마", "13/가")
    assert names_for(SourcePath("3", "카")) == (
        "동물병원", "동물미용실", "동물위탁관리업 시설"
    )
    assert names_for(SourcePath("4", "차")) == (
        "동물병원", "동물미용실", "동물위탁관리업 시설"
    )
    assert tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("동물병원")
    ) == ("3/카", "4/차")
    assert tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("동물미용실")
    ) == ("3/카", "4/차")
    assert tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("동물위탁관리업 시설")
    ) == ("3/카", "4/차")
    assert names_for(SourcePath("3", "마")) == ("탁구장", "체육도장")
    assert names_for(SourcePath("4", "파")) == (
        "테니스장", "체력단련장", "에어로빅장", "당구장", "실내낚시터", "골프연습장"
    )
    assert names_for(SourcePath("13", "가")) == (
        "탁구장", "체육도장", "테니스장", "체력단련장", "에어로빅장",
        "당구장", "실내낚시터", "골프연습장"
    )
    assert tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("체육도장")
    ) == ("3/마", "13/가")
    assert tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("테니스장")
    ) == ("4/파", "13/가")
    assert tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("체력단련장")
    ) == ("4/파", "13/가")
    assert tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("에어로빅장")
    ) == ("4/파", "13/가")
    assert tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("당구장")
    ) == ("4/파", "13/가")
    assert tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("실내낚시터")
    ) == ("4/파", "13/가")
    assert tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("골프연습장")
    ) == ("4/파", "13/가")

    assert names_for(SourcePath("3", "나")) == ("휴게음식점", "제과점")
    assert names_for(SourcePath("4", "아")) == ("휴게음식점", "제과점")
    assert names_for(SourcePath("3", "다")) == ("이용원", "미용원", "목욕장", "세탁소")
    assert names_for(SourcePath("3", "라")) == ("의원", "치과의원", "한의원", "침술원", "접골원", "조산원", "안마원", "산후조리원")
    assert tuple(use.source_path.key for use in canonical_uses_for_canonical_name("휴게음식점")) == ("3/나", "4/아")
    assert tuple(use.source_path.key for use in canonical_uses_for_canonical_name("제과점")) == ("3/나", "4/아")
    assert names_for(SourcePath("3", "자")) == ("금융업소", "사무소", "부동산중개사무소", "출판사")
    assert names_for(SourcePath("4", "하")) == ("금융업소", "사무소", "부동산중개사무소", "출판사")
    assert names_for(SourcePath("14", "나", 1)) == ("금융업소", "사무소", "부동산중개사무소", "출판사")
    assert tuple(use.source_path.key for use in canonical_uses_for_canonical_name("금융업소")) == ("3/자", "4/하", "14/나/1")
    assert tuple(use.source_path.key for use in canonical_uses_for_canonical_name("사무소")) == ("3/자", "4/하", "14/나/1")
    assert tuple(use.source_path.key for use in canonical_uses_for_canonical_name("부동산중개사무소")) == ("3/자", "4/하", "14/나/1")
    assert tuple(use.source_path.key for use in canonical_uses_for_canonical_name("출판사")) == ("3/자", "4/하", "14/나/1")
    assert names_for(SourcePath("99")) == ()

    assert all(use.source_path.key in {"10/라", "4/바", "4/러", "4/타", "16/마", "23/다", "26/라", "19/가", "19/나", "19/다", "19/라", "19/바", "15/가", "3/마", "13/가", "3/카", "4/차", "4/파", "3/나", "4/아", "3/다", "3/라"} for use in CANONICAL_BUILDING_USES)
    assert all(use.major_use for use in CANONICAL_BUILDING_USES)

    print("RESULT: PASS")
    print("Canonical use count:", len(CANONICAL_BUILDING_USES))
    print("10/라:", names_for(SourcePath("10", "라")))
    print("4/바:", names_for(SourcePath("4", "바")))
    print("4/러:", names_for(SourcePath("4", "러")))
    print("4/타:", names_for(SourcePath("4", "타")))
    print("16/마:", names_for(SourcePath("16", "마")))
    print("23/다:", names_for(SourcePath("23", "다")))
    print("26/라:", names_for(SourcePath("26", "라")))
    print("19/가:", names_for(SourcePath("19", "가")))
    print("19/나:", names_for(SourcePath("19", "나")))
    print("19/다:", names_for(SourcePath("19", "다")))
    print("19/라:", names_for(SourcePath("19", "라")))
    print("19/바:", names_for(SourcePath("19", "바")))
    print("15/가:", names_for(SourcePath("15", "가")))
    print("탁구장 source paths:", tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("탁구장")
    ))
    print("동물병원 source paths:", tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("동물병원")
    ))
    print("동물미용실 source paths:", tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("동물미용실")
    ))
    print("동물위탁관리업 시설 source paths:", tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("동물위탁관리업 시설")
    ))
    print("체육도장 source paths:", tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("체육도장")
    ))
    print("테니스장 source paths:", tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("테니스장")
    ))
    print("체력단련장 source paths:", tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("체력단련장")
    ))
    print("에어로빅장 source paths:", tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("에어로빅장")
    ))
    print("당구장 source paths:", tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("당구장")
    ))
    print("실내낚시터 source paths:", tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("실내낚시터")
    ))
    print("골프연습장 source paths:", tuple(
        use.source_path.key for use in canonical_uses_for_canonical_name("골프연습장")
    ))
    print("3/나:", names_for(SourcePath("3", "나")))
    print("4/아:", names_for(SourcePath("4", "아")))
    print("3/다:", names_for(SourcePath("3", "다")))
    print("3/라:", names_for(SourcePath("3", "라")))
    print("휴게음식점 source paths:", tuple(use.source_path.key for use in canonical_uses_for_canonical_name("휴게음식점")))
    print("제과점 source paths:", tuple(use.source_path.key for use in canonical_uses_for_canonical_name("제과점")))
    print("3/자:", names_for(SourcePath("3", "자")))
    print("4/하:", names_for(SourcePath("4", "하")))
    print("14/나/1:", names_for(SourcePath("14", "나", 1)))
    print("금융업소 source paths:", tuple(use.source_path.key for use in canonical_uses_for_canonical_name("금융업소")))
    print("사무소 source paths:", tuple(use.source_path.key for use in canonical_uses_for_canonical_name("사무소")))
    print("부동산중개사무소 source paths:", tuple(use.source_path.key for use in canonical_uses_for_canonical_name("부동산중개사무소")))
    print("출판사 source paths:", tuple(use.source_path.key for use in canonical_uses_for_canonical_name("출판사")))
    print("Unknown path:", names_for(SourcePath("99")))
    print("Not proven: full canonical coverage, UI integration, PROJECT mapping, or Rule Engine integration.")


if __name__ == "__main__":
    main()
