import json
from pathlib import Path

from law_detail_normalize_test import (
    TARGETS,
    request_detail,
    normalize_detail,
)


# ============================================================
# STEP 17-21-C-3
# 통합 법규 핵심 규정 자동 탐색 테스트
#
# 대상:
# - 자치구 조례
# - 서울특별시 조례
# - 국가 법률
# - 국가 시행령
#
# 검색 대상:
# - 조문 전체
# - 항 / 호 / 목 포함 article_full_text
# - 별표 / 서식
# ============================================================


BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = BASE_DIR / "law_data" / "output"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "law_core_rule_matches.json"
)


# ============================================================
# 핵심 규제 카테고리
# ============================================================

RULE_CATEGORIES = {
    "건폐율": [
        "건폐율",
    ],

    "용적률": [
        "용적률",
    ],

    "용도지역": [
        "용도지역",
    ],

    "용도지구": [
        "용도지구",
    ],

    "용도구역": [
        "용도구역",
    ],

    "건축물용도": [
        "건축물의 용도",
        "건축물 용도",
        "건축할 수 있는 건축물",
        "건축할 수 없는 건축물",
        "허용용도",
        "불허용도",
    ],

    "높이": [
        "건축물의 높이",
        "건축물 높이",
        "높이 제한",
        "높이제한",
        "최고높이",
        "최저높이",
    ],

    "대지": [
        "대지면적",
        "대지의 면적",
        "대지 안",
        "대지안",
    ],

    "도로": [
        "도로",
        "접도",
        "전면도로",
        "도로폭",
        "도로의 너비",
    ],

    "개발행위": [
        "개발행위",
        "개발행위허가",
        "개발행위 허가",
    ],

    "지구단위계획": [
        "지구단위계획",
        "지구단위 계획",
    ],

    "주차": [
        "주차장",
        "부설주차장",
        "주차대수",
        "주차구획",
    ],
}


# ============================================================
# 공통 유틸
# ============================================================

def normalize_space(value):
    """
    검색용 문자열 정리
    """

    if value is None:
        return ""

    text = str(value)

    text = text.replace(
        "\r",
        " "
    )

    text = text.replace(
        "\n",
        " "
    )

    while "  " in text:
        text = text.replace(
            "  ",
            " "
        )

    return text.strip()


def make_article_display_number(
    article
):
    """
    제84조 / 제84조의2 같은 표시번호 생성
    """

    number = article.get(
        "article_number",
        ""
    )

    branch = article.get(
        "article_branch_number",
        ""
    )

    if branch:
        return f"{number}조의{branch}"

    if number:
        return f"{number}조"

    return ""


def is_real_article(article):
    """
    장/절 제목이 아니라 실제 조문인지 판별
    """

    status = article.get(
        "article_status",
        ""
    )

    source_format = article.get(
        "source_format",
        ""
    )

    if source_format == "ordin":

        return status == "Y"

    if source_format == "law":

        return status == "조문"

    return True


# ============================================================
# 키워드 매칭
# ============================================================

def find_keywords(
    text,
    keywords,
):

    found = []

    for keyword in keywords:

        if keyword in text:
            found.append(
                keyword
            )

    return found


# ============================================================
# 조문 검색
# ============================================================

def search_articles(
    normalized_law,
    category,
    keywords,
):

    matches = []

    for article in normalized_law[
        "articles"
    ]:

        # 실제 조문만 검색
        if not is_real_article(
            article
        ):
            continue

        title = normalize_space(
            article.get(
                "article_title",
                ""
            )
        )

        full_text = normalize_space(
            article.get(
                "article_full_text",
                ""
            )
        )

        search_text = (
            title
            + " "
            + full_text
        )

        found_keywords = (
            find_keywords(
                search_text,
                keywords,
            )
        )

        if not found_keywords:
            continue

        matches.append(
            {
                "source_type": "article",

                "level": normalized_law[
                    "level"
                ],

                "hierarchy_type": (
                    normalized_law[
                        "hierarchy_type"
                    ]
                ),

                "law_name": (
                    normalized_law[
                        "basic_info"
                    ].get(
                        "name",
                        ""
                    )
                ),

                "category": category,

                "keywords": (
                    found_keywords
                ),

                "article_number": (
                    article.get(
                        "article_number",
                        ""
                    )
                ),

                "article_branch_number": (
                    article.get(
                        "article_branch_number",
                        ""
                    )
                ),

                "article_key": (
                    article.get(
                        "article_key",
                        ""
                    )
                ),

                "article_title": (
                    article.get(
                        "article_title",
                        ""
                    )
                ),

                "effective_date": (
                    article.get(
                        "effective_date",
                        ""
                    )
                ),

                "text": full_text,
            }
        )

    return matches


# ============================================================
# 별표 검색
# ============================================================

def search_appendices(
    normalized_law,
    category,
    keywords,
):

    matches = []

    for appendix in normalized_law[
        "appendices"
    ]:

        title = normalize_space(
            appendix.get(
                "title",
                ""
            )
        )

        content = normalize_space(
            appendix.get(
                "content",
                ""
            )
        )

        search_text = (
            title
            + " "
            + content
        )

        found_keywords = (
            find_keywords(
                search_text,
                keywords,
            )
        )

        if not found_keywords:
            continue

        matches.append(
            {
                "source_type": "appendix",

                "level": normalized_law[
                    "level"
                ],

                "hierarchy_type": (
                    normalized_law[
                        "hierarchy_type"
                    ]
                ),

                "law_name": (
                    normalized_law[
                        "basic_info"
                    ].get(
                        "name",
                        ""
                    )
                ),

                "category": category,

                "keywords": (
                    found_keywords
                ),

                "appendix_number": (
                    appendix.get(
                        "number",
                        ""
                    )
                ),

                "appendix_branch_number": (
                    appendix.get(
                        "branch_number",
                        ""
                    )
                ),

                "appendix_key": (
                    appendix.get(
                        "key",
                        ""
                    )
                ),

                "appendix_title": (
                    appendix.get(
                        "title",
                        ""
                    )
                ),

                "text": content,
            }
        )

    return matches


# ============================================================
# 법규 하나 검색
# ============================================================

def search_law(
    normalized_law
):

    result = {}

    for (
        category,
        keywords
    ) in RULE_CATEGORIES.items():

        article_matches = (
            search_articles(
                normalized_law,
                category,
                keywords,
            )
        )

        appendix_matches = (
            search_appendices(
                normalized_law,
                category,
                keywords,
            )
        )

        result[
            category
        ] = {
            "articles": (
                article_matches
            ),

            "appendices": (
                appendix_matches
            ),
        }

    return result


# ============================================================
# 출력용 미리보기
# ============================================================

def preview_text(
    text,
    limit=220,
):

    text = normalize_space(
        text
    )

    if len(text) <= limit:
        return text

    return (
        text[:limit]
        + "..."
    )


# ============================================================
# 개별 법규 검색 결과 출력
# ============================================================

def print_law_search_result(
    normalized_law,
    search_result,
):

    info = normalized_law[
        "basic_info"
    ]

    print()
    print("=" * 70)

    print(
        f"LEVEL "
        f"{normalized_law['level']} "
        f"| "
        f"{normalized_law['hierarchy_type']}"
    )

    print(
        info.get(
            "name",
            ""
        )
    )

    print("=" * 70)

    for (
        category,
        result
    ) in search_result.items():

        articles = result[
            "articles"
        ]

        appendices = result[
            "appendices"
        ]

        total = (
            len(articles)
            + len(appendices)
        )

        print()
        print(
            f"[{category}] "
            f"총 {total}건 "
            f"(조문 {len(articles)} / "
            f"별표 {len(appendices)})"
        )

        # ----------------------------------------------------
        # 조문 최대 3개 미리보기
        # ----------------------------------------------------

        for match in articles[:3]:

            article_number = (
                match.get(
                    "article_number",
                    ""
                )
            )

            branch = (
                match.get(
                    "article_branch_number",
                    ""
                )
            )

            if branch:

                number_display = (
                    f"제{article_number}조의"
                    f"{branch}"
                )

            else:

                number_display = (
                    f"제{article_number}조"
                )

            title = match.get(
                "article_title",
                ""
            )

            keywords = ", ".join(
                match.get(
                    "keywords",
                    []
                )
            )

            print(
                f"  조문 | "
                f"{number_display} "
                f"{title}"
            )

            print(
                f"       키워드: "
                f"{keywords}"
            )

            print(
                f"       "
                f"{preview_text(match['text'])}"
            )

        # ----------------------------------------------------
        # 별표 최대 2개 미리보기
        # ----------------------------------------------------

        for match in appendices[:2]:

            number = match.get(
                "appendix_number",
                ""
            )

            title = match.get(
                "appendix_title",
                ""
            )

            keywords = ", ".join(
                match.get(
                    "keywords",
                    []
                )
            )

            print(
                f"  별표 | "
                f"{number} "
                f"{title}"
            )

            print(
                f"       키워드: "
                f"{keywords}"
            )

            text = match.get(
                "text",
                ""
            )

            if text:

                print(
                    f"       "
                    f"{preview_text(text)}"
                )


# ============================================================
# 전체 카테고리 통계
# ============================================================

def build_category_summary(
    all_results
):

    summary = {}

    for category in (
        RULE_CATEGORIES.keys()
    ):

        summary[
            category
        ] = {
            "article_count": 0,
            "appendix_count": 0,
            "levels": {},
        }

    for item in all_results:

        level = item[
            "normalized"
        ][
            "level"
        ]

        search_result = item[
            "search_result"
        ]

        for (
            category,
            result
        ) in search_result.items():

            article_count = len(
                result["articles"]
            )

            appendix_count = len(
                result["appendices"]
            )

            summary[
                category
            ][
                "article_count"
            ] += article_count

            summary[
                category
            ][
                "appendix_count"
            ] += appendix_count

            summary[
                category
            ][
                "levels"
            ][
                str(level)
            ] = {
                "articles": (
                    article_count
                ),
                "appendices": (
                    appendix_count
                ),
            }

    return summary


# ============================================================
# JSON 저장용 데이터 생성
# ============================================================

def make_output_data(
    all_results,
    summary,
):

    laws = []

    for item in all_results:

        normalized = item[
            "normalized"
        ]

        info = normalized[
            "basic_info"
        ]

        laws.append(
            {
                "level": (
                    normalized[
                        "level"
                    ]
                ),

                "hierarchy_type": (
                    normalized[
                        "hierarchy_type"
                    ]
                ),

                "law_name": (
                    info.get(
                        "name",
                        ""
                    )
                ),

                "law_id": (
                    info.get(
                        "law_id",
                        ""
                    )
                ),

                "mst": (
                    info.get(
                        "mst",
                        ""
                    )
                ),

                "effective_date": (
                    info.get(
                        "effective_date",
                        ""
                    )
                ),

                "matches": (
                    item[
                        "search_result"
                    ]
                ),
            }
        )

    return {
        "summary": summary,
        "laws": laws,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=== STEP 17-21-C-3 "
        "통합 법규 핵심 규정 탐색 테스트 ==="
    )

    print()

    print(
        "검색 카테고리:"
    )

    for category in (
        RULE_CATEGORIES.keys()
    ):

        print(
            " -",
            category
        )

    normalized_laws = []

    # ========================================================
    # 1. API 조회 + 정규화
    # ========================================================

    print()
    print("=" * 70)
    print(
        "1. 법규 상세 데이터 조회 / 정규화"
    )
    print("=" * 70)

    for target in TARGETS:

        print()
        print(
            f"LEVEL {target['level']} | "
            f"{target['name']}"
        )

        try:

            data = request_detail(
                target
            )

        except Exception as exc:

            print(
                "조회 실패:",
                exc
            )

            continue

        if data is None:
            continue

        normalized = (
            normalize_detail(
                data,
                target,
            )
        )

        if normalized is None:

            print(
                "정규화 실패"
            )

            continue

        normalized_laws.append(
            normalized
        )

        print(
            f"정규화 성공 | "
            f"조문 "
            f"{len(normalized['articles'])} | "
            f"별표 "
            f"{len(normalized['appendices'])}"
        )

    # ========================================================
    # 2. 핵심 규정 검색
    # ========================================================

    print()
    print()
    print("=" * 70)
    print(
        "2. 핵심 규정 통합 탐색"
    )
    print("=" * 70)

    all_results = []

    for normalized in normalized_laws:

        search_result = (
            search_law(
                normalized
            )
        )

        all_results.append(
            {
                "normalized": (
                    normalized
                ),

                "search_result": (
                    search_result
                ),
            }
        )

        print_law_search_result(
            normalized,
            search_result,
        )

    # ========================================================
    # 3. 통합 통계
    # ========================================================

    summary = (
        build_category_summary(
            all_results
        )
    )

    print()
    print()
    print("=" * 70)

    print(
        "=== 핵심 규정 통합 검색 요약 ==="
    )

    print("=" * 70)

    for (
        category,
        result
    ) in summary.items():

        total = (
            result[
                "article_count"
            ]
            + result[
                "appendix_count"
            ]
        )

        print()

        print(
            f"[{category}] "
            f"총 {total}건"
        )

        print(
            f"  조문: "
            f"{result['article_count']}"
        )

        print(
            f"  별표: "
            f"{result['appendix_count']}"
        )

        level_parts = []

        for level in [
            "1",
            "2",
            "3",
            "4",
        ]:

            level_result = (
                result[
                    "levels"
                ].get(
                    level,
                    {
                        "articles": 0,
                        "appendices": 0,
                    }
                )
            )

            level_total = (
                level_result[
                    "articles"
                ]
                + level_result[
                    "appendices"
                ]
            )

            level_parts.append(
                f"L{level}={level_total}"
            )

        print(
            "  계층별: "
            + ", ".join(
                level_parts
            )
        )

    # ========================================================
    # 4. JSON 저장
    # ========================================================

    output_data = (
        make_output_data(
            all_results,
            summary,
        )
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output_data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print()
    print("=" * 70)
    print(
        "=== 결과 파일 저장 ==="
    )
    print("=" * 70)

    print(
        OUTPUT_FILE
    )

    # ========================================================
    # 최종
    # ========================================================

    print()
    print("=" * 70)

    print(
        "STEP 17-21-C-3 완료"
    )

    print("=" * 70)

    print()

    print(
        "다음 단계:"
    )

    print(
        "STEP 17-21-C-4"
    )

    print(
        "→ 단순 키워드 검색 결과에서 "
        "실제 적용 규정을 선별"
    )

    print(
        "→ 용도지역별 건폐율 / 용적률 "
        "수치 자동 추출 준비"
    )


if __name__ == "__main__":
    main()