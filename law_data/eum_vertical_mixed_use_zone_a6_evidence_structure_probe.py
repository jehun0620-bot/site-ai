from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"

INPUT_PATH = (
    OUTPUT_DIR
    / "eum_vertical_mixed_use_zone_mapplan_live.json"
)


TARGETS = [
    "UQQ300",
    "UQQ905",
    '"layer"',
    "analysis",
    "preview",
    "response",
    "raw",
]


def load_json(path: Path) -> Any:
    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def short(value: Any, length: int = 500) -> str:
    try:
        if isinstance(value, (dict, list)):
            text = json.dumps(
                value,
                ensure_ascii=False,
            )
        else:
            text = str(value)
    except Exception:
        text = repr(value)

    text = text.replace("\n", " ")

    if len(text) > length:
        return text[:length] + "..."

    return text


def walk(
    obj: Any,
    path: str = "$",
    depth: int = 0,
) -> None:

    if isinstance(obj, dict):

        for key, value in obj.items():

            current_path = f"{path}.{key}"

            print(
                f"{'  ' * depth}"
                f"{current_path}"
                f" | type={type(value).__name__}"
                f" | value={short(value, 180)}"
            )

            walk(
                value,
                current_path,
                depth + 1,
            )

    elif isinstance(obj, list):

        for index, value in enumerate(obj):

            current_path = f"{path}[{index}]"

            print(
                f"{'  ' * depth}"
                f"{current_path}"
                f" | type={type(value).__name__}"
                f" | value={short(value, 180)}"
            )

            walk(
                value,
                current_path,
                depth + 1,
            )


def search(
    obj: Any,
    keyword: str,
    path: str = "$",
) -> list[dict]:

    results = []

    if isinstance(obj, dict):

        for key, value in obj.items():

            current_path = f"{path}.{key}"

            if keyword.lower() in str(key).lower():

                results.append(
                    {
                        "path": current_path,
                        "match_type": "KEY",
                        "value": short(value),
                    }
                )

            results.extend(
                search(
                    value,
                    keyword,
                    current_path,
                )
            )

    elif isinstance(obj, list):

        for index, value in enumerate(obj):

            current_path = f"{path}[{index}]"

            results.extend(
                search(
                    value,
                    keyword,
                    current_path,
                )
            )

    else:

        text = str(obj)

        if keyword.lower() in text.lower():

            results.append(
                {
                    "path": path,
                    "match_type": "VALUE",
                    "value": short(obj),
                }
            )

    return results


def main():

    print(
        "=== STEP 17-21-C-9-2-6A-8-DIAG "
        "A-6 Evidence JSON 구조 진단 ==="
    )

    print()
    print("입력:")
    print(INPUT_PATH)

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"A-6 결과 파일 없음: {INPUT_PATH}"
        )

    data = load_json(INPUT_PATH)

    print()
    print("=" * 70)
    print("=== 1. 최상위 구조 ===")
    print("=" * 70)

    print(
        "root type:",
        type(data).__name__,
    )

    if isinstance(data, dict):

        print(
            "top-level keys:",
            list(data.keys()),
        )

    print()
    print("=" * 70)
    print("=== 2. 전체 JSON Path 구조 ===")
    print("=" * 70)

    walk(data)

    print()
    print("=" * 70)
    print("=== 3. 핵심 Evidence 검색 ===")
    print("=" * 70)

    for target in TARGETS:

        print()
        print("-" * 70)
        print(f"검색어: {target}")

        hits = search(
            data,
            target.replace('"', ""),
        )

        print(
            "hit 수:",
            len(hits),
        )

        for index, hit in enumerate(
            hits[:30],
            start=1,
        ):

            print()
            print(f"Hit {index}")
            print(
                "path:",
                hit["path"],
            )
            print(
                "match_type:",
                hit["match_type"],
            )
            print(
                "value:",
                hit["value"],
            )

    print()
    print("=" * 70)
    print("=== 4. 핵심 판정 ===")
    print("=" * 70)

    uqq300_hits = search(
        data,
        "UQQ300",
    )

    uqq905_hits = search(
        data,
        "UQQ905",
    )

    print(
        "UQQ300 JSON 내 존재:",
        bool(uqq300_hits),
    )

    print(
        "UQQ905 JSON 내 존재:",
        bool(uqq905_hits),
    )

    if uqq300_hits:

        print()
        print(
            "→ A-6 JSON 안에 UQQ300 evidence가 존재합니다."
        )

        print(
            "→ A-8 parser의 JSON path/string parsing만 보정하면 됩니다."
        )

    else:

        print()
        print(
            "→ A-6 JSON 안에 UQQ300 문자열 자체가 없습니다."
        )

        print(
            "→ A-6 실행 당시 콘솔에는 존재했지만 "
            "결과 JSON에 raw analysis 응답이 저장되지 않은 상태입니다."
        )

        print(
            "→ 이 경우 A-8 parser 수정만으로는 복원이 불가능합니다."
        )

    print()
    print(
        "STEP 17-21-C-9-2-6A-8-DIAG 완료"
    )


if __name__ == "__main__":
    main()