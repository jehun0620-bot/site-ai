import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================
# STEP 17-21-C-9-2-2A
# SITE 공간조회 Query Context / 필지 식별자 정규화
#
# 목적
# ------------------------------------------------------------
# 1. SITE ID에서 시군구코드 / 법정동코드 / 본번 / 부번 복원
# 2. 기존 snapshot 필드가 있으면 우선 사용
# 3. 없으면 SITE ID fallback 사용
# 4. PNU 생성
# 5. 실제 공간 API 호출 전 query context 검증
#
# SITE ID 예:
#   11680-10300-0012-0000
#
# 의미:
#   11680 : 시군구코드
#   10300 : 법정동코드
#   0012  : 본번
#   0000  : 부번
#
# PNU:
#   시군구코드 5
# + 법정동코드 5
# + 산여부 1
# + 본번 4
# + 부번 4
#
# 일반 번지 산여부 = 1
# 산번지 = 2
#
# 예:
#   1168010300100120000
# ============================================================


BASE_DIR = Path(__file__).resolve().parent

INPUT_SITE_PATH = (
    BASE_DIR
    / "output"
    / "site_law_condition_snapshot.json"
)

INPUT_SOURCE_PATH = (
    BASE_DIR
    / "output"
    / "site_spatial_source_snapshot.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "output"
    / "site_spatial_query_context.json"
)


# ============================================================
# JSON
# ============================================================

def load_json(path: Path) -> Any:
    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_json(
    path: Path,
    data: Any,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# 공통 탐색
# ============================================================

def recursive_find_value(
    obj: Any,
    target_keys: List[str],
) -> Optional[Any]:

    if isinstance(obj, dict):

        for key in target_keys:

            if (
                key in obj
                and obj[key] not in (
                    None,
                    "",
                )
            ):
                return obj[key]

        for value in obj.values():

            result = recursive_find_value(
                value,
                target_keys,
            )

            if result not in (
                None,
                "",
            ):
                return result

    elif isinstance(obj, list):

        for value in obj:

            result = recursive_find_value(
                value,
                target_keys,
            )

            if result not in (
                None,
                "",
            ):
                return result

    return None


def clean_code(
    value: Any,
) -> str:

    if value is None:
        return ""

    value = str(value).strip()

    if value in {
        "",
        "-",
        "None",
        "null",
    }:
        return ""

    return value


# ============================================================
# SITE 기본정보
# ============================================================

def extract_basic_site_info(
    site_data: Any,
) -> Dict[str, str]:

    return {

        "site_id": clean_code(
            recursive_find_value(
                site_data,
                [
                    "site_id",
                    "SITE ID",
                    "id",
                ],
            )
        ),

        "address": clean_code(
            recursive_find_value(
                site_data,
                [
                    "address",
                    "주소",
                    "jibun_address",
                    "parcel_address",
                ],
            )
        ),

        "road_address": clean_code(
            recursive_find_value(
                site_data,
                [
                    "road_address",
                    "도로명주소",
                    "roadAddress",
                ],
            )
        ),

        "zone": clean_code(
            recursive_find_value(
                site_data,
                [
                    "zone",
                    "용도지역",
                    "land_use_zone",
                    "use_zone",
                    "zoning",
                ],
            )
        ),

        "sigungu_code": clean_code(
            recursive_find_value(
                site_data,
                [
                    "sigungu_code",
                    "시군구코드",
                    "sigunguCd",
                ],
            )
        ),

        "bjdong_code": clean_code(
            recursive_find_value(
                site_data,
                [
                    "bjdong_code",
                    "법정동코드",
                    "bjdongCd",
                ],
            )
        ),

        "main_no": clean_code(
            recursive_find_value(
                site_data,
                [
                    "main_no",
                    "본번",
                    "bun",
                ],
            )
        ),

        "sub_no": clean_code(
            recursive_find_value(
                site_data,
                [
                    "sub_no",
                    "부번",
                    "ji",
                ],
            )
        ),
    }


# ============================================================
# SITE ID 파싱
# ============================================================

def parse_site_id(
    site_id: str,
) -> Dict[str, str]:

    result = {
        "sigungu_code": "",
        "bjdong_code": "",
        "main_no": "",
        "sub_no": "",
    }

    if not site_id:
        return result

    match = re.fullmatch(
        r"(\d{5})-(\d{5})-(\d{1,4})-(\d{1,4})",
        site_id.strip(),
    )

    if not match:
        return result

    result[
        "sigungu_code"
    ] = match.group(1)

    result[
        "bjdong_code"
    ] = match.group(2)

    result[
        "main_no"
    ] = match.group(3).zfill(4)

    result[
        "sub_no"
    ] = match.group(4).zfill(4)

    return result


# ============================================================
# 산 여부
# ============================================================

def detect_mountain_flag(
    address: str,
) -> str:
    """
    PNU 산여부 코드

    일반번지: 1
    산번지: 2
    """

    if re.search(
        r"(?:^|\s)산\s*\d+",
        address or "",
    ):
        return "2"

    return "1"


# ============================================================
# Query Context 생성
# ============================================================

def normalize_site_context(
    site_data: Any,
) -> Dict[str, Any]:

    basic = extract_basic_site_info(
        site_data
    )

    parsed = parse_site_id(
        basic[
            "site_id"
        ]
    )

    sigungu_code = (
        basic[
            "sigungu_code"
        ]
        or parsed[
            "sigungu_code"
        ]
    )

    bjdong_code = (
        basic[
            "bjdong_code"
        ]
        or parsed[
            "bjdong_code"
        ]
    )

    main_no = (
        basic[
            "main_no"
        ]
        or parsed[
            "main_no"
        ]
    )

    sub_no = (
        basic[
            "sub_no"
        ]
        or parsed[
            "sub_no"
        ]
        or "0000"
    )

    if main_no:
        main_no = main_no.zfill(
            4
        )

    if sub_no:
        sub_no = sub_no.zfill(
            4
        )

    mountain_flag = detect_mountain_flag(
        basic[
            "address"
        ]
    )

    pnu = ""

    if (
        len(sigungu_code) == 5
        and len(bjdong_code) == 5
        and len(main_no) == 4
        and len(sub_no) == 4
    ):
        pnu = (
            sigungu_code
            + bjdong_code
            + mountain_flag
            + main_no
            + sub_no
        )

    parcel_key = ""

    if (
        sigungu_code
        and bjdong_code
        and main_no
    ):
        parcel_key = (
            f"{sigungu_code}-"
            f"{bjdong_code}-"
            f"{main_no}-"
            f"{sub_no}"
        )

    return {

        "site_id":
            basic[
                "site_id"
            ],

        "address":
            basic[
                "address"
            ],

        "road_address":
            basic[
                "road_address"
            ],

        "zone":
            basic[
                "zone"
            ],

        "sigungu_code":
            sigungu_code,

        "bjdong_code":
            bjdong_code,

        "mountain_flag":
            mountain_flag,

        "main_no":
            main_no,

        "sub_no":
            sub_no,

        "parcel_key":
            parcel_key,

        "pnu":
            pnu,

        "source": {

            "sigungu_code": (
                "snapshot"
                if basic[
                    "sigungu_code"
                ]
                else (
                    "site_id"
                    if parsed[
                        "sigungu_code"
                    ]
                    else None
                )
            ),

            "bjdong_code": (
                "snapshot"
                if basic[
                    "bjdong_code"
                ]
                else (
                    "site_id"
                    if parsed[
                        "bjdong_code"
                    ]
                    else None
                )
            ),

            "main_no": (
                "snapshot"
                if basic[
                    "main_no"
                ]
                else (
                    "site_id"
                    if parsed[
                        "main_no"
                    ]
                    else None
                )
            ),

            "sub_no": (
                "snapshot"
                if basic[
                    "sub_no"
                ]
                else (
                    "site_id"
                    if parsed[
                        "sub_no"
                    ]
                    else None
                )
            ),
        },
    }


# ============================================================
# 검증
# ============================================================

def validation_site_id_format(
    context: Dict[str, Any],
) -> bool:

    return bool(
        re.fullmatch(
            r"\d{5}-\d{5}-\d{4}-\d{4}",
            context.get(
                "parcel_key",
                "",
            ),
        )
    )


def validation_sigungu_code(
    context: Dict[str, Any],
) -> bool:

    return bool(
        re.fullmatch(
            r"\d{5}",
            context.get(
                "sigungu_code",
                "",
            ),
        )
    )


def validation_bjdong_code(
    context: Dict[str, Any],
) -> bool:

    return bool(
        re.fullmatch(
            r"\d{5}",
            context.get(
                "bjdong_code",
                "",
            ),
        )
    )


def validation_main_no(
    context: Dict[str, Any],
) -> bool:

    return bool(
        re.fullmatch(
            r"\d{4}",
            context.get(
                "main_no",
                "",
            ),
        )
    )


def validation_sub_no(
    context: Dict[str, Any],
) -> bool:

    return bool(
        re.fullmatch(
            r"\d{4}",
            context.get(
                "sub_no",
                "",
            ),
        )
    )


def validation_mountain_flag(
    context: Dict[str, Any],
) -> bool:

    return (
        context.get(
            "mountain_flag"
        )
        in {
            "1",
            "2",
        }
    )


def validation_pnu(
    context: Dict[str, Any],
) -> bool:

    return bool(
        re.fullmatch(
            r"\d{19}",
            context.get(
                "pnu",
                "",
            ),
        )
    )


def validation_target_example(
    context: Dict[str, Any],
) -> bool:
    """
    현재 검증 SITE:
    서울 강남구 개포동 12번지
    """

    if (
        context.get(
            "site_id"
        )
        != "11680-10300-0012-0000"
    ):
        return True

    return (
        context.get(
            "sigungu_code"
        )
        == "11680"
        and context.get(
            "bjdong_code"
        )
        == "10300"
        and context.get(
            "main_no"
        )
        == "0012"
        and context.get(
            "sub_no"
        )
        == "0000"
        and context.get(
            "mountain_flag"
        )
        == "1"
        and context.get(
            "pnu"
        )
        == "1168010300100120000"
    )


def run_validations(
    context: Dict[str, Any],
) -> Dict[str, bool]:

    return {

        "parcel key 생성":
            validation_site_id_format(
                context
            ),

        "시군구코드 5자리":
            validation_sigungu_code(
                context
            ),

        "법정동코드 5자리":
            validation_bjdong_code(
                context
            ),

        "본번 4자리":
            validation_main_no(
                context
            ),

        "부번 4자리":
            validation_sub_no(
                context
            ),

        "산여부 코드":
            validation_mountain_flag(
                context
            ),

        "PNU 19자리":
            validation_pnu(
                context
            ),

        "개포동 12번지 기준값":
            validation_target_example(
                context
            ),
    }


# ============================================================
# Main
# ============================================================

def print_separator(
    char: str = "=",
    width: int = 70,
) -> None:

    print(
        char * width
    )


def main() -> None:

    print(
        "=== STEP 17-21-C-9-2-2A "
        "SITE 공간조회 Query Context 정규화 테스트 ==="
    )

    print()

    print(
        "SITE 입력:"
    )

    print(
        INPUT_SITE_PATH
    )

    print()

    print(
        "Source Registry 입력:"
    )

    print(
        INPUT_SOURCE_PATH
    )

    print()

    if not INPUT_SITE_PATH.exists():

        raise FileNotFoundError(
            f"SITE 입력 파일이 없습니다: "
            f"{INPUT_SITE_PATH}"
        )

    if not INPUT_SOURCE_PATH.exists():

        raise FileNotFoundError(
            f"Source Registry 파일이 없습니다: "
            f"{INPUT_SOURCE_PATH}"
        )

    site_data = load_json(
        INPUT_SITE_PATH
    )

    source_data = load_json(
        INPUT_SOURCE_PATH
    )

    context = normalize_site_context(
        site_data
    )

    print_separator()
    print(
        "=== 정규화된 SITE Query Context ==="
    )
    print_separator()

    print(
        "SITE ID:",
        context.get(
            "site_id"
        )
        or "-",
    )

    print(
        "주소:",
        context.get(
            "address"
        )
        or "-",
    )

    print(
        "용도지역:",
        context.get(
            "zone"
        )
        or "-",
    )

    print()

    print(
        "시군구코드:",
        context.get(
            "sigungu_code"
        )
        or "-",
    )

    print(
        "법정동코드:",
        context.get(
            "bjdong_code"
        )
        or "-",
    )

    print(
        "산여부:",
        context.get(
            "mountain_flag"
        )
        or "-",
    )

    print(
        "본번:",
        context.get(
            "main_no"
        )
        or "-",
    )

    print(
        "부번:",
        context.get(
            "sub_no"
        )
        or "-",
    )

    print()

    print(
        "Parcel Key:",
        context.get(
            "parcel_key"
        )
        or "-",
    )

    print(
        "PNU:",
        context.get(
            "pnu"
        )
        or "-",
    )

    print()

    print(
        "필드 복원 source:"
    )

    for key, value in (
        context.get(
            "source",
            {}
        )
        .items()
    ):
        print(
            f"- {key}: "
            f"{value or '-'}"
        )

    validations = run_validations(
        context
    )

    print()

    print_separator()
    print(
        "=== C-9-2-2A 검증 ==="
    )
    print_separator()

    for name, passed in (
        validations.items()
    ):

        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    all_pass = all(
        validations.values()
    )

    output_data = {

        "step":
            "STEP 17-21-C-9-2-2A",

        "query_context":
            context,

        "validations":
            validations,

        "all_pass":
            all_pass,

        "next_source_plan": {

            "primary": {
                "provider":
                    "국토교통부 / VWorld",
                "dataset":
                    "지구단위계획",
                "purpose":
                    "실제 도형 기반 공간조회",
            },

            "secondary": {
                "provider":
                    "서울특별시 열린데이터광장",
                "service":
                    "upisCUq161",
                "purpose":
                    "서울시 지구단위계획구역 속성 교차검증",
            },
        },

        "source_registry_step":
            source_data.get(
                "step"
            ),
    }

    save_json(
        OUTPUT_PATH,
        output_data,
    )

    print()

    print_separator()
    print(
        "결과 저장:"
    )
    print(
        OUTPUT_PATH
    )
    print_separator()

    print()

    if all_pass:

        print(
            "STEP 17-21-C-9-2-2A 완료"
        )

        print()

        print(
            "SITE 공간조회 Query Context 검증: ALL PASS"
        )

        print()

        print(
            "다음 단계:"
        )

        print(
            "STEP 17-21-C-9-2-2B"
        )

        print(
            "→ VWorld 지구단위계획 공간 API 연결"
        )

        print(
            "→ 필지 좌표/도형 확보"
        )

        print(
            "→ 지구단위계획 도형과 실제 교차 조회"
        )

        print(
            "→ 서울시 upisCUq161 결과와 보조 검증"
        )

        print(
            "→ 조회 성공 시에만 "
            "지구단위계획 TRUE/FALSE 확정"
        )

    else:

        print(
            "STEP 17-21-C-9-2-2A 검증 실패"
        )

        print()

        print(
            "필지 식별자가 불완전하므로 "
            "실제 공간 API를 호출하지 않습니다."
        )


if __name__ == "__main__":
    main()