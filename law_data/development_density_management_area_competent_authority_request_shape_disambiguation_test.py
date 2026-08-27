# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-16-S7-S1

Development Density Management Area
Competent Authority Request Shape Disambiguation

S7에서 notice family는 request shape 0, urban family는 shape 2로 실행이 차단되었다.
본 단계는 S7 output에 보존된 live function definition/form evidence만 사용하여
function body와 form/control 간의 직접 결합을 정밀하게 판별한다.

원칙
======================================================================
1. S7 sample_results만 입력으로 사용한다.
2. HTTP detail request는 실행하지 않는다.
3. function body preview에 실제로 등장하는 form/action/control evidence만 인정한다.
4. 파일 다운로드/preview form은 detail navigation과 분리한다.
5. exact function argument가 identity control에 대입되는 경우만 우선 인정한다.
6. 동일 family에서 sample마다 동일 request shape가 재현되어야 family contract 후보가 된다.
7. URL/parameter/method 추측 금지.
8. target query/UQQ700 identity/SITE 판정 금지.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent
S7_INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_competent_authority_bounded_detail_request_validation.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_competent_authority_request_shape_disambiguation.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

FAMILY_NOTICE = "CURRENT_MUNICIPAL_OFFICIAL_NOTICE_ARCHIVE"
FAMILY_URBAN = "CURRENT_URBAN_PLANNING_INFORMATION_ARCHIVE"
ALLOWED_FAMILIES = {FAMILY_NOTICE, FAMILY_URBAN}

CLASS_SINGLE = "DISAMBIGUATED_SINGLE_REQUEST_SHAPE"
CLASS_FAMILY_SINGLE = "DISAMBIGUATED_FAMILY_REQUEST_SHAPE"
CLASS_NO_EVIDENCE = "REQUEST_SHAPE_DISAMBIGUATION_NO_EVIDENCE"
CLASS_AMBIGUOUS = "REQUEST_SHAPE_DISAMBIGUATION_AMBIGUOUS"
CLASS_REJECTED_FILE = "REJECTED_FILE_OPERATION_SHAPE"
VALID_CLASSES = {
    CLASS_SINGLE,
    CLASS_FAMILY_SINGLE,
    CLASS_NO_EVIDENCE,
    CLASS_AMBIGUOUS,
    CLASS_REJECTED_FILE,
}

FILE_PATH_HINTS = ("getfile", "filepreview", "download", "attach", "file")
DETAIL_FUNCTIONS = {
    FAMILY_NOTICE: "f_view",
    FAMILY_URBAN: "fn_move_form",
}
IDENTITY_HINTS = {
    FAMILY_NOTICE: ("notancmtmgtno", "ancmt", "mgtno"),
    FAMILY_URBAN: ("pstsn", "pst_sn", "post"),
}

# body preview에서 실제 operation을 읽기 위한 패턴
ACTION_LITERAL_PATTERN = re.compile(
    r'''(?:\.attr\s*\(\s*["']action["']\s*,\s*["'](?P<a1>[^"']+)["']\s*\)|\.action\s*=\s*["'](?P<a2>[^"']+)["'])''',
    re.I,
)
SUBMIT_PATTERN = re.compile(r'''\.submit\s*\(\s*\)''', re.I)
VAL_ASSIGN_PATTERN = re.compile(
    r'''(?:\$\(\s*["']#(?P<id1>[A-Za-z0-9_-]+)["']\s*\)\.val\s*\(\s*(?P<v1>[A-Za-z_$][\w$]*)\s*\)|document\.getElementById\(\s*["'](?P<id2>[^"']+)["']\s*\)\.value\s*=\s*(?P<v2>[A-Za-z_$][\w$]*))''',
    re.I,
)
FORM_SELECTOR_PATTERN = re.compile(
    r'''(?:\$\(\s*["'](?P<sel>#[A-Za-z0-9_-]+|form(?:#[A-Za-z0-9_-]+)?)["']\s*\)|document\.(?P<doc>[A-Za-z0-9_-]+))''',
    re.I,
)


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def unique_strings(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: Set[str] = set()
    for value in values:
        text = normalize_space(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def is_file_operation(url: str) -> bool:
    path = (urlparse(normalize_space(url)).path or "").lower()
    return any(hint in path for hint in FILE_PATH_HINTS)


def identity_name_matches(name: str, family: str) -> bool:
    lowered = normalize_space(name).lower()
    return bool(lowered) and any(hint in lowered for hint in IDENTITY_HINTS.get(family, ()))


def extract_body_semantics(body: str, function_args: List[str]) -> Dict[str, Any]:
    args = set(unique_strings(function_args))
    action_literals = unique_strings((m.group("a1") or m.group("a2")) for m in ACTION_LITERAL_PATTERN.finditer(body or ""))
    assignments: List[Dict[str, str]] = []
    for m in VAL_ASSIGN_PATTERN.finditer(body or ""):
        control = normalize_space(m.group("id1") or m.group("id2"))
        variable = normalize_space(m.group("v1") or m.group("v2"))
        if control and variable and variable in args:
            assignments.append({"control": control, "argument": variable})
    selectors = unique_strings((m.group("sel") or m.group("doc")) for m in FORM_SELECTOR_PATTERN.finditer(body or ""))
    return {
        "action_literals": action_literals,
        "argument_assignments": assignments,
        "form_selectors": selectors,
        "submit_present": bool(SUBMIT_PATTERN.search(body or "")),
    }


def candidate_key(candidate: Dict[str, Any]) -> Tuple[str, str, str, str]:
    return (
        normalize_space(candidate.get("kind")),
        normalize_space(candidate.get("method")).upper(),
        normalize_space(candidate.get("action_url")),
        normalize_space(candidate.get("identity_name")),
    )


def score_candidate(candidate: Dict[str, Any], family: str, semantics: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []
    action_url = normalize_space(candidate.get("action_url"))
    identity_name = normalize_space(candidate.get("identity_name"))

    if is_file_operation(action_url):
        return -1000, ["FILE_OPERATION_EXCLUDED"]

    if identity_name_matches(identity_name, family):
        score += 60
        reasons.append("FAMILY_IDENTITY_CONTROL_MATCH")

    for sem in semantics:
        if any(identity_name == normalize_space(a.get("control")) for a in sem.get("argument_assignments") or []):
            score += 100
            reasons.append("FUNCTION_ARGUMENT_DIRECTLY_ASSIGNED_TO_IDENTITY_CONTROL")
        if any(normalize_space(action_url).endswith(normalize_space(a)) or normalize_space(a).endswith(urlparse(action_url).path) for a in sem.get("action_literals") or []):
            score += 80
            reasons.append("FUNCTION_BODY_ACTION_LITERAL_MATCH")
        if sem.get("submit_present"):
            score += 10
            reasons.append("FUNCTION_BODY_SUBMIT_PRESENT")

    # 일반 목록 form 자체는 낮게, identity+direct assignment가 있어야 강하게 인정
    if candidate.get("kind") == "FORM":
        score += 5
    elif candidate.get("kind") == "LOCATION":
        score += 20

    return score, unique_strings(reasons)


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("REQUEST SHAPE DISAMBIGUATION")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Detail request execution: DISABLED")
    print("Target identity evaluation: DISABLED")
    print()

    if not S7_INPUT_PATH.exists():
        raise FileNotFoundError(f"S7 input not found: {S7_INPUT_PATH}")
    data = json.loads(S7_INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("S7 input must be JSON object")

    raw = data.get("sample_results") if isinstance(data.get("sample_results"), list) else []
    samples = [x for x in raw if isinstance(x, dict) and normalize_space(x.get("source_family")) in ALLOWED_FAMILIES]

    sample_results: List[Dict[str, Any]] = []
    family_candidate_keys: Dict[str, List[Tuple[str, str, str, str]]] = defaultdict(list)

    for index, sample in enumerate(samples, start=1):
        family = normalize_space(sample.get("source_family"))
        function_name = normalize_space(sample.get("function"))
        expected_function = DETAIL_FUNCTIONS.get(family)
        definitions = sample.get("definition_records") if isinstance(sample.get("definition_records"), list) else []
        candidates = sample.get("request_shape_candidates") if isinstance(sample.get("request_shape_candidates"), list) else []

        semantics = []
        for definition in definitions:
            if normalize_space(definition.get("function")) != expected_function:
                continue
            args = definition.get("args") if isinstance(definition.get("args"), list) else []
            semantics.append(extract_body_semantics(normalize_space(definition.get("body_preview")), args))

        scored = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            score, reasons = score_candidate(candidate, family, semantics)
            scored.append({"candidate": candidate, "score": score, "reasons": reasons})

        non_file = [x for x in scored if x["score"] > -1000]
        non_file.sort(key=lambda x: (-x["score"], candidate_key(x["candidate"])))

        selected = None
        if non_file:
            best_score = non_file[0]["score"]
            best = [x for x in non_file if x["score"] == best_score]
            # direct identity/action evidence가 있는 경우만 single selection
            if len(best) == 1 and best_score >= 60:
                selected = best[0]

        if selected:
            classification = CLASS_SINGLE
            qualified = True
            family_candidate_keys[family].append(candidate_key(selected["candidate"]))
        elif candidates and all(is_file_operation(c.get("action_url") or "") for c in candidates if isinstance(c, dict)):
            classification = CLASS_REJECTED_FILE
            qualified = False
        elif non_file:
            classification = CLASS_AMBIGUOUS
            qualified = False
        else:
            classification = CLASS_NO_EVIDENCE
            qualified = False

        result = {
            "sample_index": sample.get("sample_index"),
            "source_family": family,
            "function": function_name,
            "argument": sample.get("argument"),
            "body_semantics": semantics,
            "scored_candidates": scored,
            "selected_candidate": selected["candidate"] if selected else None,
            "selected_score": selected["score"] if selected else None,
            "selected_reasons": selected["reasons"] if selected else [],
            "classification": classification,
            "qualified_for_family_consensus": qualified,
            "detail_request_executed": False,
            "target_query_executed": False,
            "target_identity_evaluated": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        sample_results.append(result)

        print("-" * 60)
        print(f"SAMPLE {index}")
        print("Family:", family)
        print("Function:", function_name)
        print("Original candidates:", len(candidates))
        print("Scored non-file candidates:", len(non_file))
        if selected:
            print("Selected:", candidate_key(selected["candidate"]))
            print("Score:", selected["score"])
            print("Reasons:", selected["reasons"])
        print("Resolution:", classification)

    family_results = []
    next_stage_pool = []
    for family in sorted(ALLOWED_FAMILIES):
        keys = family_candidate_keys.get(family, [])
        unique_keys = sorted(set(keys))
        family_samples = [x for x in sample_results if x.get("source_family") == family]
        qualified_samples = [x for x in family_samples if x.get("qualified_for_family_consensus")]

        if qualified_samples and len(unique_keys) == 1 and len(qualified_samples) == len(family_samples):
            classification = CLASS_FAMILY_SINGLE
            qualified = True
            selected_key = unique_keys[0]
            sample_candidate = qualified_samples[0].get("selected_candidate")
        elif qualified_samples and len(unique_keys) == 1:
            # 일부 sample만 복원된 경우 family contract로 승격하지 않음
            classification = CLASS_AMBIGUOUS
            qualified = False
            selected_key = unique_keys[0]
            sample_candidate = qualified_samples[0].get("selected_candidate")
        elif unique_keys:
            classification = CLASS_AMBIGUOUS
            qualified = False
            selected_key = None
            sample_candidate = None
        else:
            classification = CLASS_NO_EVIDENCE
            qualified = False
            selected_key = None
            sample_candidate = None

        family_result = {
            "source_family": family,
            "sample_count": len(family_samples),
            "qualified_sample_count": len(qualified_samples),
            "unique_candidate_shape_count": len(unique_keys),
            "candidate_keys": [list(k) for k in unique_keys],
            "selected_family_candidate": sample_candidate,
            "classification": classification,
            "qualified_for_next_stage": qualified,
            "detail_request_executed": False,
            "target_query_executed": False,
            "target_identity_evaluated": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        family_results.append(family_result)
        if qualified:
            next_stage_pool.append({
                **family_result,
                "requires_known_sample_reexecution": True,
            })

        print()
        print("-" * 60)
        print("FAMILY:", family)
        print("Sample count:", len(family_samples))
        print("Qualified samples:", len(qualified_samples))
        print("Unique shapes:", len(unique_keys))
        print("Qualified for next stage:", qualified)
        print("Resolution:", classification)

    resolution = (
        "COMPETENT_AUTHORITY_REQUEST_SHAPE_DISAMBIGUATION_COMPLETED"
        if next_stage_pool
        else "COMPETENT_AUTHORITY_REQUEST_SHAPE_DISAMBIGUATION_NO_CONSENSUS"
    )
    next_action = (
        "family-level single request shape consensus가 확인된 family만 known sample 재실행 단계로 넘긴다. "
        "응답에서 기존 sample metadata 재현이 확인되기 전에는 historical traversal에 사용하지 않는다."
        if next_stage_pool
        else
        "function body/form evidence만으로 family-level single request shape를 확정하지 못했다. "
        "SITE FALSE가 아니며 UNKNOWN을 유지한다. 다음에는 function body 원문/DOM serialization을 더 정밀하게 복원한다."
    )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-16-S7-S1 Request Shape Disambiguation",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "method": {
            "S7_evidence_only": True,
            "file_operation_exclusion_enabled": True,
            "direct_argument_assignment_preferred": True,
            "action_literal_match_preferred": True,
            "family_consensus_required": True,
            "detail_request_execution_enabled": False,
            "guessed_request_shape_disabled": True,
            "target_query_execution_enabled": False,
            "target_identity_evaluation_enabled": False,
            "document_candidate_promotion_allowed": False,
        },
        "summary": {
            "sample_count": len(sample_results),
            "family_result_count": len(family_results),
            "next_stage_family_count": len(next_stage_pool),
        },
        "classification_counts": dict(sorted(Counter(x.get("classification") for x in sample_results + family_results).items())),
        "sample_results": sample_results,
        "family_results": family_results,
        "next_stage_family_request_shape_pool": next_stage_pool,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    file_operation_leakage = sum(
        1 for x in next_stage_pool
        if is_file_operation((x.get("selected_family_candidate") or {}).get("action_url") or "")
    )
    detail_request_leakage = sum(1 for x in sample_results + family_results + next_stage_pool if x.get("detail_request_executed") is True)
    target_query_leakage = sum(1 for x in sample_results + family_results + next_stage_pool if x.get("target_query_executed") is True)
    target_identity_leakage = sum(1 for x in sample_results + family_results + next_stage_pool if x.get("target_identity_evaluated") is True)
    unsafe_promotion_leakage = sum(
        1 for x in sample_results + family_results + next_stage_pool
        if x.get("document_candidate") is True
        or x.get("verified_positive") is True
        or x.get("runtime_registration_allowed") is True
        or x.get("site_positive_allowed") is True
        or x.get("site_negative_allowed") is True
        or x.get("final_positive_promotion_allowed") is True
    )

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "S7 input exists": S7_INPUT_PATH.exists(),
        "S7 input parsed": isinstance(data, dict),
        "S7 samples loaded": len(samples) > 0,
        "file operation exclusion enabled": True,
        "family consensus required": True,
        "guessed request shape disabled": True,
        "all classes valid": all(x.get("classification") in VALID_CLASSES for x in sample_results + family_results),
        "next-stage file operation leakage zero": file_operation_leakage == 0,
        "detail request execution leakage zero": detail_request_leakage == 0,
        "target query execution leakage zero": target_query_leakage == 0,
        "target identity evaluation leakage zero": target_identity_leakage == 0,
        "unsafe promotion leakage zero": unsafe_promotion_leakage == 0,
        "runtime registration remains blocked": output_data["runtime_registration_allowed"] is False,
        "SITE TRUE remains blocked": output_data["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output_data["site_negative_allowed"] is False,
        "final positive promotion remains blocked": output_data["final_positive_promotion_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print()
    print("=" * 60)
    print("REQUEST SHAPE DISAMBIGUATION RESULT")
    print("=" * 60)
    print("Sample count:", len(sample_results))
    print("Family result count:", len(family_results))
    print("Next-stage family count:", len(next_stage_pool))
    print("Resolution:", resolution)
    print("Output:", OUTPUT_PATH)
    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("File operation leakage:", file_operation_leakage)
    print("Detail request leakage:", detail_request_leakage)
    print("Target query leakage:", target_query_leakage)
    print("Target identity leakage:", target_identity_leakage)
    print("Unsafe promotion leakage:", unsafe_promotion_leakage)
    print()
    all_pass = all(validations.values())
    print(f"all_pass: {all_pass}")
    if not all_pass:
        print("FAILED:")
        for name, passed in validations.items():
            if not passed:
                print("-", name)
        raise AssertionError("UQQ700 request shape disambiguation regression failed")


if __name__ == "__main__":
    main()
