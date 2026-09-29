# -*- coding: utf-8 -*-
"""Fail-closed semantic inventory for current official Annex 1.

Every structural source node is inventoried. Semantic labels are assigned only
to paths already verified by preceding tests; all other paths remain
UNRESOLVED. No JSON or production rule data is written.
"""

from __future__ import annotations

from law_data.building_act_enforcement_decree_annex1_source_probe_test import (
    find_annex1,
    search_current_target,
    text_value,
)
from law_data.building_use_annex1_semantic_model import (
    ACTIVE,
    DELETED,
    UNRESOLVED,
    USE,
    MULTI_USE,
    CATEGORY,
    QUALIFICATION,
    DELETED_ROLE,
    UNRESOLVED_ROLE,
    BuildingUseSemanticNode,
    SourcePath,
)
from law_data.building_use_annex1_structural_parser_test import (
    parse_structure,
    reconstruct_body_units,
    split_annex_sections,
)
from law_data.law_detail_normalize_test import normalize_detail, request_detail


EXPECTED_STRUCTURAL_UNITS = 188
EXPECTED_MAJOR_COUNT = 30


# Only paths whose semantic meaning has already been verified in preceding
# tests are admitted here. Structural shape alone never creates semantics.
VERIFIED_SEMANTICS: dict[str, BuildingUseSemanticNode] = {
    "1": BuildingUseSemanticNode(SourcePath("1"), ACTIVE, CATEGORY, "단독주택"),
    "2": BuildingUseSemanticNode(SourcePath("2"), ACTIVE, CATEGORY, "공동주택"),
    "3": BuildingUseSemanticNode(SourcePath("3"), ACTIVE, CATEGORY, "제1종 근린생활시설"),
    "4": BuildingUseSemanticNode(SourcePath("4"), ACTIVE, CATEGORY, "제2종 근린생활시설"),
    "5": BuildingUseSemanticNode(SourcePath("5"), ACTIVE, CATEGORY, "문화 및 집회시설"),
    "6": BuildingUseSemanticNode(SourcePath("6"), ACTIVE, CATEGORY, "종교시설"),
    "7": BuildingUseSemanticNode(SourcePath("7"), ACTIVE, CATEGORY, "판매시설"),
    "11": BuildingUseSemanticNode(SourcePath("11"), ACTIVE, CATEGORY, "노유자시설"),
    "12": BuildingUseSemanticNode(SourcePath("12"), ACTIVE, CATEGORY, "수련시설"),
    "13": BuildingUseSemanticNode(SourcePath("13"), ACTIVE, CATEGORY, "운동시설"),
    "14": BuildingUseSemanticNode(SourcePath("14"), ACTIVE, CATEGORY, "업무시설"),
    "15": BuildingUseSemanticNode(SourcePath("15"), ACTIVE, CATEGORY, "숙박시설"),
    "16": BuildingUseSemanticNode(SourcePath("16"), ACTIVE, CATEGORY, "위락시설"),
    "19": BuildingUseSemanticNode(SourcePath("19"), ACTIVE, CATEGORY, "위험물 저장 및 처리 시설"),
    "23": BuildingUseSemanticNode(SourcePath("23"), ACTIVE, CATEGORY, "교정시설"),
    "1/가": BuildingUseSemanticNode(SourcePath("1", "가"), ACTIVE, USE, "단독주택"),
    "1/라": BuildingUseSemanticNode(SourcePath("1", "라"), ACTIVE, USE, "공관"),
    "4/다": BuildingUseSemanticNode(SourcePath("4", "다"), ACTIVE, USE, "자동차영업소"),
    "4/라": BuildingUseSemanticNode(SourcePath("4", "라"), ACTIVE, USE, "서점"),
    "4/마": BuildingUseSemanticNode(SourcePath("4", "마"), ACTIVE, USE, "총포판매소"),
    "4/자": BuildingUseSemanticNode(SourcePath("4", "자"), ACTIVE, USE, "일반음식점"),
    "4/거": BuildingUseSemanticNode(SourcePath("4", "거"), ACTIVE, USE, "다중생활시설"),
    "4/더": BuildingUseSemanticNode(SourcePath("4", "더"), ACTIVE, USE, "단란주점"),
    "4/머": BuildingUseSemanticNode(SourcePath("4", "머"), ACTIVE, USE, "주문배송시설"),
    "4/버": BuildingUseSemanticNode(SourcePath("4", "버"), ACTIVE, USE, "공유보관시설"),
    "5/가": BuildingUseSemanticNode(SourcePath("5", "가"), ACTIVE, USE, "공연장"),
    "5/나": BuildingUseSemanticNode(SourcePath("5", "나"), ACTIVE, USE, "집회장"),
    "5/다": BuildingUseSemanticNode(SourcePath("5", "다"), ACTIVE, USE, "관람장"),
    "5/라": BuildingUseSemanticNode(SourcePath("5", "라"), ACTIVE, USE, "전시장"),
    "5/마": BuildingUseSemanticNode(SourcePath("5", "마"), ACTIVE, USE, "동·식물원"),
    "6/가": BuildingUseSemanticNode(SourcePath("6", "가"), ACTIVE, USE, "종교집회장"),
    "7/가": BuildingUseSemanticNode(SourcePath("7", "가"), ACTIVE, USE, "도매시장"),
    "7/나": BuildingUseSemanticNode(SourcePath("7", "나"), ACTIVE, USE, "소매시장"),
    "12/다": BuildingUseSemanticNode(SourcePath("12", "다"), ACTIVE, USE, "유스호스텔"),
    "14/가": BuildingUseSemanticNode(SourcePath("14", "가"), ACTIVE, USE, "공공업무시설"),
    "15/다": BuildingUseSemanticNode(SourcePath("15", "다"), ACTIVE, USE, "다중생활시설"),
    "16/바": BuildingUseSemanticNode(SourcePath("16", "바"), ACTIVE, USE, "카지노영업소"),
    "15/나": BuildingUseSemanticNode(SourcePath("15", "나"), ACTIVE, USE, "관광숙박시설"),
    "19/사": BuildingUseSemanticNode(SourcePath("19", "사"), ACTIVE, USE, "도료류 판매소"),
    "19/아": BuildingUseSemanticNode(SourcePath("19", "아"), ACTIVE, USE, "도시가스 제조시설"),
    "19/자": BuildingUseSemanticNode(SourcePath("19", "자"), ACTIVE, USE, "화약류 저장소"),
    "4/바": BuildingUseSemanticNode(SourcePath("4", "바"), ACTIVE, MULTI_USE),
    "4/러": BuildingUseSemanticNode(SourcePath("4", "러"), ACTIVE, MULTI_USE),
    "4/타": BuildingUseSemanticNode(SourcePath("4", "타"), ACTIVE, MULTI_USE),
    "10/라": BuildingUseSemanticNode(SourcePath("10", "라"), ACTIVE, MULTI_USE),
    "15/가": BuildingUseSemanticNode(SourcePath("15", "가"), ACTIVE, MULTI_USE),
    "16/마": BuildingUseSemanticNode(SourcePath("16", "마"), ACTIVE, MULTI_USE),
    "19/가": BuildingUseSemanticNode(SourcePath("19", "가"), ACTIVE, MULTI_USE),
    "19/나": BuildingUseSemanticNode(SourcePath("19", "나"), ACTIVE, MULTI_USE),
    "19/다": BuildingUseSemanticNode(SourcePath("19", "다"), ACTIVE, MULTI_USE),
    "19/라": BuildingUseSemanticNode(SourcePath("19", "라"), ACTIVE, MULTI_USE),
    "19/바": BuildingUseSemanticNode(SourcePath("19", "바"), ACTIVE, MULTI_USE),
    "23/다": BuildingUseSemanticNode(SourcePath("23", "다"), ACTIVE, MULTI_USE),
    "26/라": BuildingUseSemanticNode(SourcePath("26", "라"), ACTIVE, MULTI_USE),
    "3/마": BuildingUseSemanticNode(SourcePath("3", "마"), ACTIVE, MULTI_USE),
    "3/카": BuildingUseSemanticNode(SourcePath("3", "카"), ACTIVE, MULTI_USE),
    "4/차": BuildingUseSemanticNode(SourcePath("4", "차"), ACTIVE, MULTI_USE),
    "4/파": BuildingUseSemanticNode(SourcePath("4", "파"), ACTIVE, MULTI_USE),
    "13/가": BuildingUseSemanticNode(SourcePath("13", "가"), ACTIVE, MULTI_USE),
    "4/가": BuildingUseSemanticNode(SourcePath("4", "가"), ACTIVE, USE, "공연장"),
    "4/나": BuildingUseSemanticNode(SourcePath("4", "나"), ACTIVE, USE, "종교집회장"),
    "12/라": BuildingUseSemanticNode(SourcePath("12", "라"), ACTIVE, USE, "야영장 시설"),
    "13/나": BuildingUseSemanticNode(SourcePath("13", "나"), ACTIVE, USE, "체육관"),
    "13/다": BuildingUseSemanticNode(SourcePath("13", "다"), ACTIVE, USE, "운동장"),
    "16/가": BuildingUseSemanticNode(SourcePath("16", "가"), ACTIVE, USE, "단란주점"),
    "1/나": BuildingUseSemanticNode(SourcePath("1", "나"), ACTIVE, USE, "다중주택"),
    "1/나/1": BuildingUseSemanticNode(SourcePath("1", "나", 1), ACTIVE, QUALIFICATION),
    "1/나/2": BuildingUseSemanticNode(SourcePath("1", "나", 2), ACTIVE, QUALIFICATION),
    "1/나/3": BuildingUseSemanticNode(SourcePath("1", "나", 3), ACTIVE, QUALIFICATION),
    "1/나/4": BuildingUseSemanticNode(SourcePath("1", "나", 4), ACTIVE, QUALIFICATION),
    "1/다": BuildingUseSemanticNode(SourcePath("1", "다"), ACTIVE, USE, "다가구주택"),
    "1/다/1": BuildingUseSemanticNode(SourcePath("1", "다", 1), ACTIVE, QUALIFICATION),
    "1/다/2": BuildingUseSemanticNode(SourcePath("1", "다", 2), ACTIVE, QUALIFICATION),
    "1/다/3": BuildingUseSemanticNode(SourcePath("1", "다", 3), ACTIVE, QUALIFICATION),
    "2/라/2": BuildingUseSemanticNode(SourcePath("2", "라", 2), ACTIVE, USE, "임대형기숙사"),
    "2/가": BuildingUseSemanticNode(SourcePath("2", "가"), ACTIVE, USE, "아파트"),
    "2/나": BuildingUseSemanticNode(SourcePath("2", "나"), ACTIVE, USE, "연립주택"),
    "2/다": BuildingUseSemanticNode(SourcePath("2", "다"), ACTIVE, USE, "다세대주택"),
    "2/라": BuildingUseSemanticNode(SourcePath("2", "라"), ACTIVE, USE, "기숙사"),
    "2/라/1": BuildingUseSemanticNode(SourcePath("2", "라", 1), ACTIVE, USE, "일반기숙사"),
    "4/너/1": BuildingUseSemanticNode(SourcePath("4", "너", 1), ACTIVE, QUALIFICATION),
    "4/너/2": BuildingUseSemanticNode(SourcePath("4", "너", 2), ACTIVE, QUALIFICATION),
    "7/다/1": BuildingUseSemanticNode(SourcePath("7", "다", 1), ACTIVE, QUALIFICATION),
    "7/다/2": BuildingUseSemanticNode(SourcePath("7", "다", 2), ACTIVE, QUALIFICATION),
    "16/라": BuildingUseSemanticNode(SourcePath("16", "라"), DELETED, DELETED_ROLE),
    "17": BuildingUseSemanticNode(SourcePath("17"), ACTIVE, USE, "공장"),
    "25": BuildingUseSemanticNode(SourcePath("25"), ACTIVE, USE, "발전시설"),
    "29": BuildingUseSemanticNode(SourcePath("29"), ACTIVE, USE, "야영장 시설"),
    "8": BuildingUseSemanticNode(SourcePath("8"), ACTIVE, CATEGORY, "운수시설"),
    "8/가": BuildingUseSemanticNode(SourcePath("8", "가"), ACTIVE, USE, "여객자동차터미널"),
    "8/나": BuildingUseSemanticNode(SourcePath("8", "나"), ACTIVE, USE, "철도시설"),
    "8/다": BuildingUseSemanticNode(SourcePath("8", "다"), ACTIVE, USE, "공항시설"),
    "8/라": BuildingUseSemanticNode(SourcePath("8", "라"), ACTIVE, USE, "항만시설"),
    "8/마": BuildingUseSemanticNode(SourcePath("8", "마"), ACTIVE, USE, "버티포트"),
    "9/가": BuildingUseSemanticNode(SourcePath("9", "가"), ACTIVE, USE, "병원"),
    "9/나": BuildingUseSemanticNode(SourcePath("9", "나"), ACTIVE, USE, "격리병원"),
    "10/가": BuildingUseSemanticNode(SourcePath("10", "가"), ACTIVE, USE, "학교"),
    "10/나": BuildingUseSemanticNode(SourcePath("10", "나"), ACTIVE, USE, "교육원"),
    "10/다": BuildingUseSemanticNode(SourcePath("10", "다"), ACTIVE, USE, "직업훈련소"),
    "10/마": BuildingUseSemanticNode(SourcePath("10", "마"), ACTIVE, USE, "연구소"),
    "10/바": BuildingUseSemanticNode(SourcePath("10", "바"), ACTIVE, USE, "도서관"),

    "9": BuildingUseSemanticNode(SourcePath("9"), ACTIVE, CATEGORY, "의료시설"),
    "10": BuildingUseSemanticNode(SourcePath("10"), ACTIVE, CATEGORY, "교육연구시설"),
    "18": BuildingUseSemanticNode(SourcePath("18"), ACTIVE, CATEGORY, "창고시설"),
    "18/가": BuildingUseSemanticNode(SourcePath("18","가"), ACTIVE, USE, "창고"),
    "18/나": BuildingUseSemanticNode(SourcePath("18","나"), ACTIVE, USE, "하역장"),
    "18/다": BuildingUseSemanticNode(SourcePath("18","다"), ACTIVE, USE, "물류터미널"),
    "18/라": BuildingUseSemanticNode(SourcePath("18","라"), ACTIVE, USE, "집배송 시설"),
    "20/가": BuildingUseSemanticNode(SourcePath("20","가"), ACTIVE, USE, "주차장"),
    "20/나": BuildingUseSemanticNode(SourcePath("20","나"), ACTIVE, USE, "세차장"),
    "20/다": BuildingUseSemanticNode(SourcePath("20","다"), ACTIVE, USE, "폐차장"),
    "20/라": BuildingUseSemanticNode(SourcePath("20","라"), ACTIVE, USE, "검사장"),
    "20/마": BuildingUseSemanticNode(SourcePath("20","마"), ACTIVE, USE, "매매장"),
    "20/바": BuildingUseSemanticNode(SourcePath("20","바"), ACTIVE, USE, "정비공장"),
    "20/사": BuildingUseSemanticNode(SourcePath("20","사"), ACTIVE, USE, "운전학원 및 정비학원"),
    "20/아": BuildingUseSemanticNode(SourcePath("20","아"), ACTIVE, USE, "차고 및 주기장"),
    "20/자": BuildingUseSemanticNode(SourcePath("20","자"), ACTIVE, USE, "전기자동차 충전소"),
    "21/가": BuildingUseSemanticNode(SourcePath("21","가"), ACTIVE, USE, "축사"),
    "21/나": BuildingUseSemanticNode(SourcePath("21","나"), ACTIVE, USE, "가축시설"),
    "21/다": BuildingUseSemanticNode(SourcePath("21","다"), ACTIVE, USE, "도축장"),
    "21/라": BuildingUseSemanticNode(SourcePath("21","라"), ACTIVE, USE, "도계장"),
    "21/마": BuildingUseSemanticNode(SourcePath("21","마"), ACTIVE, USE, "작물 재배사"),
    "21/바": BuildingUseSemanticNode(SourcePath("21","바"), ACTIVE, USE, "종묘배양시설"),
    "21/사": BuildingUseSemanticNode(SourcePath("21","사"), ACTIVE, USE, "온실"),
    "22/가": BuildingUseSemanticNode(SourcePath("22","가"), ACTIVE, USE, "하수 등 처리시설"),
    "22/나": BuildingUseSemanticNode(SourcePath("22","나"), ACTIVE, USE, "고물상"),
    "22/다": BuildingUseSemanticNode(SourcePath("22","다"), ACTIVE, USE, "폐기물재활용시설"),
    "22/라": BuildingUseSemanticNode(SourcePath("22","라"), ACTIVE, USE, "폐기물 처분시설"),
    "22/마": BuildingUseSemanticNode(SourcePath("22","마"), ACTIVE, USE, "폐기물감량화시설"),
    "24/가": BuildingUseSemanticNode(SourcePath("24","가"), ACTIVE, USE, "방송국"),
    "24/나": BuildingUseSemanticNode(SourcePath("24","나"), ACTIVE, USE, "전신전화국"),
    "24/다": BuildingUseSemanticNode(SourcePath("24","다"), ACTIVE, USE, "촬영소"),
    "24/라": BuildingUseSemanticNode(SourcePath("24","라"), ACTIVE, USE, "통신용 시설"),
    "24/마": BuildingUseSemanticNode(SourcePath("24","마"), ACTIVE, USE, "데이터센터"),
    "26/가": BuildingUseSemanticNode(SourcePath("26","가"), ACTIVE, USE, "화장시설"),
    "26/나": BuildingUseSemanticNode(SourcePath("26","나"), ACTIVE, USE, "봉안당"),
    "27/가": BuildingUseSemanticNode(SourcePath("27","가"), ACTIVE, USE, "야외음악당"),
    "27/나": BuildingUseSemanticNode(SourcePath("27","나"), ACTIVE, USE, "야외극장"),
    "27/다": BuildingUseSemanticNode(SourcePath("27","다"), ACTIVE, USE, "어린이회관"),
    "27/라": BuildingUseSemanticNode(SourcePath("27","라"), ACTIVE, USE, "관망탑"),
    "27/마": BuildingUseSemanticNode(SourcePath("27","마"), ACTIVE, USE, "휴게소"),
    "28/가": BuildingUseSemanticNode(SourcePath("28","가"), ACTIVE, USE, "장례식장"),
    "28/나": BuildingUseSemanticNode(SourcePath("28","나"), ACTIVE, USE, "동물 전용의 장례식장"),

    "20": BuildingUseSemanticNode(SourcePath("20"), ACTIVE, CATEGORY, "자동차 관련 시설"),
    "21": BuildingUseSemanticNode(SourcePath("21"), ACTIVE, CATEGORY, "동물 및 식물 관련 시설"),
    "22": BuildingUseSemanticNode(SourcePath("22"), ACTIVE, CATEGORY, "자원순환 관련 시설"),
    "24": BuildingUseSemanticNode(SourcePath("24"), ACTIVE, CATEGORY, "방송통신시설"),
    "26": BuildingUseSemanticNode(SourcePath("26"), ACTIVE, CATEGORY, "묘지 관련 시설"),
    "27": BuildingUseSemanticNode(SourcePath("27"), ACTIVE, CATEGORY, "관광 휴게시설"),
    "28": BuildingUseSemanticNode(SourcePath("28"), ACTIVE, CATEGORY, "장례시설"),
    "14/나/2": BuildingUseSemanticNode(SourcePath("14", "나", 2), ACTIVE, USE, "오피스텔"),
    "23/라": BuildingUseSemanticNode(SourcePath("23", "라"), DELETED, DELETED_ROLE),
    "23의2": BuildingUseSemanticNode(SourcePath("23의2"), ACTIVE, USE, "국방ㆍ군사시설"),
}

def flatten_inventory(majors: list[dict]) -> list[dict]:
    rows: list[dict] = []

    for major in majors:
        major_path = major["source_label"]
        rows.append(
            make_row(
                source_path=major_path,
                structure_kind="MAJOR",
                source_text=major["text"],
                raw_lines=major["raw_lines"],
            )
        )

        for direct in major["direct_text"]:
            # The current structural model can represent direct detail nodes,
            # but SourcePath deliberately does not invent a semantic path for
            # them. Preserve a structural display path only.
            direct_path = f'{major_path}/DETAIL-{direct["number"]}'
            rows.append(
                make_row(
                    source_path=direct_path,
                    structure_kind="DETAIL",
                    source_text=direct["text"],
                    raw_lines=direct["raw_lines"],
                )
            )

        for subitem in major["subitems"]:
            subitem_path = f'{major_path}/{subitem["code"]}'
            rows.append(
                make_row(
                    source_path=subitem_path,
                    structure_kind="SUBITEM",
                    source_text=subitem["text"],
                    raw_lines=subitem["raw_lines"],
                )
            )

            for detail in subitem["details"]:
                detail_path = f'{subitem_path}/{detail["number"]}'
                rows.append(
                    make_row(
                        source_path=detail_path,
                        structure_kind="DETAIL",
                        source_text=detail["text"],
                        raw_lines=detail["raw_lines"],
                    )
                )

    return rows


def make_row(
    *,
    source_path: str,
    structure_kind: str,
    source_text: str,
    raw_lines: list[str],
) -> dict:
    semantic = VERIFIED_SEMANTICS.get(source_path)

    if semantic is None:
        status = UNRESOLVED
        role = UNRESOLVED_ROLE
        canonical_name = None
    else:
        if semantic.source_path.key != source_path:
            raise AssertionError(
                f"Verified semantic key mismatch: {source_path} != "
                f"{semantic.source_path.key}"
            )
        status = semantic.status
        role = semantic.role
        canonical_name = semantic.canonical_name

    return {
        "source_path": source_path,
        "structure_kind": structure_kind,
        "source_text": source_text,
        "semantic_status": status,
        "semantic_role": role,
        "canonical_name": canonical_name,
        "raw_line_count": len(raw_lines),
    }


def main() -> None:
    target = search_current_target()
    data = request_detail(target)
    if data is None:
        raise AssertionError("Law detail API returned no usable data.")

    normalized = normalize_detail(data, target)
    if normalized is None:
        raise AssertionError("Law detail normalization failed.")

    annex1 = find_annex1(normalized.get("appendices", []))
    content = text_value(annex1.get("content"))
    if not content:
        raise AssertionError("Annex 1 content is empty.")

    _header_lines, body_lines, _note_lines = split_annex_sections(content)
    units = reconstruct_body_units(body_lines)
    majors = parse_structure(units)
    rows = flatten_inventory(majors)

    if len(units) != EXPECTED_STRUCTURAL_UNITS:
        raise AssertionError(
            f"Expected {EXPECTED_STRUCTURAL_UNITS} structural units; "
            f"got {len(units)}."
        )
    if len(majors) != EXPECTED_MAJOR_COUNT:
        raise AssertionError(
            f"Expected {EXPECTED_MAJOR_COUNT} majors; got {len(majors)}."
        )
    if len(rows) != EXPECTED_STRUCTURAL_UNITS:
        raise AssertionError(
            f"Expected {EXPECTED_STRUCTURAL_UNITS} inventory rows; "
            f"got {len(rows)}."
        )

    paths = [row["source_path"] for row in rows]
    if len(paths) != len(set(paths)):
        duplicates = sorted(
            path for path in set(paths)
            if paths.count(path) > 1
        )
        raise AssertionError(f"Duplicate inventory paths: {duplicates}")

    by_path = {row["source_path"]: row for row in rows}
    missing_verified = sorted(
        path for path in VERIFIED_SEMANTICS
        if path not in by_path
    )
    if missing_verified:
        raise AssertionError(
            f"Verified semantic paths missing from source: {missing_verified}"
        )

    for path, semantic in VERIFIED_SEMANTICS.items():
        row = by_path[path]
        if row["semantic_status"] != semantic.status:
            raise AssertionError(f"Status mismatch at {path}")
        if row["semantic_role"] != semantic.role:
            raise AssertionError(f"Role mismatch at {path}")
        if row["canonical_name"] != semantic.canonical_name:
            raise AssertionError(f"Canonical name mismatch at {path}")

    unresolved_rows = [
        row for row in rows
        if row["semantic_status"] == UNRESOLVED
    ]
    resolved_rows = [
        row for row in rows
        if row["semantic_status"] != UNRESOLVED
    ]

    if len(resolved_rows) != len(VERIFIED_SEMANTICS):
        raise AssertionError(
            "Inventory resolved count exceeds or misses explicitly "
            "verified semantics."
        )

    print("Resolved current MST:", target["mst"])
    print("Structural units:", len(units))
    print("Major count:", len(majors))
    print("Inventory rows:", len(rows))
    print("Verified semantic rows:", len(resolved_rows))
    print("Unresolved semantic rows:", len(unresolved_rows))
    print()
    print("source_path | structure | status | role | canonical_name | source_text")

    for row in rows:
        canonical = row["canonical_name"] or "-"
        preview = row["source_text"].replace("\n", " ")[:100]
        print(
            f'{row["source_path"]} | '
            f'{row["structure_kind"]} | '
            f'{row["semantic_status"]} | '
            f'{row["semantic_role"]} | '
            f'{canonical} | '
            f'{preview}'
        )

    print()
    print("RESULT: PASS")
    print(
        "Meaning: all 188 current structural nodes are inventoried exactly "
        "once, and only explicitly verified paths receive semantics."
    )
    print(
        "Not proven: semantic meaning of UNRESOLVED rows, full canonical "
        "coverage, qualification evaluation, PROJECT mapping, or Rule Engine "
        "integration."
    )


if __name__ == "__main__":
    main()
