# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-3B-8
SITE Rule Evaluation completion snapshot

목표
======================================================================
SITE 기반 condition evaluation 단계를 완료 처리한다.

현재까지 해결 완료
======================================================================
서울도심
    FALSE / HIGH

개발밀도관리구역
    FALSE / HIGH

학교이적지
    FALSE / HIGH

도시지역편입해제구역
    UNKNOWN / MEDIUM
    HISTORICAL_SOURCE_PENDING

중요
======================================================================
도시지역편입해제구역 UNKNOWN은 일반적인 미처리 상태가 아니다.

서울시 공식 DB / current spatial data / 직접 고시까지
자동검증 가능한 범위는 모두 검증했지만,

1988~1989 국가기록원 원문과
일부 미구축 historic notice 때문에
FALSE까지 증명할 수 없는 상태이다.

따라서:

UNKNOWN
+
external_dependency = HISTORICAL_SOURCE_PENDING

으로 고정한다.

이 상태에서도 SITE evaluation 단계는 COMPLETE_WITH_EXTERNAL_DEPENDENCY
로 완료 처리한다.
"""

from __future__ import annotations

import copy
import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-10-3B-8 "
    "SITE Rule Evaluation completion snapshot"
)


# ============================================================
# PATH
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

RULE_PATH = (
    OUTPUT_DIR
    / "site_rule_evaluation_school_overlay.json"
)

HISTORY_PATH = (
    OUTPUT_DIR
    / "urban_area_conversion_history_final_resolution.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "site_rule_evaluation_site_complete.json"
)


# ============================================================
# util
# ============================================================

def load_json(
    path: Path,
) -> Dict[str, Any]:

    if not path.exists():

        raise FileNotFoundError(
            f"입력 파일 없음: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def save_json(
    data: Dict[str, Any],
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )


# ============================================================
# main
# ============================================================

def main() -> int:

    snapshot = load_json(
        RULE_PATH
    )

    history = load_json(
        HISTORY_PATH
    )

    rules = copy.deepcopy(
        snapshot.get(
            "rules",
            [],
        )
    )

    # ========================================================
    # 1. history resolution
    # ========================================================

    history_resolution = (
        history.get(
            "current_resolution",
            {},
        )
    )

    history_status = (
        history_resolution.get(
            "status"
        )
    )

    history_confidence = (
        history_resolution.get(
            "confidence"
        )
    )

    automation_state = (
        history_resolution.get(
            "automation_state"
        )
    )

    history_reason = (
        history_resolution.get(
            "reason"
        )
    )

    overlay_action = (
        history.get(
            "overlay_policy",
            {},
        ).get(
            "action"
        )
    )

    affected_clause_count = int(
        history.get(
            "affected_clause_count",
            0,
        )
        or 0
    )

    if (
        history_status
        != "UNKNOWN"
        or automation_state
        != "HISTORICAL_SOURCE_PENDING"
        or overlay_action
        != "KEEP_UNKNOWN"
    ):

        raise ValueError(
            "도시지역편입해제구역 historical pending 상태가 아님"
        )

    # ========================================================
    # 2. 해당 rule에 external dependency metadata 추가
    #
    # applicability 자체는 변경하지 않는다.
    # ========================================================

    touched_rules = []

    unknown_dependency_rules = []

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):
            continue

        matched = False

        for condition in rule.get(
            "conditions",
            [],
        ):

            if not isinstance(
                condition,
                dict,
            ):
                continue

            if (
                condition.get(
                    "name"
                )
                != "도시지역편입해제구역"
            ):
                continue

            matched = True

            condition[
                "state"
            ] = (
                "UNKNOWN"
            )

            condition[
                "confidence"
            ] = (
                history_confidence
            )

            condition[
                "source"
            ] = (
                "URBAN_AREA_CONVERSION_HISTORY_FINAL_RESOLUTION"
            )

            condition[
                "external_dependency"
            ] = (
                "HISTORICAL_SOURCE_PENDING"
            )

            condition[
                "resolution_reason"
            ] = (
                history_reason
            )

        if not matched:
            continue

        dependency = {
            "type": (
                "HISTORICAL_SOURCE"
            ),

            "condition": (
                "도시지역편입해제구역"
            ),

            "status": (
                "PENDING"
            ),

            "automation_state": (
                "HISTORICAL_SOURCE_PENDING"
            ),

            "required_source": (
                "1988~1989 대치택지개발 관련 "
                "미구축 고시 또는 국가기록원 원기록"
            ),

            "blocking_system_completion": (
                False
            ),

            "blocking_rule_resolution": (
                rule.get(
                    "applicability"
                )
                == "UNKNOWN"
            ),
        }

        rule[
            "external_dependencies"
        ] = [
            dependency
        ]

        touched_rules.append(
            rule.get(
                "clause_index"
            )
        )

        if (
            rule.get(
                "applicability"
            )
            == "UNKNOWN"
        ):

            unknown_dependency_rules.append(
                {
                    "clause_index": (
                        rule.get(
                            "clause_index"
                        )
                    ),

                    "law_name": (
                        rule.get(
                            "law_name"
                        )
                    ),

                    "rule_title": (
                        rule.get(
                            "rule_title"
                        )
                    ),

                    "reason": (
                        rule.get(
                            "applicability_reason"
                        )
                    ),
                }
            )

    # ========================================================
    # 3. summary
    # ========================================================

    applicability_counter = Counter(
        rule.get(
            "applicability"
        )
        for rule
        in rules
        if isinstance(
            rule,
            dict,
        )
    )

    # ========================================================
    # 4. unresolved condition 분류
    #
    # 일반 unresolved와 external dependency 분리
    # ========================================================

    ordinary_unresolved = []

    external_unresolved = []

    source_unresolved = (
        snapshot.get(
            "input_requirements",
            {},
        ).get(
            "unresolved_site_conditions",
            [],
        )
    )

    for item in source_unresolved:

        if (
            item.get(
                "name"
            )
            == "도시지역편입해제구역"
        ):

            external_unresolved.append(
                {
                    "name": (
                        "도시지역편입해제구역"
                    ),

                    "type": (
                        "SITE_HISTORY"
                    ),

                    "state": (
                        "UNKNOWN"
                    ),

                    "confidence": (
                        history_confidence
                    ),

                    "affected_clause_count": (
                        item.get(
                            "affected_clause_count"
                        )
                    ),

                    "automation_state": (
                        automation_state
                    ),

                    "blocking_site_stage": (
                        False
                    ),

                    "resolution_path": (
                        "국가기록원 원문 또는 "
                        "미구축 historic notice 확보"
                    ),
                }
            )

        else:

            ordinary_unresolved.append(
                item
            )

    # ========================================================
    # 5. confirmed regulation
    # ========================================================

    confirmed_regulation = (
        snapshot.get(
            "confirmed_regulation",
            {},
        )
    )

    confirmed_bcr = (
        confirmed_regulation.get(
            "building_coverage_ratio",
            {},
        ).get(
            "value"
        )
    )

    confirmed_far = (
        confirmed_regulation.get(
            "floor_area_ratio",
            {},
        ).get(
            "value"
        )
    )

    # ========================================================
    # 6. SITE stage status
    # ========================================================

    if (
        not ordinary_unresolved
        and len(
            external_unresolved
        )
        == 1
        and automation_state
        == "HISTORICAL_SOURCE_PENDING"
    ):

        site_stage_status = (
            "COMPLETE_WITH_EXTERNAL_DEPENDENCY"
        )

    else:

        site_stage_status = (
            "INCOMPLETE"
        )

    # ========================================================
    # 7. system readiness
    # ========================================================

    site_rule_engine_ready = (
        site_stage_status
        == "COMPLETE_WITH_EXTERNAL_DEPENDENCY"
        and confirmed_bcr
        == 50.0
        and confirmed_far
        == 250.0
    )

    # ========================================================
    # 8. validations
    # ========================================================

    validations = {

        "rules 314": (
            len(
                rules
            )
            == 314
        ),

        "affected condition rules 3": (
            len(
                touched_rules
            )
            == affected_clause_count
            == 3
        ),

        "UNKNOWN 2 유지": (
            applicability_counter[
                "UNKNOWN"
            ]
            == 2
        ),

        "APPLICABLE 58 유지": (
            applicability_counter[
                "APPLICABLE"
            ]
            == 58
        ),

        "NOT_APPLICABLE 211 유지": (
            applicability_counter[
                "NOT_APPLICABLE"
            ]
            == 211
        ),

        "CONDITIONAL 43 유지": (
            applicability_counter[
                "CONDITIONAL"
            ]
            == 43
        ),

        "ordinary unresolved 0": (
            len(
                ordinary_unresolved
            )
            == 0
        ),

        "external unresolved 1": (
            len(
                external_unresolved
            )
            == 1
        ),

        "external dependency historical pending": (
            external_unresolved[
                0
            ][
                "automation_state"
            ]
            == "HISTORICAL_SOURCE_PENDING"
        ),

        "unknown dependency rules 2": (
            len(
                unknown_dependency_rules
            )
            == 2
        ),

        "confirmed BCR 50": (
            confirmed_bcr
            == 50.0
        ),

        "confirmed FAR 250": (
            confirmed_far
            == 250.0
        ),

        "SITE stage complete": (
            site_stage_status
            == "COMPLETE_WITH_EXTERNAL_DEPENDENCY"
        ),

        "SITE rule engine ready": (
            site_rule_engine_ready
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # 9. final output
    # ========================================================

    output = {
        "step": (
            STEP_NAME
        ),

        "site": (
            snapshot.get(
                "site",
                {}
            )
        ),

        "site_stage": {
            "status": (
                site_stage_status
            ),

            "rule_engine_ready": (
                site_rule_engine_ready
            ),

            "policy": (
                "외부 역사 원문 dependency는 "
                "SITE 단계 전체 완료를 차단하지 않으며 "
                "영향 조문만 UNKNOWN으로 유지"
            ),
        },

        "confirmed_regulation": (
            confirmed_regulation
        ),

        "rule_evaluation_summary": {
            "total_clauses": (
                len(
                    rules
                )
            ),

            "applicable": (
                applicability_counter[
                    "APPLICABLE"
                ]
            ),

            "not_applicable": (
                applicability_counter[
                    "NOT_APPLICABLE"
                ]
            ),

            "conditional": (
                applicability_counter[
                    "CONDITIONAL"
                ]
            ),

            "unknown": (
                applicability_counter[
                    "UNKNOWN"
                ]
            ),

            "confirmed_building_coverage_ratio": (
                confirmed_bcr
            ),

            "confirmed_floor_area_ratio": (
                confirmed_far
            ),
        },

        "site_dependencies": {

            "ordinary_unresolved": (
                ordinary_unresolved
            ),

            "external_historical_dependencies": (
                external_unresolved
            ),
        },

        "historical_dependency": {
            "condition": (
                "도시지역편입해제구역"
            ),

            "status": (
                history_status
            ),

            "confidence": (
                history_confidence
            ),

            "automation_state": (
                automation_state
            ),

            "affected_clause_count": (
                affected_clause_count
            ),

            "unknown_rule_count": (
                len(
                    unknown_dependency_rules
                )
            ),

            "unknown_rules": (
                unknown_dependency_rules
            ),

            "blocking_site_stage": (
                False
            ),
        },

        "input_requirements": {
            "project": (
                snapshot.get(
                    "input_requirements",
                    {},
                ).get(
                    "project",
                    [],
                )
            ),

            "procedure": (
                snapshot.get(
                    "input_requirements",
                    {},
                ).get(
                    "procedure",
                    [],
                )
            ),
        },

        "rule_groups": (
            snapshot.get(
                "rule_groups",
                {}
            )
        ),

        "rules": (
            rules
        ),

        "validations": (
            validations
        ),

        "all_pass": (
            all_pass
        ),
    }

    save_json(
        output
    )

    # ========================================================
    # concise console
    # ========================================================

    print(
        "SITE stage:",
        site_stage_status,
    )

    print(
        "Rule engine ready:",
        site_rule_engine_ready,
    )

    print()

    print(
        "APPLICABLE:",
        applicability_counter[
            "APPLICABLE"
        ],
    )

    print(
        "NOT_APPLICABLE:",
        applicability_counter[
            "NOT_APPLICABLE"
        ],
    )

    print(
        "CONDITIONAL:",
        applicability_counter[
            "CONDITIONAL"
        ],
    )

    print(
        "UNKNOWN:",
        applicability_counter[
            "UNKNOWN"
        ],
    )

    print()

    print(
        "Ordinary unresolved SITE:",
        len(
            ordinary_unresolved
        ),
    )

    print(
        "External historical dependencies:",
        len(
            external_unresolved
        ),
    )

    print(
        "Historical UNKNOWN rules:",
        len(
            unknown_dependency_rules
        ),
    )

    print()

    print(
        "Confirmed BCR:",
        confirmed_bcr,
    )

    print(
        "Confirmed FAR:",
        confirmed_far,
    )

    print()

    print(
        "all_pass:",
        all_pass,
    )

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    return (
        0
        if all_pass
        else 1
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )