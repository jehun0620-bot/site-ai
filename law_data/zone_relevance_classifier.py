import re
from typing import Any, Dict, List, Optional


EXACT_ZONES = [
    "제1종전용주거지역",
    "제2종전용주거지역",
    "제1종일반주거지역",
    "제2종일반주거지역",
    "제3종일반주거지역",
    "준주거지역",
    "중심상업지역",
    "일반상업지역",
    "근린상업지역",
    "유통상업지역",
    "전용공업지역",
    "일반공업지역",
    "준공업지역",
    "보전녹지지역",
    "생산녹지지역",
    "자연녹지지역",
    "보전관리지역",
    "생산관리지역",
    "계획관리지역",
    "농림지역",
    "자연환경보전지역",
]


ZONE_GROUPS = {
    "도시지역": {
        "제1종전용주거지역", "제2종전용주거지역",
        "제1종일반주거지역", "제2종일반주거지역", "제3종일반주거지역",
        "준주거지역",
        "중심상업지역", "일반상업지역", "근린상업지역", "유통상업지역",
        "전용공업지역", "일반공업지역", "준공업지역",
        "보전녹지지역", "생산녹지지역", "자연녹지지역",
    },
    "주거지역": {
        "제1종전용주거지역", "제2종전용주거지역",
        "제1종일반주거지역", "제2종일반주거지역", "제3종일반주거지역",
        "준주거지역",
    },
    "전용주거지역": {"제1종전용주거지역", "제2종전용주거지역"},
    "일반주거지역": {"제1종일반주거지역", "제2종일반주거지역", "제3종일반주거지역"},
    "상업지역": {"중심상업지역", "일반상업지역", "근린상업지역", "유통상업지역"},
    "공업지역": {"전용공업지역", "일반공업지역", "준공업지역"},
    "녹지지역": {"보전녹지지역", "생산녹지지역", "자연녹지지역"},
    "관리지역": {"보전관리지역", "생산관리지역", "계획관리지역"},
}


def compact_spaces(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_exact_zones(text: str) -> List[str]:
    zones = []
    for zone in sorted(EXACT_ZONES, key=len, reverse=True):
        if zone in text:
            zones.append(zone)
    return list(dict.fromkeys(zones))


def mask_exact_zones(text: str) -> str:
    masked = text
    for i, zone in enumerate(sorted(EXACT_ZONES, key=len, reverse=True)):
        masked = masked.replace(zone, f"__ZONE_{i}__")
    return masked


def extract_zone_groups(text: str) -> List[str]:
    masked = mask_exact_zones(text)
    groups = []
    ordered_groups = sorted(ZONE_GROUPS.keys(), key=len, reverse=True)
    working = masked
    for group in ordered_groups:
        if group not in working:
            continue
        groups.append(group)
        working = working.replace(group, " ")
    return groups


def target_belongs_to_group(target_zone: str, group: str) -> bool:
    return target_zone in ZONE_GROUPS.get(group, set())


def has_restrictive_zone_qualifier(text: str, target_zone: str) -> Optional[str]:
    normalized = compact_spaces(text)
    green_only_patterns = [
        r"도시지역\s*\(\s*녹지지역만\s*해당",
        r"도시지역\s*중\s*녹지지역",
        r"도시지역.*녹지지역만\s*해당",
    ]
    if any(re.search(pattern, normalized) for pattern in green_only_patterns):
        if not target_belongs_to_group(target_zone, "녹지지역"):
            return "도시지역 중 녹지지역에만 적용되는 한정 규정"
    return None


def is_outside_urban_only(
    law_name: str,
    rule_title: str,
    text: str,
    target_zone: str,
) -> bool:
    combined = " ".join([law_name, rule_title, text])
    markers = [
        "도시지역 외 지구단위계획구역",
        "도시지역 외에 지정",
        "도시지역 외의 지역",
    ]
    if not any(marker in combined for marker in markers):
        return False
    return target_belongs_to_group(target_zone, "도시지역")


def classify_zone_relevance(
    target_zone: str,
    own_text: str,
    inherited_context: str,
    law_name: str,
    rule_title: str,
) -> Dict[str, Any]:
    own_exact = extract_exact_zones(own_text)
    own_groups = extract_zone_groups(own_text)
    parent_exact = extract_exact_zones(inherited_context)
    parent_groups = extract_zone_groups(inherited_context)

    if is_outside_urban_only(
        law_name,
        rule_title,
        own_text + " " + inherited_context,
        target_zone,
    ):
        return {
            "status": "OTHER_ZONE",
            "reason": "도시지역 외에만 적용되는 규정이므로 대상 도시지역 SITE에서 제외",
            "zones": own_exact,
            "groups": own_groups,
            "matched_groups": [],
        }

    qualifier_reason = has_restrictive_zone_qualifier(own_text, target_zone)
    if qualifier_reason:
        return {
            "status": "OTHER_ZONE",
            "reason": qualifier_reason,
            "zones": own_exact,
            "groups": own_groups,
            "matched_groups": [],
        }

    if own_exact:
        if target_zone in own_exact:
            return {
                "status": "DIRECT",
                "reason": f"{target_zone} 직접 명시",
                "zones": own_exact,
                "groups": own_groups,
                "matched_groups": [],
            }
        return {
            "status": "OTHER_ZONE",
            "reason": "세부 규정이 정확한 용도지역을 열거하고 있으나 " f"{target_zone}은 해당 목록에 없음",
            "zones": own_exact,
            "groups": own_groups,
            "matched_groups": [],
        }

    matched_groups = [
        group for group in own_groups
        if target_belongs_to_group(target_zone, group)
    ]
    if matched_groups:
        return {
            "status": "GROUP",
            "reason": f"{', '.join(matched_groups)} 규정에 {target_zone} 포함",
            "zones": [],
            "groups": own_groups,
            "matched_groups": matched_groups,
        }
    if own_groups:
        return {
            "status": "OTHER_ZONE",
            "reason": f"{', '.join(own_groups)} 규정은 {target_zone}에 해당하지 않음",
            "zones": [],
            "groups": own_groups,
            "matched_groups": [],
        }

    if parent_exact:
        if target_zone in parent_exact:
            return {
                "status": "DIRECT",
                "reason": "상위 문맥에서 " f"{target_zone} 직접 명시",
                "zones": parent_exact,
                "groups": [],
                "matched_groups": [],
            }
        return {
            "status": "OTHER_ZONE",
            "reason": "상위 문맥이 정확한 용도지역을 제한적으로 열거하며 " f"{target_zone}은 해당 목록에 없음",
            "zones": parent_exact,
            "groups": [],
            "matched_groups": [],
        }

    parent_qualifier = has_restrictive_zone_qualifier(inherited_context, target_zone)
    if parent_qualifier:
        return {
            "status": "OTHER_ZONE",
            "reason": parent_qualifier,
            "zones": [],
            "groups": parent_groups,
            "matched_groups": [],
        }

    parent_matched_groups = [
        group for group in parent_groups
        if target_belongs_to_group(target_zone, group)
    ]
    if parent_matched_groups:
        return {
            "status": "GROUP",
            "reason": "상위 문맥의 " f"{', '.join(parent_matched_groups)} 규정에 {target_zone} 포함",
            "zones": [],
            "groups": parent_groups,
            "matched_groups": parent_matched_groups,
        }
    if parent_groups:
        return {
            "status": "OTHER_ZONE",
            "reason": "상위 문맥의 " f"{', '.join(parent_groups)} 규정은 {target_zone}에 해당하지 않음",
            "zones": [],
            "groups": parent_groups,
            "matched_groups": [],
        }

    return {
        "status": "UNSPECIFIED",
        "reason": "세부 규정 자체와 상위 문맥에서 용도지역을 특정하지 않음",
        "zones": [],
        "groups": [],
        "matched_groups": [],
    }
