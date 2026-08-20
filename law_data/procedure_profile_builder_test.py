# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-1D
ProcedureProfile / PROCEDURE 조건 입력 모델 구축

목표
======================================================================
1. law_special_rule_clauses.json에서 PROCEDURE 조건 자동 추출
2. required_conditions.PROCEDURE와 실제 clause 조건 교차검증
3. TRUE / FALSE / UNKNOWN / UNSET 상태모델 적용
4. 최초 상태는 모두 UNSET
5. 미입력을 FALSE로 자동 변환하지 않음
6. 다음 단계에서 Clause Applicability Engine에 연결
"""

from __future__ import annotations

import json

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set


STEP_NAME = (
    "STEP 17-21-C-10-1D "
    "ProcedureProfile / PROCEDURE 조건 입력 모델 구축"
)


# ============================================================
# 경로
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

CLAUSE_PATH = (
    OUTPUT_DIR
    / "law_special_rule_clauses.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "procedure_profile_template.json"
)


# ============================================================
# 상태
# ============================================================

VALID_STATES = {
    "TRUE",
    "FALSE",
    "UNKNOWN",
    "UNSET",
}


# ============================================================
# semantic registry
# ============================================================

PROCEDURE_FIELD_REGISTRY = {

    "도시계획위원회심의": {
        "field": (
            "urban_planning_committee_review"
        ),
        "value_type": (
            "boolean"
        ),
        "description": (
            "해당 특례 적용을 위해 "
            "도시계획위원회 또는 지방도시계획위원회의 "
            "심의·의결이 필요한지 또는 완료되었는지 여부"
        ),
    },

    "시장정비사업심의": {
        "field": (
            "market_redevelopment_review"
        ),
        "value_type": (
            "boolean"
        ),
        "description": (
            "시장정비사업 관련 법정 심의절차의 "
            "적용 또는 완료 여부"
        ),
    },
}


# ============================================================
# util
# ============================================================

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


# ============================================================
# C-8 declared conditions
# ============================================================

def get_declared_procedure_conditions(
    data: Dict[str, Any],
) -> List[str]:

    required = data.get(
        "required_conditions",
        {},
    )

    values = required.get(
        "PROCEDURE",
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


# ============================================================
# 실제 clause 추출
# ============================================================

def extract_procedure_conditions(
    clauses: List[Dict[str, Any]],
) -> Dict[str, Any]:

    names: Set[str] = set()

    usage_count = Counter()

    categories = defaultdict(set)

    laws = defaultdict(set)

    rule_titles = defaultdict(set)

    effect_targets = defaultdict(set)

    clause_ids = defaultdict(list)

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

            condition_type = safe_string(
                condition.get(
                    "type"
                )
            )

            if condition_type != "PROCEDURE":

                continue

            name = safe_string(
                condition.get(
                    "name"
                )
            )

            if not name:

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

        "usage_count": (
            usage_count
        ),

        "categories": (
            categories
        ),

        "laws": (
            laws
        ),

        "rule_titles": (
            rule_titles
        ),

        "effect_targets": (
            effect_targets
        ),

        "clause_ids": (
            clause_ids
        ),
    }


# ============================================================
# condition entry
# ============================================================

def build_condition_entry(
    name: str,
    extracted: Dict[str, Any],
) -> Dict[str, Any]:

    registry = (
        PROCEDURE_FIELD_REGISTRY.get(
            name,
            {},
        )
    )

    return {
        "name": (
            name
        ),

        "type": (
            "PROCEDURE"
        ),

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

        "state": (
            "UNSET"
        ),

        "value": None,

        "confidence": (
            "NONE"
        ),

        "source": (
            "USER_OR_PROCESS_INPUT_REQUIRED"
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


# ============================================================
# state summary
# ============================================================

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
        "true": (
            counter[
                "TRUE"
            ]
        ),

        "false": (
            counter[
                "FALSE"
            ]
        ),

        "unknown": (
            counter[
                "UNKNOWN"
            ]
        ),

        "unset": (
            counter[
                "UNSET"
            ]
        ),
    }


# ============================================================
# validation
# ============================================================

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

    all_unset = all(
        condition.get(
            "state"
        )
        == "UNSET"
        for condition
        in conditions
    )

    registry_complete = all(
        name
        in PROCEDURE_FIELD_REGISTRY
        for name
        in extracted_set
    )

    fields = [
        PROCEDURE_FIELD_REGISTRY[
            name
        ][
            "field"
        ]
        for name
        in extracted_names
        if name
        in PROCEDURE_FIELD_REGISTRY
    ]

    return {
        "C-8 declared PROCEDURE 조건과 실제 clause 조건 일치": (
            declared_set
            == extracted_set
        ),

        "ProcedureProfile 조건명 전체 일치": (
            condition_names
            == extracted_set
        ),

        "PROCEDURE 상태값 4종 한정": (
            valid_states
        ),

        "최초 PROCEDURE 조건은 모두 UNSET": (
            all_unset
        ),

        "PROCEDURE semantic registry 전체 존재": (
            registry_complete
        ),

        "semantic field 중복 없음": (
            len(fields)
            == len(
                set(fields)
            )
        ),

        "미입력 PROCEDURE를 FALSE로 자동 처리하지 않음": (
            all_unset
        ),
    }


# ============================================================
# main
# ============================================================

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
        get_declared_procedure_conditions(
            clause_data
        )
    )

    extracted = (
        extract_procedure_conditions(
            clauses
        )
    )

    extracted_names = (
        extracted[
            "names"
        ]
    )

    procedure_conditions = [
        build_condition_entry(
            name,
            extracted,
        )
        for name
        in extracted_names
    ]

    fields = {}

    for condition in procedure_conditions:

        field = condition.get(
            "field"
        )

        if field:

            fields[
                field
            ] = None

    state_summary = (
        summarize_states(
            procedure_conditions
        )
    )

    validations = (
        validate_profile(
            declared,
            extracted_names,
            procedure_conditions,
        )
    )

    all_pass = all(
        validations.values()
    )

    output = {
        "step": (
            STEP_NAME
        ),

        "profile_version": (
            "1.0"
        ),

        "profile_type": (
            "ProcedureProfile"
        ),

        "state_model": {
            "TRUE": (
                "필요한 절차 또는 심의가 충족/완료됨"
            ),

            "FALSE": (
                "필요한 절차 조건을 충족하지 않음"
            ),

            "UNKNOWN": (
                "절차 관련 정보는 있으나 "
                "충족 여부를 확정할 수 없음"
            ),

            "UNSET": (
                "절차 정보가 아직 입력되지 않음"
            ),
        },

        "fields": (
            fields
        ),

        "conditions": (
            procedure_conditions
        ),

        "summary": {
            "condition_count": (
                len(
                    procedure_conditions
                )
            ),

            **state_summary,
        },

        "source_validation": {
            "declared_conditions": (
                declared
            ),

            "clause_extracted_conditions": (
                extracted_names
            ),

            "missing_from_clauses": sorted(
                set(
                    declared
                )
                - set(
                    extracted_names
                )
            ),

            "undeclared_in_clauses": sorted(
                set(
                    extracted_names
                )
                - set(
                    declared
                )
            ),
        },

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
        "PROCEDURE conditions:",
        len(
            procedure_conditions
        ),
    )

    print(
        "Declared:",
        len(
            declared
        ),
    )

    print(
        "Extracted:",
        len(
            extracted_names
        ),
    )

    print()

    for condition in (
        procedure_conditions
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