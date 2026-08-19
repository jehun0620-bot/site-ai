import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup


STEP_NAME = (
    "STEP 17-21-C-9-2-6A-2 "
    "토지이음 도시군계획시설입체복합구역 Layer / 코드 탐색"
)

BASE_DIR = Path(__file__).resolve().parent.parent
LAW_DATA_DIR = BASE_DIR / "law_data"
OUTPUT_DIR = LAW_DATA_DIR / "output"

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR / "site_spatial_query_context.json"
)

PREVIOUS_PROBE_PATH = (
    OUTPUT_DIR / "seoul_vertical_mixed_use_zone_uq145_schema_probe.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR / "eum_vertical_mixed_use_zone_layer_probe.json"
)

EUM_MAP_URL = (
    "https://www.eum.go.kr/web/mp/mpMapDet.jsp"
)

TARGET_TERMS = [
    "도시군계획시설입체복합구역",
    "도시ㆍ군계획시설입체복합구역",
    "도시·군계획시설입체복합구역",
    "입체복합구역",
]


def print_separator(char: str = "=") -> None:
    print(char * 70)


def print_title(title: str) -> None:
    print()
    print_separator()
    print(f"=== {title} ===")
    print_separator()


def load_json(path: Path) -> Dict[str, Any]:

    if not path.exists():
        raise FileNotFoundError(
            f"파일 없음: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_json(
    path: Path,
    data: Dict[str, Any],
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


def recursive_find(
    obj: Any,
    keys: List[str],
) -> Optional[Any]:

    if isinstance(obj, dict):

        for key in keys:

            if key in obj:

                value = obj[key]

                if value not in (
                    None,
                    "",
                    [],
                    {},
                ):
                    return value

        for value in obj.values():

            found = recursive_find(
                value,
                keys,
            )

            if found not in (
                None,
                "",
                [],
                {},
            ):
                return found

    elif isinstance(obj, list):

        for item in obj:

            found = recursive_find(
                item,
                keys,
            )

            if found not in (
                None,
                "",
                [],
                {},
            ):
                return found

    return None


def extract_site(
    context: Dict[str, Any],
) -> Dict[str, Any]:

    return {
        "site_id": recursive_find(
            context,
            [
                "site_id",
                "SITE_ID",
            ],
        ),
        "address": recursive_find(
            context,
            [
                "address",
                "jibun_address",
                "site_address",
            ],
        ),
        "pnu": str(
            recursive_find(
                context,
                [
                    "pnu",
                    "PNU",
                ],
            )
            or ""
        ),
    }


def normalize_text(value: Any) -> str:

    if value is None:
        return ""

    return (
        str(value)
        .replace("\u00a0", " ")
        .strip()
    )


def fetch_page(
    pnu: str,
) -> Dict[str, Any]:

    result = {
        "http_status": None,
        "url": None,
        "html": "",
        "error": None,
    }

    try:

        response = requests.get(
            EUM_MAP_URL,
            params={
                "add": "land",
                "pnu": pnu,
            },
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/120 Safari/537.36"
                ),
                "Referer": "https://www.eum.go.kr/",
            },
            timeout=30,
        )

        result["http_status"] = (
            response.status_code
        )

        result["url"] = (
            response.url
        )

        result["html"] = (
            response.text
        )

    except Exception as exc:

        result["error"] = str(exc)

    return result


def find_target_contexts(
    html: str,
) -> List[Dict[str, Any]]:

    results = []

    compact = re.sub(
        r"\s+",
        " ",
        html,
    )

    for target in TARGET_TERMS:

        start = 0

        while True:

            index = compact.find(
                target,
                start,
            )

            if index < 0:
                break

            left = max(
                0,
                index - 500,
            )

            right = min(
                len(compact),
                index
                + len(target)
                + 500,
            )

            results.append(
                {
                    "target": target,
                    "context": compact[
                        left:right
                    ],
                }
            )

            start = (
                index
                + len(target)
            )

    return results


def inspect_elements(
    html: str,
) -> List[Dict[str, Any]]:

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    matches = []

    for tag in soup.find_all(True):

        text = normalize_text(
            tag.get_text(
                " ",
                strip=True,
            )
        )

        attrs_text = " ".join(
            f"{key}={value}"
            for key, value
            in tag.attrs.items()
        )

        combined = (
            text
            + " "
            + attrs_text
        )

        hit_terms = [
            term
            for term in TARGET_TERMS
            if term in combined
        ]

        if not hit_terms:
            continue

        matches.append(
            {
                "tag": tag.name,
                "text": text[:1000],
                "attrs": {
                    key: value
                    for key, value
                    in tag.attrs.items()
                },
                "hit_terms": hit_terms,
            }
        )

    return matches


def extract_identifier_candidates(
    html: str,
    contexts: List[Dict[str, Any]],
    elements: List[Dict[str, Any]],
) -> List[str]:

    candidates = set()

    source_texts = [
        html,
    ]

    source_texts.extend(
        item["context"]
        for item in contexts
    )

    for element in elements:

        source_texts.append(
            json.dumps(
                element,
                ensure_ascii=False,
            )
        )

    patterns = [
        r"\b[A-Z]{2,10}[A-Z0-9_\-]{2,30}\b",
        r"\bUQ[A-Z0-9]{2,10}\b",
        r"\b[A-Z]{2,5}[0-9]{3,8}\b",
        r"""(?:layer|layerId|code|cd|lyr|theme)["'=:\s]+([A-Za-z0-9_\-]+)""",
    ]

    for text in source_texts:

        for pattern in patterns:

            for match in re.findall(
                pattern,
                text,
                flags=re.I,
            ):

                if isinstance(
                    match,
                    tuple,
                ):
                    values = match
                else:
                    values = [match]

                for value in values:

                    value = normalize_text(
                        value
                    )

                    if not value:
                        continue

                    if len(value) > 50:
                        continue

                    candidates.add(
                        value
                    )

    return sorted(
        candidates
    )


def inspect_scripts(
    html: str,
) -> List[str]:

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    scripts = []

    for tag in soup.find_all(
        "script"
    ):

        src = tag.get(
            "src"
        )

        if src:
            scripts.append(src)

    return scripts


def main() -> int:

    print(
        f"=== {STEP_NAME} ==="
    )

    context = load_json(
        QUERY_CONTEXT_PATH
    )

    previous = None

    if PREVIOUS_PROBE_PATH.exists():

        previous = load_json(
            PREVIOUS_PROBE_PATH
        )

    site = extract_site(
        context
    )

    print_title(
        "대상 SITE"
    )

    print(
        "SITE ID:",
        site.get("site_id")
        or "-",
    )

    print(
        "주소:",
        site.get("address")
        or "-",
    )

    print(
        "PNU:",
        site.get("pnu")
        or "-",
    )

    pnu = site.get("pnu")

    if (
        not pnu
        or len(pnu) != 19
        or not pnu.isdigit()
    ):

        raise RuntimeError(
            "PNU가 19자리가 아닙니다."
        )

    print_title(
        "1. 토지이음 지도 조회"
    )

    page = fetch_page(
        pnu
    )

    print(
        "HTTP:",
        page[
            "http_status"
        ],
    )

    print(
        "URL:",
        page[
            "url"
        ],
    )

    if page.get(
        "error"
    ):

        print(
            "error:",
            page["error"],
        )

    html = page.get(
        "html",
        "",
    )

    print(
        "HTML bytes:",
        len(
            html.encode(
                "utf-8",
                errors="ignore",
            )
        ),
    )

    print_title(
        "2. 입체복합구역 명칭 확인"
    )

    contexts = find_target_contexts(
        html
    )

    print(
        "keyword context 수:",
        len(contexts),
    )

    for index, item in enumerate(
        contexts[:20],
        start=1,
    ):

        print()
        print_separator("-")

        print(
            f"Context {index}"
        )

        print(
            "target:",
            item["target"],
        )

        print(
            item["context"]
        )

    print_title(
        "3. HTML element / attribute 분석"
    )

    elements = inspect_elements(
        html
    )

    print(
        "target element 수:",
        len(elements),
    )

    for index, item in enumerate(
        elements[:30],
        start=1,
    ):

        print()
        print_separator("-")

        print(
            f"Element {index}"
        )

        print(
            "tag:",
            item["tag"],
        )

        print(
            "text:",
            item["text"],
        )

        print(
            "attrs:",
            item["attrs"],
        )

        print(
            "hits:",
            item[
                "hit_terms"
            ],
        )

    print_title(
        "4. 식별자 후보 추출"
    )

    candidates = (
        extract_identifier_candidates(
            html,
            contexts,
            elements,
        )
    )

    print(
        "후보 수:",
        len(candidates),
    )

    for value in candidates[:200]:

        print(
            f"- {value}"
        )

    print_title(
        "5. 외부 JS 목록"
    )

    scripts = inspect_scripts(
        html
    )

    print(
        "script 수:",
        len(scripts),
    )

    for script in scripts:

        print(
            f"- {script}"
        )

    target_present = (
        len(contexts) > 0
    )

    code_verified = False
    verified_code = None

    # 현 단계에서는 단순 regex 후보를
    # 공식 코드로 자동 확정하지 않음.
    #
    # 명칭과 동일 element/attribute에
    # 명시적으로 연결된 구조가 다음 단계에서
    # 확인되어야 함.

    print_title(
        "6. 입체복합구역 Layer 판정"
    )

    if target_present:

        source_status = (
            "TERM_PRESENT_CODE_UNRESOLVED"
        )

        reason = (
            "토지이음 지도 HTML에서 "
            "도시군계획시설입체복합구역 "
            "명칭을 확인했으나 "
            "현재 단계에서는 명칭과 직접 연결된 "
            "공식 layer/code 식별자를 "
            "확정하지 않음"
        )

    else:

        source_status = (
            "TERM_NOT_EXTRACTED"
        )

        reason = (
            "토지이음 지도 요청은 수행했으나 "
            "현재 반환 HTML에서 "
            "도시군계획시설입체복합구역 "
            "문자열을 직접 추출하지 못함. "
            "동적 JavaScript 로딩 가능성이 있으므로 "
            "source 부재로 간주하지 않음"
        )

    print(
        "source_status:",
        source_status,
    )

    print(
        "term present:",
        target_present,
    )

    print(
        "verified code:",
        verified_code
        or "미확정",
    )

    print(
        "reason:",
        reason,
    )

    print_title(
        "7. 현재 입체복합구역 SITE 판정"
    )

    resolution = {
        "query_status":
            "NOT_CONNECTED",

        "resolution":
            "UNKNOWN",

        "confidence":
            "NONE",

        "reason": (
            "입체복합구역의 공식 명칭/레이어 "
            "관리체계를 탐색 중이며 "
            "대상 필지에 대한 geometry "
            "공간교차를 수행하지 않았으므로 "
            "TRUE/FALSE 판정을 하지 않음"
        ),
    }

    print(
        "query_status:",
        resolution[
            "query_status"
        ],
    )

    print(
        "resolution:",
        resolution[
            "resolution"
        ],
    )

    print(
        "confidence:",
        resolution[
            "confidence"
        ],
    )

    print(
        "reason:",
        resolution[
            "reason"
        ],
    )

    print_title(
        "C-9-2-6A-2 검증"
    )

    checks = {
        "SITE 주소 존재":
            bool(
                site.get(
                    "address"
                )
            ),

        "PNU 19자리":
            bool(
                pnu
                and len(pnu) == 19
                and pnu.isdigit()
            ),

        "토지이음 지도 조회 실행":
            page[
                "http_status"
            ]
            is not None,

        "HTTP 200":
            page[
                "http_status"
            ]
            == 200,

        "코드 후보 자동확정 없음":
            code_verified
            is False,

        "geometry 미확정 TRUE 금지":
            resolution[
                "resolution"
            ]
            != "TRUE",

        "geometry 미확정 FALSE 금지":
            resolution[
                "resolution"
            ]
            != "FALSE",

        "SITE UNKNOWN 유지":
            resolution[
                "resolution"
            ]
            == "UNKNOWN",
    }

    all_pass = True

    for name, passed in (
        checks.items()
    ):

        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(
            f"{name}: {status}"
        )

        if not passed:
            all_pass = False

    output = {
        "step": STEP_NAME,
        "site": site,
        "previous_probe_loaded":
            previous is not None,

        "eum": {
            "url": page[
                "url"
            ],
            "http_status": page[
                "http_status"
            ],
            "target_present":
                target_present,
            "contexts":
                contexts,
            "elements":
                elements,
            "identifier_candidates":
                candidates,
            "scripts":
                scripts,
        },

        "source": {
            "source_status":
                source_status,
            "verified_code":
                verified_code,
            "reason":
                reason,
        },

        "site_resolution":
            resolution,

        "checks":
            checks,

        "all_pass":
            all_pass,
    }

    save_json(
        OUTPUT_PATH,
        output,
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
            "STEP 17-21-C-9-2-6A-2 완료"
        )

        print()

        if target_present:

            print(
                "토지이음에서 "
                "도시군계획시설입체복합구역 "
                "명칭을 확인했습니다."
            )

            print()

            print(
                "다음 단계:"
            )

            print(
                "STEP 17-21-C-9-2-6A-3"
            )

            print(
                "→ 해당 명칭이 포함된 HTML/JS의 "
                "실제 layer parameter 추적"
            )

            print(
                "→ 네트워크 요청 endpoint / "
                "관리코드 식별"
            )

            print(
                "→ geometry source 연결 가능성 검증"
            )

        else:

            print(
                "정적 HTML에서 명칭을 "
                "추출하지 못했습니다."
            )

            print()

            print(
                "다음 단계:"
            )

            print(
                "→ 외부 JavaScript 파일 분석"
            )

            print(
                "→ 동적 지도 layer 설정 탐색"
            )

        return 0

    print(
        "STEP 17-21-C-9-2-6A-2 "
        "검증 미완료"
    )

    return 1


if __name__ == "__main__":
    sys.exit(
        main()
    )