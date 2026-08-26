from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TARGET_NAME = "개발밀도관리구역"

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "development_density_management_area_document_parser_execution.json"
)


TARGET_RESOLUTION_TOKEN = "TARGET_CANDIDATE"


def load_json(path: Path) -> Any:
    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def walk(
    value: Any,
    path: str = "$",
):
    if isinstance(value, dict):
        yield path, value

        for key, child in value.items():
            yield from walk(
                child,
                f"{path}.{key}",
            )

    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(
                child,
                f"{path}[{index}]",
            )


def preview(value: Any, limit: int = 500) -> str:
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\n", " ").replace("\r", " ")

    while "  " in text:
        text = text.replace("  ", " ")

    return text[:limit]


def main() -> None:
    print("=" * 70)
    print("PARSER OUTPUT CONTRACT INSPECTION")
    print("=" * 70)
    print()

    print(f"Input: {INPUT_PATH}")
    print()

    if not INPUT_PATH.exists():
        raise FileNotFoundError(INPUT_PATH)

    data = load_json(INPUT_PATH)

    all_records = list(walk(data))

    resolution_records = []
    target_text_records = []

    # ========================================================
    # 1. TARGET_CANDIDATE resolution record
    # ========================================================

    for path, record in all_records:
        resolution = record.get("resolution")

        if not isinstance(resolution, str):
            continue

        if TARGET_RESOLUTION_TOKEN not in resolution:
            continue

        resolution_records.append(
            (path, record)
        )

    # ========================================================
    # 2. 실제 target 문자열을 포함하는 모든 string field
    # ========================================================

    for path, record in all_records:
        matching_fields = []

        for key, value in record.items():
            if not isinstance(value, str):
                continue

            if TARGET_NAME not in value:
                continue

            matching_fields.append(
                (
                    key,
                    value,
                )
            )

        if matching_fields:
            target_text_records.append(
                (
                    path,
                    record,
                    matching_fields,
                )
            )

    # ========================================================
    # OUTPUT
    # ========================================================

    print(
        "Resolution target candidate record count: "
        f"{len(resolution_records)}"
    )

    print(
        "Actual target-text record count: "
        f"{len(target_text_records)}"
    )

    print()

    print("=" * 70)
    print("TARGET CANDIDATE RESOLUTION RECORDS")
    print("=" * 70)

    for index, (path, record) in enumerate(
        resolution_records,
        start=1,
    ):
        print()
        print("-" * 70)
        print(f"RESOLUTION RECORD {index}")
        print(f"Path: {path}")
        print(f"Resolution: {record.get('resolution')}")
        print(f"Keys: {sorted(record.keys())}")

        print()
        print("Important fields:")

        for key in [
            "candidate_index",
            "index",
            "region",
            "url",
            "download_url",
            "final_url",
            "source_url",
            "document_url",
            "parser",
            "declared_type",
            "detected_type",
            "target_in_text",
            "target_found",
            "target_in_extracted_text",
            "text_length",
            "extracted_text_length",
        ]:
            if key not in record:
                continue

            print(
                f"  {key}: "
                f"{preview(record.get(key))}"
            )

        print()
        print("String fields:")

        for key, value in record.items():
            if not isinstance(value, str):
                continue

            print(
                f"  {key}: "
                f"{preview(value)}"
            )

    print()
    print("=" * 70)
    print("ACTUAL TARGET TEXT RECORDS")
    print("=" * 70)

    for index, (
        path,
        record,
        matching_fields,
    ) in enumerate(
        target_text_records,
        start=1,
    ):
        print()
        print("-" * 70)
        print(f"TARGET TEXT RECORD {index}")
        print(f"Path: {path}")
        print(f"Keys: {sorted(record.keys())}")

        for key, value in matching_fields:
            print()
            print(f"Field: {key}")
            print(
                "Preview: "
                f"{preview(value, 1200)}"
            )

    # ========================================================
    # TOP-LEVEL STRUCTURE
    # ========================================================

    print()
    print("=" * 70)
    print("TOP LEVEL")
    print("=" * 70)

    if isinstance(data, dict):
        print(
            f"Top-level keys: {sorted(data.keys())}"
        )

        for key, value in data.items():
            if isinstance(value, list):
                print(
                    f"{key}: list[{len(value)}]"
                )

            elif isinstance(value, dict):
                print(
                    f"{key}: dict keys="
                    f"{sorted(value.keys())[:30]}"
                )

            else:
                print(
                    f"{key}: {preview(value)}"
                )

    print()
    print("=" * 70)
    print("CONTRACT DIAGNOSIS")
    print("=" * 70)

    if (
        resolution_records
        and target_text_records
    ):
        print(
            "TARGET_TEXT_EXISTS_SEPARATELY_FROM_RESOLUTION_RECORD"
        )
        print()
        print(
            "X-stage artifact contains both candidate resolution "
            "and target-bearing text. "
            "Y-stage sibling-record reconstruction is required."
        )

    elif (
        resolution_records
        and not target_text_records
    ):
        print(
            "TARGET_TEXT_NOT_PERSISTED_IN_X_STAGE_ARTIFACT"
        )
        print()
        print(
            "X-stage detected the target during parser execution, "
            "but the extracted target-bearing text was not written "
            "to the JSON artifact."
        )
        print()
        print(
            "Fix X-stage output first: persist extracted_text or "
            "target_context for every TARGET_CANDIDATE record."
        )

    elif target_text_records:
        print(
            "TARGET_TEXT_EXISTS_WITHOUT_TARGET_RESOLUTION_RECORD"
        )

    else:
        print(
            "NO_TARGET_EVIDENCE_IN_X_STAGE_ARTIFACT"
        )


if __name__ == "__main__":
    main()