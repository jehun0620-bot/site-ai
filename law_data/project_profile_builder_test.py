# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-1B
ProjectProfile / PROJECT 조건 입력 모델 구축

핵심 수정
======================================================================
- parser가 PROJECT로 분류했더라도 semantic override를 적용한다.
- '기존공장'은 SITE_HISTORY로 교정한다.
- ProjectProfile에는 실제 PROJECT 조건만 포함한다.
- C-8 required_conditions.PROJECT = 11개와 일치해야 한다.
"""

from __future__ import annotations

import json

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set


STEP_NAME = (
    "STEP 17-21-C-10-1B "
    "ProjectProfile / PROJECT 조건 입력 모델 구축"
)

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

CLAUSE_PATH = (
    OUTPUT_DIR
    / "law_special_rule_clauses.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "project_profile_template.json"
)


VALID_STATES = {
    "TRUE",
    "FALSE",
    "UNKNOWN",
    "UNSET",
}


# ============================================================
# semantic override
# ============================================================

CONDITION_TYPE_OVERRIDES = {
    "기존공장": "SITE_HISTORY",
}


# ============================================================
# PROJECT semantic registry
# ============================================================

PROJECT_FIELD_REGISTRY = {

    "공개공지": {
        "field": "public_open_space",
        "value_type": "boolean",
        "description": (
            "사업계획에 공개공지 또는 공개공간을 "
            "설치·확보하는지 여부"
        ),
    },

    "공공시설제공": {
        "field": "public_facility_contribution",
        "value_type": "boolean",
        "description": (
            "사업계획에서 공공시설을 설치하거나 "
            "공공에 제공하는지 여부"
        ),
    },

    "공공주택": {
        "field": "public_housing",
        "value_type": "boolean",
        "description": (
            "해당 사업 또는 건축물이 공공주택에 "
            "해당하는지 여부"
        ),
    },

    "공동주택": {
        "field": "multi_family_housing",
        "value_type": "boolean",
        "description": (
            "주된 건축물 용도가 공동주택에 "
            "해당하는지 여부"
        ),
    },

    "기부채납": {
        "field": "donation",
        "value_type": "boolean",
        "description": (
            "토지·시설 등의 기부채납이 "
            "사업계획에 포함되는지 여부"
        ),
    },

    "대학": {
        "field": "university",
        "value_type": "boolean",
        "description": (
            "대학 또는 대학 관련 시설 사업인지 여부"
        ),
    },

    "사회복지시설": {
        "field": "social_welfare_facility",
        "value_type": "boolean",
        "description": (
            "사회복지시설에 해당하는 사업인지 여부"
        ),
    },

    "임대주택": {
        "field": "rental_housing",
        "value_type": "boolean",
        "description": (
            "임대주택을 포함하거나 임대주택 사업에 "
            "해당하는지 여부"
        ),
    },

    "종합의료시설": {
        "field": "general_medical_facility",
        "value_type": "boolean",
        "description": (
            "종합병원 등 종합의료시설 사업인지 여부"
        ),
    },

    "주거복합": {
        "field": "residential_mixed_use",
        "value_type": "boolean",
        "description": (
            "주거와 비주거 기능이 결합된 "
            "주거복합 사업인지 여부"
        ),
    },

    "한옥": {
        "field": "hanok",
        "value_type": "boolean",
        "description": (
            "건축법령상 한옥에 해당하는 "
            "건축물 또는 사업인지 여부"
        ),
    },
}


def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip()


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


def effective_condition_type(
    name: str,
    declared_type: str,
) -> str:

    return CONDITION_TYPE_OVERRIDES.get(
        name,
        declared_type,
    )


def get_declared_project_conditions(
    data: Dict[str, Any],
) -> List[str]:

    required = data.get(
        "required_conditions",
        {},
    )

    values = required.get(
        "PROJECT",
        [],
    )

    if not isinstance(
        values,
        list,
    ):
        return []

    return sorted(
        {
            safe_string(item)
            for item in values
            if safe_string(item)
        }
    )


def extract_project_conditions(
    clauses: List[Dict[str, Any]],
) -> Dict[str, Any]:

    names: Set[str] = set()

    usage_count = Counter()
    categories = defaultdict(set)
    laws = defaultdict(set)
    rule_titles = defaultdict(set)
    effect_targets = defaultdict(set)
    clause_ids = defaultdict(list)

    semantic_overrides = Counter()

    for index, clause in enumerate(
        clauses,
        start=1,
    ):

        if not isinstance(
            clause,
            dict,
        ):
            continue

        conditions = clause.get(
            "conditions",
            [],
        )

        if not isinstance(
            conditions,
            list,
        ):
            continue

        for condition in conditions:

            if not isinstance(
                condition,
                dict,
            ):
                continue

            name = safe_string(
                condition.get(
                    "name"
                )
            )

            declared_type = safe_string(
                condition.get(
                    "type"
                )
            )

            if not name:
                continue

            effective_type = (
                effective_condition_type(
                    name,
                    declared_type,
                )
            )

            if (
                effective_type
                != declared_type
            ):

                semantic_overrides[
                    f"{name}: "
                    f"{declared_type} -> "
                    f"{effective_type}"
                ] += 1

            # 실제 PROJECT만 Profile에 포함
            if (
                effective_type
                != "PROJECT"
            ):
                continue

            names.add(
                name
            )

            usage_count[
                name
            ] += 1

            category = safe_string(
                clause.get(
                    "category"
                )
            )

            law_name = safe_string(
                clause.get(
                    "law_name"
                )
            )

            rule_title = safe_string(
                clause.get(
                    "rule_title"
                )
            )

            if category:
                categories[
                    name
                ].add(
                    category
                )

            if law_name:
                laws[
                    name
                ].add(
                    law_name
                )

            if rule_title:
                rule_titles[
                    name
                ].add(
                    rule_title
                )

            for target in clause.get(
                "effect_targets",
                [],
            ):

                target = safe_string(
                    target
                )

                if target:
                    effect_targets[
                        name
                    ].add(
                        target
                    )

            clause_ids[
                name
            ].append(
                index
            )

    return {
        "names": sorted(
            names
        ),

        "usage_count": usage_count,

        "categories": categories,

        "laws": laws,

        "rule_titles": rule_titles,

        "effect_targets": effect_targets,

        "clause_ids": clause_ids,

        "semantic_overrides": (
            semantic_overrides
        ),
    }


def build_condition_entry(
    name: str,
    extracted: Dict[str, Any],
) -> Dict[str, Any]:

    registry = (
        PROJECT_FIELD_REGISTRY.get(
            name,
            {},
        )
    )

    return {
        "name": name,

        "type": "PROJECT",

        "field": (
            registry.get(
                "field"
            )
        ),

        "value_type": (
            registry.get(
                "value_type",
                "boolean",
            )
        ),

        "state": "UNSET",

        "value": None,

        "confidence": "NONE",

        "source": (
            "USER_INPUT_REQUIRED"
        ),

        "description": (
            registry.get(
                "description",
                ""
            )
        ),

        "rule_usage": {
            "clause_count": (
                extracted[
                    "usage_count"
                ][name]
            ),

            "categories": sorted(
                extracted[
                    "categories"
                ][name]
            ),

            "laws": sorted(
                extracted[
                    "laws"
                ][name]
            ),

            "rule_titles": sorted(
                extracted[
                    "rule_titles"
                ][name]
            ),

            "effect_targets": sorted(
                extracted[
                    "effect_targets"
                ][name]
            ),

            "clause_indexes": (
                extracted[
                    "clause_ids"
                ][name]
            ),
        },

        "evidence": [],
    }


def summarize_states(
    conditions: List[
        Dict[str, Any]
    ],
) -> Dict[str, int]:

    counter = Counter(
        safe_string(
            condition.get(
                "state"
            )
        )
        for condition
        in conditions
    )

    return {
        "true": counter["TRUE"],
        "false": counter["FALSE"],
        "unknown": counter["UNKNOWN"],
        "unset": counter["UNSET"],
    }


def validate_profile(
    declared: List[str],
    extracted_names: List[str],
    conditions: List[
        Dict[str, Any]
    ],
) -> Dict[str, bool]:

    declared_set = set(
        declared
    )

    extracted_set = set(
        extracted_names
    )

    condition_names = {
        safe_string(
            condition.get(
                "name"
            )
        )
        for condition
        in conditions
    }

    valid_states = all(
        safe_string(
            condition.get(
                "state"
            )
        )
        in VALID_STATES
        for condition
        in conditions
    )

    all_unset_initially = all(
        condition.get(
            "state"
        )
        == "UNSET"
        for condition
        in conditions
    )

    registry_complete = all(
        name in PROJECT_FIELD_REGISTRY
        for name
        in extracted_set
    )

    fields = [
        PROJECT_FIELD_REGISTRY[
            name
        ][
            "field"
        ]
        for name
        in extracted_names
        if name
        in PROJECT_FIELD_REGISTRY
    ]

    return {
        "C-8 declared PROJECT 조건과 semantic PROJECT 조건 일치": (
            declared_set
            == extracted_set
        ),

        "ProjectProfile 조건명 전체 일치": (
            condition_names
            == extracted_set
        ),

        "PROJECT 상태값 4종 한정": (
            valid_states
        ),

        "최초 PROJECT 조건은 모두 UNSET": (
            all_unset_initially
        ),

        "PROJECT semantic registry 전체 존재": (
            registry_complete
        ),

        "semantic field 중복 없음": (
            len(fields)
            == len(
                set(fields)
            )
        ),

        "기존공장을 PROJECT에서 제외": (
            "기존공장"
            not in extracted_set
        ),

        "기존공장 semantic override는 SITE_HISTORY": (
            CONDITION_TYPE_OVERRIDES.get(
                "기존공장"
            )
            == "SITE_HISTORY"
        ),
    }


def main() -> int:

    clause_data = load_json(
        CLAUSE_PATH
    )

    clauses = clause_data.get(
        "clauses",
        [],
    )

    if not isinstance(
        clauses,
        list,
    ):
        print(
            "ERROR: clauses invalid"
        )
        return 1

    declared = (
        get_declared_project_conditions(
            clause_data
        )
    )

    extracted = (
        extract_project_conditions(
            clauses
        )
    )

    extracted_names = (
        extracted[
            "names"
        ]
    )

    project_conditions = [
        build_condition_entry(
            name,
            extracted,
        )
        for name
        in extracted_names
    ]

    fields = {}

    for condition in project_conditions:

        field = condition.get(
            "field"
        )

        if field:
            fields[field] = None

    state_summary = (
        summarize_states(
            project_conditions
        )
    )

    validations = (
        validate_profile(
            declared,
            extracted_names,
            project_conditions,
        )
    )

    all_pass = all(
        validations.values()
    )

    output = {
        "step": STEP_NAME,

        "profile_version": "1.1",

        "profile_type": (
            "ProjectProfile"
        ),

        "semantic_overrides": {
            "기존공장": {
                "parser_type": (
                    "PROJECT"
                ),
                "effective_type": (
                    "SITE_HISTORY"
                ),
                "reason": (
                    "해당 용도지역 지정 당시 "
                    "이미 준공된 공장인지 여부가 "
                    "핵심 사실관계이므로 과거 SITE 상태"
                ),
                "affected_clause_count": (
                    extracted[
                        "semantic_overrides"
                    ].get(
                        (
                            "기존공장: "
                            "PROJECT -> "
                            "SITE_HISTORY"
                        ),
                        0,
                    )
                ),
            }
        },

        "state_model": {
            "TRUE": (
                "사업계획상 조건 충족"
            ),
            "FALSE": (
                "사업계획상 조건 비충족"
            ),
            "UNKNOWN": (
                "정보는 있으나 판정 부족"
            ),
            "UNSET": (
                "프로젝트 정보 미입력"
            ),
        },

        "fields": fields,

        "conditions": (
            project_conditions
        ),

        "summary": {
            "condition_count": (
                len(
                    project_conditions
                )
            ),
            **state_summary,
        },

        "source_validation": {
            "declared_conditions": (
                declared
            ),

            "semantic_project_conditions": (
                extracted_names
            ),

            "semantic_override_counts": (
                dict(
                    extracted[
                        "semantic_overrides"
                    ]
                )
            ),

            "missing_from_clauses": sorted(
                set(declared)
                - set(
                    extracted_names
                )
            ),

            "undeclared_in_clauses": sorted(
                set(
                    extracted_names
                )
                - set(declared)
            ),
        },

        "validations": validations,

        "all_pass": all_pass,
    }

    save_json(
        output
    )

    print(
        "PROJECT conditions:",
        len(
            project_conditions
        ),
    )

    print(
        "Declared:",
        len(
            declared
        ),
    )

    print(
        "Semantic PROJECT:",
        len(
            extracted_names
        ),
    )

    print(
        "Existing factory override:",
        (
            extracted[
                "semantic_overrides"
            ].get(
                (
                    "기존공장: "
                    "PROJECT -> "
                    "SITE_HISTORY"
                ),
                0,
            )
        ),
    )

    print()

    for condition in (
        project_conditions
    ):

        print(
            f"{condition['name']}: "
            f"{condition['field']} "
            f"/ {condition['state']} "
            f"/ clauses="
            f"{condition['rule_usage']['clause_count']}"
        )

    print()

    print(
        "TRUE:",
        state_summary[
            "true"
        ],
    )

    print(
        "FALSE:",
        state_summary[
            "false"
        ],
    )

    print(
        "UNKNOWN:",
        state_summary[
            "unknown"
        ],
    )

    print(
        "UNSET:",
        state_summary[
            "unset"
        ],
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