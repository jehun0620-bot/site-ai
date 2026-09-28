# -*- coding: utf-8 -*-
"""
Building Act Enforcement Decree Annex 1 structural parser test.

Scope
-----
Parse the verified official Annex 1 text into source structure only.

This test:
- reuses the existing official API + appendix normalization path,
- separates the building-use body from the explicit "비고" section,
- reconstructs physical API line wraps before marker parsing,
- parses major (1.), subitem (가.), and detail (1)) source nodes,
- verifies selected known paths and false-positive boundaries.

It does NOT assign Canonical Building Use semantics, connect PROJECT facts,
evaluate numeric predicates, or modify production/generated rule data.
"""

from __future__ import annotations

import re

from building_act_enforcement_decree_annex1_source_probe_test import (
    find_annex1,
    search_current_target,
    text_value,
)
from law_detail_normalize_test import normalize_detail, request_detail


MAJOR_RE = re.compile(r"^(\d+)(?:의(\d+))?\.\s*(.*)$")
SUBITEM_RE = re.compile(r"^([가-힣]+)\.\s*(.*)$")
DETAIL_RE = re.compile(r"^(\d+)\)\s*(.*)$")
NOTE_MARKER = "비고"


def split_annex_sections(content: str) -> tuple[list[str], list[str], list[str]]:
    lines = content.splitlines()
    note_indexes = [
        index for index, line in enumerate(lines)
        if line.strip() == NOTE_MARKER
    ]

    if len(note_indexes) != 1:
        raise AssertionError(
            f'Expected exactly one "{NOTE_MARKER}" marker; '
            f"found {len(note_indexes)}."
        )

    note_index = note_indexes[0]
    major_indexes = [
        index for index, line in enumerate(lines[:note_index])
        if MAJOR_RE.match(line.strip())
    ]

    if not major_indexes:
        raise AssertionError("No major building-use marker found.")

    body_start = major_indexes[0]

    return (
        lines[:body_start],
        lines[body_start:note_index],
        lines[note_index + 1:],
    )


def marker_kind(text: str) -> str | None:
    if MAJOR_RE.match(text):
        return "MAJOR"
    if SUBITEM_RE.match(text):
        return "SUBITEM"
    if DETAIL_RE.match(text):
        return "DETAIL"
    return None


def starts_with_valid_marker(
    text: str,
    *,
    current_major: tuple[int, int] | None,
    last_subitem: str | None,
    last_detail: int | None,
) -> bool:
    major = MAJOR_RE.match(text)
    if major:
        number = int(major.group(1))
        branch_number = int(major.group(2) or 0)
        candidate = (number, branch_number)

        if current_major is None:
            return candidate == (1, 0)

        current_number, current_branch = current_major

        if number == current_number:
            return branch_number == current_branch + 1 and branch_number > 0

        return number == current_number + 1 and branch_number == 0

    detail = DETAIL_RE.match(text)
    if detail:
        number = int(detail.group(1))
        if last_detail is None:
            return number == 1
        return number == last_detail + 1

    subitem = SUBITEM_RE.match(text)
    if subitem:
        code = subitem.group(1)

        # Annex 1 subitems progress through the Korean legal item sequence.
        # A wrapped word such as "말한" + "다. 이하 같다" must therefore
        # not become a new subitem unless it is the expected next code.
        sequence = [
            "가", "나", "다", "라", "마", "바", "사", "아", "자", "차",
            "카", "타", "파", "하", "거", "너", "더", "러", "머", "버",
            "서", "어", "저", "처", "커", "터", "퍼", "허",
        ]

        if code not in sequence:
            return False

        if last_subitem is None:
            return code == "가"

        try:
            return sequence.index(code) == sequence.index(last_subitem) + 1
        except ValueError:
            return False

    return False


def reconstruct_body_units(body_lines: list[str]) -> list[dict]:
    units: list[dict] = []
    current_text = ""
    current_raw_lines: list[str] = []
    current_major: tuple[int, int] | None = None
    last_subitem: str | None = None
    last_detail: int | None = None

    for raw_line in body_lines:
        text = raw_line.strip()
        if not text:
            continue

        if starts_with_valid_marker(
            text,
            current_major=current_major,
            last_subitem=last_subitem,
            last_detail=last_detail,
        ):
            if current_text:
                units.append({
                    "text": current_text,
                    "raw_lines": current_raw_lines,
                })

            current_text = text
            current_raw_lines = [raw_line]

            major = MAJOR_RE.match(text)
            subitem = SUBITEM_RE.match(text)
            detail = DETAIL_RE.match(text)

            if major:
                current_major = (
                    int(major.group(1)),
                    int(major.group(2) or 0),
                )
                last_subitem = None
                last_detail = None
            elif subitem:
                last_subitem = subitem.group(1)
                last_detail = None
            elif detail:
                last_detail = int(detail.group(1))
        else:
            # The API may wrap inside a Korean word. Joining without an
            # inserted space restores cases such as "말한" + "다.".
            current_text += text
            current_raw_lines.append(raw_line)

    if current_text:
        units.append({
            "text": current_text,
            "raw_lines": current_raw_lines,
        })

    return units


def parse_structure(units: list[dict]) -> list[dict]:
    majors: list[dict] = []
    current_major: dict | None = None
    current_subitem: dict | None = None

    for unit in units:
        text = unit["text"]
        raw_lines = unit["raw_lines"]
        major = MAJOR_RE.match(text)
        if major:
            current_major = {
                "number": int(major.group(1)),
                "branch_number": int(major.group(2) or 0),
                "source_label": (
                    major.group(1)
                    if major.group(2) is None
                    else f"{major.group(1)}의{major.group(2)}"
                ),
                "text": major.group(3).strip(),
                "raw_lines": raw_lines,
                "subitems": [],
                "direct_text": [],
            }
            majors.append(current_major)
            current_subitem = None
            continue

        subitem = SUBITEM_RE.match(text)
        if subitem:
            if current_major is None:
                raise AssertionError("Subitem appeared before a major node.")

            current_subitem = {
                "code": subitem.group(1),
                "text": subitem.group(2).strip(),
                "raw_lines": raw_lines,
                "details": [],
            }
            current_major["subitems"].append(current_subitem)
            continue

        detail = DETAIL_RE.match(text)
        if detail:
            if current_major is None:
                raise AssertionError("Detail appeared before a major node.")

            node = {
                "number": int(detail.group(1)),
                "text": detail.group(2).strip(),
                "raw_lines": raw_lines,
            }

            if current_subitem is not None:
                current_subitem["details"].append(node)
            else:
                current_major["direct_text"].append(node)
            continue

        raise AssertionError(f"Unclassified reconstructed unit: {text[:120]}")

    return majors


def find_major(
    majors: list[dict],
    number: int,
    branch_number: int = 0,
) -> dict:
    matches = [
        node for node in majors
        if node["number"] == number
        and node["branch_number"] == branch_number
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"Expected one major {number} branch {branch_number}; "
            f"found {len(matches)}."
        )
    return matches[0]


def find_subitem(major: dict, code: str) -> dict:
    matches = [
        node for node in major["subitems"]
        if node["code"] == code
    ]
    if len(matches) != 1:
        raise AssertionError(
            f'Expected one subitem "{code}" in major '
            f'{major["number"]}; found {len(matches)}.'
        )
    return matches[0]


def find_detail(subitem: dict, number: int) -> dict:
    matches = [
        node for node in subitem["details"]
        if node["number"] == number
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"Expected one detail {number}; found {len(matches)}."
        )
    return matches[0]


def main() -> None:
    print("=" * 70)
    print("BUILDING USE ANNEX 1 STRUCTURAL PARSER")
    print("=" * 70)

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

    header_lines, body_lines, note_lines = split_annex_sections(content)
    units = reconstruct_body_units(body_lines)
    majors = parse_structure(units)

    source_labels = [node["source_label"] for node in majors]
    expected_source_labels = (
        [str(number) for number in range(1, 24)]
        + ["23의2"]
        + [str(number) for number in range(24, 30)]
    )
    if source_labels != expected_source_labels:
        raise AssertionError(
            "Expected major source labels 1..23, 23의2, 24..29; "
            f"got {source_labels}."
        )

    major23 = find_major(majors, 23)
    deleted23ra = find_subitem(major23, "라")
    if not deleted23ra["text"].startswith("삭제"):
        raise AssertionError("23/라 is not the deleted source subitem.")

    major23_2 = find_major(majors, 23, 2)
    if not major23_2["text"].startswith("국방ㆍ군사시설("):
        raise AssertionError("23의2 is not 국방ㆍ군사시설.")

    if not any(
        "국방ㆍ군사시설 사업에 관한 법률" in line
        for line in major23_2["raw_lines"]
    ):
        raise AssertionError(
            "23의2 raw_lines lost the following military-facility definition."
        )

    major24 = find_major(majors, 24)
    if not major24["text"].startswith("방송통신시설("):
        raise AssertionError("24 is not 방송통신시설.")

    major2 = find_major(majors, 2)
    dormitory = find_subitem(major2, "라")
    general_dormitory = find_detail(dormitory, 1)
    rental_dormitory = find_detail(dormitory, 2)

    if not general_dormitory["text"].startswith("일반기숙사:"):
        raise AssertionError("2/라/1 is not 일반기숙사.")

    if not rental_dormitory["text"].startswith("임대형기숙사:"):
        raise AssertionError("2/라/2 is not 임대형기숙사.")

    major14 = find_major(majors, 14)
    general_office = find_subitem(major14, "나")
    officetel = find_detail(general_office, 2)

    if not officetel["text"].startswith("오피스텔("):
        raise AssertionError("14/나/2 is not 오피스텔.")

    major4 = find_major(majors, 4)
    codes4 = [node["code"] for node in major4["subitems"]]
    if codes4.count("다") != 1:
        raise AssertionError(
            "Wrapped text produced a false-positive 다 subitem."
        )

    if any(node["number"] > 29 for node in majors):
        raise AssertionError("Note numbering leaked into major nodes.")

    if not note_lines:
        raise AssertionError("Note section is empty.")

    if not any(
        line.rstrip().endswith("사용하는")
        for line in general_dormitory["raw_lines"]
    ):
        raise AssertionError(
            "2/라/1 raw_lines lost the physical line ending with 사용하는."
        )

    if not any(
        line.strip().startswith("것으로서")
        for line in general_dormitory["raw_lines"]
    ):
        raise AssertionError(
            "2/라/1 raw_lines lost the physical line starting with 것으로서."
        )

    multi_living = find_subitem(major4, "거")
    if not any(
        line.rstrip().endswith("말한")
        for line in multi_living["raw_lines"]
    ):
        raise AssertionError(
            "4/거 raw_lines lost the physical line ending with 말한."
        )

    if not any(
        line.strip().startswith("다. 이하 같다)")
        for line in multi_living["raw_lines"]
    ):
        raise AssertionError(
            "4/거 raw_lines lost the wrapped continuation starting with 다."
        )

    print("Resolved current MST:", target["mst"])
    print("Annex 1 content length:", len(content))
    print("Header line count:", len(header_lines))
    print("Body physical line count:", len(body_lines))
    print("Note physical line count:", len(note_lines))
    print("Reconstructed structural unit count:", len(units))
    print("Major count:", len(majors))
    print("Major source labels:", ", ".join(source_labels))
    print("23/라:", deleted23ra["text"][:80])
    print("23의2:", major23_2["text"][:80])
    print("23의2 raw line count:", len(major23_2["raw_lines"]))
    print("24:", major24["text"][:80])
    print("Major range:", f'{majors[0]["number"]}..{majors[-1]["number"]}')
    print("2/라/1:", general_dormitory["text"][:80])
    print("2/라/2:", rental_dormitory["text"][:80])
    print("14/나/2:", officetel["text"][:80])
    print('Major 4 "다" count:', codes4.count("다"))
    print("2/라/1 raw line count:", len(general_dormitory["raw_lines"]))
    print("4/거 raw line count:", len(multi_living["raw_lines"]))
    print("Note starts:", note_lines[0][:100])
    print("RESULT: PASS")
    print(
        "Meaning: Annex 1 body structure can be separated and parsed "
        "without treating the explicit note section as building-use majors."
    )
    print(
        "Not proven: Canonical Building Use semantics, qualification "
        "predicates, numeric evaluation, or Rule Engine integration."
    )


if __name__ == "__main__":
    main()
