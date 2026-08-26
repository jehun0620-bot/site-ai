# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-M
Development Density Management Area
Gazette Recovered Attachment Source Verification

목표
======================================================================
L-stage에서 attachment identity와 실제 payload의 결합이 검증된
PDF/HWP/HWPX 공보 attachment만 다시 HTTP 조회하여
document-local evidence만으로 개발밀도관리구역 고시 여부를 검증한다.

입력:
    law_data/output/
    development_density_management_area_
    gazette_attachment_download_endpoint_recovery.json

출력:
    law_data/output/
    development_density_management_area_
    gazette_recovered_attachment_source_verification.json

대상:
    개발밀도관리구역

표준 코드:
    UQQ700

핵심 원칙
======================================================================
1. L-stage의 next_stage_verification_pool만 입력으로 사용한다.

2. 다음 parent/L-stage evidence는 positive 판정에 상속하지 않는다.
    - parent region
    - child label
    - expected filename
    - parent title
    - attachment source
    - L-stage resolution

3. positive evidence는 다운로드한 원문 자체에서만 추출한다.

4. PDF/HWP/HWPX를 지원한다.

5. target exact phrase:
       개발밀도관리구역
   가 원문에 반드시 존재해야 한다.

6. 지정/변경/해제/결정 action context가 target 인접 문맥에
   반드시 존재해야 한다.

7. 고시번호가 원문에 반드시 존재해야 한다.

8. official context가 반드시 존재해야 한다.

9. 행정구역 문맥이 반드시 존재해야 한다.

10. scope는 추출하되 verified positive 필수조건은 아니다.

11. 공보 전체가 target을 포함하더라도
    nearest notice context를 별도로 추출한다.

12. 행정업무표·사무전결표 false positive를 차단한다.

13. 법령·조례의 단순 target 언급을 차단한다.

14. runtime registration은 계속 차단한다.

15. SITE TRUE/FALSE 자동 판정도 계속 차단한다.
"""

from __future__ import annotations

import html
import io
import json
import re
import subprocess
import tempfile
import zipfile

from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlparse,
    urlunparse,
)

import requests


# ============================================================
# OPTIONAL PDF PARSER
# ============================================================

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


# ============================================================
# PATH
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "gazette_attachment_download_endpoint_recovery.json"
    )
)

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "gazette_recovered_attachment_source_verification.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"


# ============================================================
# INPUT RESOLUTION
# ============================================================

L_STAGE_REQUIRED_RESOLUTION = (
    "GAZETTE_ATTACHMENT_DOWNLOAD_ENDPOINT_RECOVERED"
)


# ============================================================
# RECORD RESOLUTIONS
# ============================================================

RESOLUTION_VERIFIED = (
    "GAZETTE_RECOVERED_ATTACHMENT_VERIFIED_TARGET_DOCUMENT"
)

RESOLUTION_TARGET_MENTION = (
    "GAZETTE_RECOVERED_ATTACHMENT_TARGET_MENTION_ONLY"
)

RESOLUTION_ADMIN_DUTY = (
    "GAZETTE_RECOVERED_ATTACHMENT_ADMINISTRATIVE_DUTY_REFERENCE"
)

RESOLUTION_LEGAL_REFERENCE = (
    "GAZETTE_RECOVERED_ATTACHMENT_LEGAL_REFERENCE_ONLY"
)

RESOLUTION_UNRELATED = (
    "GAZETTE_RECOVERED_ATTACHMENT_UNRELATED_DOCUMENT"
)

RESOLUTION_DOWNLOAD_FAILED = (
    "GAZETTE_RECOVERED_ATTACHMENT_DOWNLOAD_FAILED"
)

RESOLUTION_PARSE_FAILED = (
    "GAZETTE_RECOVERED_ATTACHMENT_PARSE_FAILED"
)

RESOLUTION_IDENTITY_MISMATCH = (
    "GAZETTE_RECOVERED_ATTACHMENT_IDENTITY_MISMATCH"
)


VALID_RESOLUTIONS = {
    RESOLUTION_VERIFIED,
    RESOLUTION_TARGET_MENTION,
    RESOLUTION_ADMIN_DUTY,
    RESOLUTION_LEGAL_REFERENCE,
    RESOLUTION_UNRELATED,
    RESOLUTION_DOWNLOAD_FAILED,
    RESOLUTION_PARSE_FAILED,
    RESOLUTION_IDENTITY_MISMATCH,
}


# ============================================================
# HTTP
# ============================================================

TIMEOUT = 30

MAX_RESPONSE_BYTES = (
    40
    * 1024
    * 1024
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


# ============================================================
# ACTION
# ============================================================

ACTION_PATTERNS = {
    "DESIGNATION": [
        r"개발밀도관리구역.{0,180}?지정",
        r"개발밀도관리구역을.{0,180}?지정",
        r"개발밀도관리구역으로.{0,180}?지정",
        r"지정.{0,180}?개발밀도관리구역",
    ],

    "CHANGE": [
        r"개발밀도관리구역.{0,180}?변경",
        r"개발밀도관리구역.{0,180}?변경결정",
        r"개발밀도관리구역.{0,180}?결정\s*\(\s*변경\s*\)",
        r"변경.{0,180}?개발밀도관리구역",
    ],

    "RELEASE": [
        r"개발밀도관리구역.{0,180}?해제",
        r"개발밀도관리구역.{0,180}?해지",
        r"해제.{0,180}?개발밀도관리구역",
    ],

    "DECISION": [
        r"개발밀도관리구역.{0,180}?결정",
        r"결정.{0,180}?개발밀도관리구역",
    ],
}


# ============================================================
# OFFICIAL CONTEXT
# ============================================================

OFFICIAL_CONTEXT_PATTERNS = [
    r"고\s*시",
    r"고시문",
    r"고시번호",
    r"도시관리계획",
    r"도시계획",
    r"지형도면",
    r"국토의\s*계획\s*및\s*이용에\s*관한\s*법률",
    r"국토계획법",
    r"시장",
    r"군수",
    r"구청장",
    r"특별시장",
    r"광역시장",
    r"도지사",
]


# ============================================================
# NOTICE
# ============================================================

NOTICE_PATTERNS = [
    re.compile(
        r"(?P<notice>"
        r"(?:서울특별시|부산광역시|대구광역시|인천광역시|"
        r"광주광역시|대전광역시|울산광역시|세종특별자치시|"
        r"경기도|강원특별자치도|강원도|충청북도|충청남도|"
        r"전북특별자치도|전라북도|전라남도|경상북도|경상남도|"
        r"제주특별자치도|"
        r"[가-힣]{2,12}시|[가-힣]{2,12}군|[가-힣]{2,12}구)"
        r"\s*(?:고시|공고)\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호)"
    ),

    re.compile(
        r"(?P<notice>"
        r"(?:고시|공고)\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호)"
    ),
]


# ============================================================
# DATE
# ============================================================

DATE_PATTERN = re.compile(
    r"(?P<year>19\d{2}|20\d{2})"
    r"\s*[.\-/년]\s*"
    r"(?P<month>0?[1-9]|1[0-2])"
    r"\s*[.\-/월]\s*"
    r"(?P<day>0?[1-9]|[12]\d|3[01])"
    r"\s*일?"
)


# ============================================================
# REGION
# ============================================================

REGION_NAMES = [
    "서울특별시",
    "부산광역시",
    "대구광역시",
    "인천광역시",
    "광주광역시",
    "대전광역시",
    "울산광역시",
    "세종특별자치시",
    "경기도",
    "강원특별자치도",
    "강원도",
    "충청북도",
    "충청남도",
    "전북특별자치도",
    "전라북도",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주특별자치도",
]


# ============================================================
# FALSE POSITIVE GUARDS
# ============================================================

ADMINISTRATIVE_DUTY_TERMS = [
    "단위사무명",
    "단 위 사 무 명",
    "전결권자",
    "전 결 권 자",
    "사무전결",
    "업무분장",
    "위임전결",
    "전결규정",
    "담 당 자",
    "팀 장",
    "국 장",
    "부 시 장",
    "관 · 과 · 단 장",
]

LEGAL_REFERENCE_PATTERNS = [
    r"법\s*제\s*\d+\s*조",
    r"법률\s*제\s*\d+\s*호",
    r"시행령\s*제\s*\d+\s*조",
    r"조례\s*제\s*\d+\s*조",
    r"용어의\s*뜻",
    r"정의는\s*다음과",
    r"다음\s*각\s*호",
]


# ============================================================
# SCOPE
# ============================================================

SCOPE_PATTERNS = [
    r"[가-힣]{1,15}(?:동|읍|면|리)\s+\d+(?:-\d+)?\s*번지",
    r"[가-힣]{1,15}(?:동|읍|면|리)\s+일원",
    r"\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:㎡|m²|m2)",
    r"면적\s*[:：]?\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?",
    r"위치\s*[:：]",
    r"구역\s*면적",
    r"지정\s*면적",
]


# ============================================================
# UTIL
# ============================================================

def normalize_space(
    value: Any,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        str(
            value
            or ""
        ),
    ).strip()


def unique_strings(
    values: Iterable[Any],
) -> List[str]:

    result: List[str] = []
    seen: Set[str] = set()

    for value in values:

        text = normalize_space(
            value
        )

        if not text:
            continue

        if text in seen:
            continue

        seen.add(
            text
        )

        result.append(
            text
        )

    return result


# ============================================================
# URL CANONICALIZATION
# ============================================================

VOLATILE_QUERY_KEYS = {
    "token",
    "_csrf",
    "csrf",
    "csrftoken",
    "sessionid",
    "jsessionid",
    "_",
    "timestamp",
    "rand",
    "random",
    "cachebuster",
    "cache_buster",
    "cb",
    "ts",
}

TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
}


def canonicalize_url(
    url: str,
) -> str:

    value = html.unescape(
        normalize_space(
            url
        )
    )

    if not value:
        return ""

    try:

        parsed = urlparse(
            value
        )

    except Exception:

        return value

    if not parsed.hostname:
        return value

    query_items = []

    for key, query_value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        lowered = (
            key.lower()
        )

        if lowered in VOLATILE_QUERY_KEYS:
            continue

        if lowered in TRACKING_QUERY_KEYS:
            continue

        if "csrf" in lowered:
            continue

        if "session" in lowered:
            continue

        query_items.append(
            (
                key,
                query_value,
            )
        )

    query_items.sort(
        key=lambda item: (
            item[0].lower(),
            item[1],
        )
    )

    return urlunparse(
        (
            (
                parsed.scheme
                or "https"
            ).lower(),

            (
                parsed.netloc
            ).lower(),

            parsed.path
            or "/",

            "",

            urlencode(
                query_items,
                doseq=True,
            ),

            "",
        )
    )


# ============================================================
# LOAD L-STAGE POOL
# ============================================================

def load_verification_pool(
    data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    raw = data.get(
        "next_stage_verification_pool"
    )

    if not isinstance(
        raw,
        list,
    ):

        raw = []

    result: List[
        Dict[str, Any]
    ] = []

    seen: Set[
        Tuple[
            str,
            str,
        ]
    ] = set()

    for item in raw:

        if not isinstance(
            item,
            dict,
        ):
            continue

        if item.get(
            "recovered"
        ) is not True:
            continue

        if normalize_space(
            item.get(
                "resolution"
            )
        ) != L_STAGE_REQUIRED_RESOLUTION:
            continue

        best_probe = (
            item.get(
                "best_probe"
            )
            or {}
        )

        if not isinstance(
            best_probe,
            dict,
        ):
            continue

        url = canonicalize_url(
            best_probe.get(
                "final_url"
            )
            or best_probe.get(
                "requested_url"
            )
            or ""
        )

        if not url:
            continue

        identity = (
            item.get(
                "attachment_identity"
            )
            or {}
        )

        atch_file_id = normalize_space(
            identity.get(
                "atchFileId"
            )
        )

        file_sn = normalize_space(
            identity.get(
                "fileSn"
            )
            or "0"
        )

        if not atch_file_id:
            continue

        key = (
            atch_file_id,
            file_sn,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            {
                "parent_region": normalize_space(
                    item.get(
                        "parent_region"
                    )
                ),

                "parent_url": canonicalize_url(
                    item.get(
                        "parent_url"
                    )
                    or ""
                ),

                "child_label": normalize_space(
                    item.get(
                        "child_label"
                    )
                ),

                "attachment_identity": {
                    "atchFileId": atch_file_id,
                    "fileSn": file_sn,
                },

                "document_url": url,

                "expected_sha256": normalize_space(
                    best_probe.get(
                        "response_sha256"
                    )
                ),

                "expected_filename": normalize_space(
                    best_probe.get(
                        "response_filename"
                    )
                    or best_probe.get(
                        "expected_filename"
                    )
                ),

                "expected_document_type": normalize_space(
                    best_probe.get(
                        "document_type"
                    )
                ),
            }
        )

    return result


# ============================================================
# FETCH
# ============================================================

def fetch_bytes(
    session: requests.Session,
    *,
    url: str,
    referer: str = "",
) -> Dict[str, Any]:

    result = {
        "requested_url": url,
        "final_url": "",
        "http_status": None,
        "content_type": "",
        "content_disposition": "",
        "response_bytes": 0,
        "data": b"",
        "error": "",
    }

    headers = {}

    if referer:

        headers[
            "Referer"
        ] = referer

    try:

        with session.get(
            url,
            headers=headers,
            timeout=TIMEOUT,
            allow_redirects=True,
            stream=True,
        ) as response:

            result[
                "http_status"
            ] = response.status_code

            result[
                "final_url"
            ] = canonicalize_url(
                str(
                    response.url
                )
            )

            result[
                "content_type"
            ] = normalize_space(
                response.headers.get(
                    "Content-Type"
                )
            )

            result[
                "content_disposition"
            ] = normalize_space(
                response.headers.get(
                    "Content-Disposition"
                )
            )

            response.raise_for_status()

            chunks: List[bytes] = []
            total = 0

            for chunk in response.iter_content(
                chunk_size=256 * 1024,
            ):

                if not chunk:
                    continue

                total += len(
                    chunk
                )

                if total > MAX_RESPONSE_BYTES:

                    raise ValueError(
                        "response exceeds "
                        f"{MAX_RESPONSE_BYTES} bytes"
                    )

                chunks.append(
                    chunk
                )

            payload = b"".join(
                chunks
            )

            result[
                "data"
            ] = payload

            result[
                "response_bytes"
            ] = len(
                payload
            )

    except Exception as exc:

        result[
            "error"
        ] = repr(
            exc
        )

    return result


# ============================================================
# HASH
# ============================================================

def sha256_bytes(
    data: bytes,
) -> str:

    import hashlib

    return hashlib.sha256(
        data
    ).hexdigest()


# ============================================================
# DOCUMENT TYPE
# ============================================================

def detect_document_type(
    data: bytes,
) -> str:

    if data.startswith(
        b"%PDF"
    ):

        return "PDF"

    if data.startswith(
        b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"
    ):

        return "HWP"

    if data.startswith(
        b"PK\x03\x04"
    ):

        try:

            with zipfile.ZipFile(
                io.BytesIO(
                    data
                )
            ) as archive:

                names = [
                    name.lower()
                    for name
                    in archive.namelist()
                ]

                if any(
                    name.startswith(
                        "contents/"
                    )
                    for name in names
                ):

                    return "HWPX"

        except Exception:
            pass

    return "UNKNOWN"


# ============================================================
# PARSERS
# ============================================================

def parse_pdf_text(
    data: bytes,
) -> Tuple[
    str,
    str,
    str,
]:

    if PdfReader is None:

        return (
            "",
            "",
            "pypdf is not available",
        )

    try:

        reader = PdfReader(
            io.BytesIO(
                data
            )
        )

        pages: List[str] = []

        for page in reader.pages:

            text = (
                page.extract_text()
                or ""
            )

            if text:

                pages.append(
                    text
                )

        return (
            normalize_space(
                "\n".join(
                    pages
                )
            ),

            "pypdf",

            "",
        )

    except Exception as exc:

        return (
            "",
            "pypdf",
            repr(
                exc
            ),
        )


def parse_hwpx_text(
    data: bytes,
) -> Tuple[
    str,
    str,
    str,
]:

    try:

        texts: List[str] = []

        with zipfile.ZipFile(
            io.BytesIO(
                data
            )
        ) as archive:

            names = sorted(
                archive.namelist()
            )

            xml_names = [
                name
                for name in names
                if (
                    name.lower().startswith(
                        "contents/"
                    )
                    and name.lower().endswith(
                        ".xml"
                    )
                )
            ]

            for name in xml_names:

                raw = archive.read(
                    name
                )

                xml_text = raw.decode(
                    "utf-8",
                    errors="replace",
                )

                plain = re.sub(
                    r"<[^>]+>",
                    " ",
                    xml_text,
                )

                plain = html.unescape(
                    plain
                )

                if plain:

                    texts.append(
                        plain
                    )

        return (
            normalize_space(
                "\n".join(
                    texts
                )
            ),

            "hwpx-zip-xml",

            "",
        )

    except Exception as exc:

        return (
            "",
            "hwpx-zip-xml",
            repr(
                exc
            ),
        )


def parse_hwp_text(
    data: bytes,
) -> Tuple[
    str,
    str,
    str,
]:

    temp_path: Optional[
        Path
    ] = None

    try:

        with tempfile.NamedTemporaryFile(
            suffix=".hwp",
            delete=False,
        ) as temp_file:

            temp_file.write(
                data
            )

            temp_path = Path(
                temp_file.name
            )

        process = subprocess.run(
            [
                "hwp5txt",
                str(
                    temp_path
                ),
            ],
            capture_output=True,
            timeout=30,
        )

        if process.returncode != 0:

            return (
                "",
                "hwp5txt",
                normalize_space(
                    process.stderr.decode(
                        "utf-8",
                        errors="replace",
                    )
                ),
            )

        return (
            normalize_space(
                process.stdout.decode(
                    "utf-8",
                    errors="replace",
                )
            ),

            "hwp5txt",

            "",
        )

    except FileNotFoundError:

        return (
            "",
            "hwp5txt",
            "hwp5txt executable not found",
        )

    except Exception as exc:

        return (
            "",
            "hwp5txt",
            repr(
                exc
            ),
        )

    finally:

        if (
            temp_path
            and temp_path.exists()
        ):

            try:

                temp_path.unlink()

            except Exception:
                pass


def parse_document(
    document_type: str,
    data: bytes,
) -> Dict[str, Any]:

    if document_type == "PDF":

        text, parser, error = (
            parse_pdf_text(
                data
            )
        )

    elif document_type == "HWP":

        text, parser, error = (
            parse_hwp_text(
                data
            )
        )

    elif document_type == "HWPX":

        text, parser, error = (
            parse_hwpx_text(
                data
            )
        )

    else:

        text = ""
        parser = ""
        error = (
            "Unsupported document type"
        )

    return {
        "text": text,
        "parser": parser,
        "error": error,
    }


# ============================================================
# TARGET CONTEXT
# ============================================================

def extract_target_contexts(
    text: str,
    radius: int = 1200,
) -> List[str]:

    result: List[str] = []

    start = 0

    while True:

        index = text.find(
            TARGET_NAME,
            start,
        )

        if index < 0:
            break

        left = max(
            0,
            index - radius,
        )

        right = min(
            len(
                text
            ),
            index
            + len(
                TARGET_NAME
            )
            + radius,
        )

        result.append(
            text[
                left:right
            ]
        )

        start = (
            index
            + len(
                TARGET_NAME
            )
        )

    return unique_strings(
        result
    )


# ============================================================
# ACTION
# ============================================================

def extract_action_context(
    text: str,
) -> Tuple[
    List[str],
    List[str],
]:

    corpus = "\n".join(
        extract_target_contexts(
            text,
            radius=1500,
        )
    )

    action_types: List[str] = []
    evidence: List[str] = []

    for action_type, patterns in ACTION_PATTERNS.items():

        for pattern in patterns:

            match = re.search(
                pattern,
                corpus,
                flags=(
                    re.IGNORECASE
                    | re.DOTALL
                ),
            )

            if not match:
                continue

            action_types.append(
                action_type
            )

            evidence.append(
                normalize_space(
                    match.group(0)
                )
            )

    return (
        unique_strings(
            action_types
        ),
        unique_strings(
            evidence
        ),
    )


# ============================================================
# NOTICE
# ============================================================

def extract_notice_numbers(
    text: str,
) -> List[str]:

    values: List[str] = []

    for pattern in NOTICE_PATTERNS:

        for match in pattern.finditer(
            text
        ):

            values.append(
                normalize_space(
                    match.groupdict().get(
                        "notice"
                    )
                    or match.group(0)
                )
            )

    return unique_strings(
        values
    )


def extract_nearest_notice_numbers(
    text: str,
) -> List[str]:

    """
    전체 공보에는 여러 고시번호가 존재할 수 있으므로
    target 주변 ±2500자 범위의 번호를 별도 추출한다.
    """

    result: List[str] = []

    contexts = extract_target_contexts(
        text,
        radius=2500,
    )

    for context in contexts:

        result.extend(
            extract_notice_numbers(
                context
            )
        )

    return unique_strings(
        result
    )


# ============================================================
# DATE
# ============================================================

def extract_dates(
    text: str,
) -> List[str]:

    result: List[str] = []

    for match in DATE_PATTERN.finditer(
        text
    ):

        year = int(
            match.group(
                "year"
            )
        )

        month = int(
            match.group(
                "month"
            )
        )

        day = int(
            match.group(
                "day"
            )
        )

        result.append(
            f"{year:04d}-"
            f"{month:02d}-"
            f"{day:02d}"
        )

    return unique_strings(
        result
    )


def extract_nearest_dates(
    text: str,
) -> List[str]:

    result: List[str] = []

    for context in extract_target_contexts(
        text,
        radius=2500,
    ):

        result.extend(
            extract_dates(
                context
            )
        )

    return unique_strings(
        result
    )


# ============================================================
# REGIONS
# ============================================================

def extract_regions(
    text: str,
) -> List[str]:

    result: List[str] = []

    for region in REGION_NAMES:

        if region in text:

            result.append(
                region
            )

    local_patterns = [
        r"([가-힣]{2,12}시)\s*(?:고시|공고|시장)",
        r"([가-힣]{2,12}군)\s*(?:고시|공고|군수)",
        r"([가-힣]{2,12}구)\s*(?:고시|공고|구청장)",
    ]

    for pattern in local_patterns:

        for match in re.finditer(
            pattern,
            text,
        ):

            result.append(
                match.group(
                    1
                )
            )

    return unique_strings(
        result
    )


# ============================================================
# OFFICIAL CONTEXT
# ============================================================

def extract_official_context(
    text: str,
) -> List[str]:

    corpus = "\n".join(
        extract_target_contexts(
            text,
            radius=2000,
        )
    )

    result: List[str] = []

    for pattern in OFFICIAL_CONTEXT_PATTERNS:

        match = re.search(
            pattern,
            corpus,
            flags=re.IGNORECASE,
        )

        if match:

            result.append(
                normalize_space(
                    match.group(0)
                )
            )

    return unique_strings(
        result
    )


# ============================================================
# ADMIN DUTY
# ============================================================

def detect_administrative_duty_reference(
    text: str,
) -> Tuple[
    bool,
    List[str],
]:

    normalized = normalize_space(
        text
    )

    evidence: List[str] = []

    for term in ADMINISTRATIVE_DUTY_TERMS:

        if term in normalized:

            evidence.append(
                term
            )

    draft_count = len(
        re.findall(
            r"기안\s*[○●◎]?",
            normalized,
        )
    )

    strong_structure = (
        (
            "단위사무명"
            in normalized
            or "단 위 사 무 명"
            in normalized
        )
        and (
            "전결권자"
            in normalized
            or "전 결 권 자"
            in normalized
        )
    )

    target_draft = re.search(
        r"개발밀도관리구역.{0,100}?기안",
        normalized,
        flags=re.DOTALL,
    )

    detected = (
        strong_structure
        or (
            target_draft
            is not None
            and draft_count >= 5
        )
    )

    return (
        detected,
        unique_strings(
            evidence
        ),
    )


# ============================================================
# LEGAL REFERENCE
# ============================================================

def detect_legal_reference_only(
    text: str,
    *,
    action_types: List[str],
    nearest_notice_numbers: List[str],
    official_context: List[str],
) -> Tuple[
    bool,
    List[str],
]:

    corpus = "\n".join(
        extract_target_contexts(
            text,
            radius=1200,
        )
    )

    evidence: List[str] = []

    for pattern in LEGAL_REFERENCE_PATTERNS:

        match = re.search(
            pattern,
            corpus,
            flags=re.IGNORECASE,
        )

        if match:

            evidence.append(
                normalize_space(
                    match.group(0)
                )
            )

    substantial_notice_context = (
        bool(
            action_types
        )
        and bool(
            nearest_notice_numbers
        )
        and bool(
            official_context
        )
    )

    return (
        bool(
            evidence
        )
        and not substantial_notice_context,

        unique_strings(
            evidence
        ),
    )


# ============================================================
# SCOPE
# ============================================================

def extract_scope_evidence(
    text: str,
) -> List[str]:

    corpus = "\n".join(
        extract_target_contexts(
            text,
            radius=3500,
        )
    )

    result: List[str] = []

    for pattern in SCOPE_PATTERNS:

        for match in re.finditer(
            pattern,
            corpus,
            flags=re.IGNORECASE,
        ):

            result.append(
                normalize_space(
                    match.group(0)
                )
            )

    return unique_strings(
        result
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print(
        "=" * 60
    )

    print(
        "DEVELOPMENT DENSITY MANAGEMENT AREA"
    )

    print(
        "GAZETTE RECOVERED ATTACHMENT SOURCE VERIFICATION"
    )

    print(
        "=" * 60
    )

    print()

    print(
        "Target:",
        TARGET_NAME,
    )

    print(
        "Standard code:",
        STANDARD_CODE,
    )

    print(
        "Input:",
        INPUT_PATH,
    )

    print()

    if not INPUT_PATH.exists():

        raise FileNotFoundError(
            f"L-stage output not found: {INPUT_PATH}"
        )

    input_data = json.loads(
        INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    verification_pool = (
        load_verification_pool(
            input_data
        )
    )

    print(
        "Recovered attachment verification count:",
        len(
            verification_pool
        ),
    )

    print()

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": USER_AGENT,

            "Accept": (
                "application/pdf,"
                "application/octet-stream,"
                "*/*;q=0.8"
            ),

            "Accept-Language": (
                "ko-KR,ko;q=0.9,"
                "en-US;q=0.7,en;q=0.5"
            ),
        }
    )

    request_count = 0
    http_success_count = 0
    download_failed_count = 0
    parse_failed_count = 0
    identity_mismatch_count = 0

    records: List[
        Dict[str, Any]
    ] = []

    for index, item in enumerate(
        verification_pool,
        start=1,
    ):

        print(
            "-" * 60
        )

        print(
            f"DOCUMENT {index}"
        )

        print(
            "Identity:",
            item[
                "attachment_identity"
            ],
        )

        print(
            "URL:",
            item[
                "document_url"
            ],
        )

        request_count += 1

        fetched = fetch_bytes(
            session,
            url=item[
                "document_url"
            ],
            referer=item[
                "parent_url"
            ],
        )

        if fetched.get(
            "http_status"
        ) == 200:

            http_success_count += 1

        if fetched.get(
            "error"
        ):

            download_failed_count += 1

            record = {
                **item,

                "http_status": fetched.get(
                    "http_status"
                ),

                "verified_positive": False,

                "resolution": (
                    RESOLUTION_DOWNLOAD_FAILED
                ),

                "error": fetched.get(
                    "error"
                ),

                "parent_region_evidence_inherited": False,

                "parent_label_evidence_inherited": False,

                "final_positive": False,
            }

            records.append(
                record
            )

            print(
                "Resolution:",
                RESOLUTION_DOWNLOAD_FAILED,
            )

            continue

        payload = (
            fetched.get(
                "data"
            )
            or b""
        )

        actual_sha256 = (
            sha256_bytes(
                payload
            )
        )

        expected_sha256 = item.get(
            "expected_sha256"
        )

        identity_match = (
            not expected_sha256
            or actual_sha256
            == expected_sha256
        )

        if not identity_match:

            identity_mismatch_count += 1

            record = {
                **item,

                "http_status": fetched.get(
                    "http_status"
                ),

                "actual_sha256": actual_sha256,

                "verified_positive": False,

                "resolution": (
                    RESOLUTION_IDENTITY_MISMATCH
                ),

                "parent_region_evidence_inherited": False,

                "parent_label_evidence_inherited": False,

                "final_positive": False,
            }

            records.append(
                record
            )

            print(
                "Resolution:",
                RESOLUTION_IDENTITY_MISMATCH,
            )

            continue

        document_type = (
            detect_document_type(
                payload
            )
        )

        parsed = parse_document(
            document_type,
            payload,
        )

        text = normalize_space(
            parsed.get(
                "text"
            )
        )

        if (
            parsed.get(
                "error"
            )
            and not text
        ):

            parse_failed_count += 1

            record = {
                **item,

                "http_status": fetched.get(
                    "http_status"
                ),

                "actual_sha256": actual_sha256,

                "document_type": document_type,

                "parser": parsed.get(
                    "parser"
                ),

                "parse_error": parsed.get(
                    "error"
                ),

                "verified_positive": False,

                "resolution": (
                    RESOLUTION_PARSE_FAILED
                ),

                "parent_region_evidence_inherited": False,

                "parent_label_evidence_inherited": False,

                "final_positive": False,
            }

            records.append(
                record
            )

            print(
                "Document type:",
                document_type,
            )

            print(
                "Resolution:",
                RESOLUTION_PARSE_FAILED,
            )

            continue

        target_found = (
            TARGET_NAME
            in text
        )

        (
            action_types,
            action_evidence,
        ) = extract_action_context(
            text
        )

        all_notice_numbers = (
            extract_notice_numbers(
                text
            )
        )

        nearest_notice_numbers = (
            extract_nearest_notice_numbers(
                text
            )
        )

        all_dates = extract_dates(
            text
        )

        nearest_dates = (
            extract_nearest_dates(
                text
            )
        )

        administrative_regions = (
            extract_regions(
                text
            )
        )

        official_context = (
            extract_official_context(
                text
            )
        )

        (
            administrative_duty_reference,
            administrative_duty_evidence,
        ) = detect_administrative_duty_reference(
            text
        )

        (
            legal_reference_only,
            legal_reference_evidence,
        ) = detect_legal_reference_only(
            text,
            action_types=action_types,
            nearest_notice_numbers=(
                nearest_notice_numbers
            ),
            official_context=(
                official_context
            ),
        )

        scope_evidence = (
            extract_scope_evidence(
                text
            )
        )

        verified_positive = (
            target_found
            and bool(
                action_types
            )
            and bool(
                nearest_notice_numbers
                or all_notice_numbers
            )
            and bool(
                official_context
            )
            and bool(
                administrative_regions
            )
            and not administrative_duty_reference
            and not legal_reference_only
        )

        if verified_positive:

            resolution = (
                RESOLUTION_VERIFIED
            )

        elif administrative_duty_reference:

            resolution = (
                RESOLUTION_ADMIN_DUTY
            )

        elif legal_reference_only:

            resolution = (
                RESOLUTION_LEGAL_REFERENCE
            )

        elif target_found:

            resolution = (
                RESOLUTION_TARGET_MENTION
            )

        else:

            resolution = (
                RESOLUTION_UNRELATED
            )

        target_contexts = (
            extract_target_contexts(
                text,
                radius=1600,
            )
        )

        record = {
            **item,

            "http_status": fetched.get(
                "http_status"
            ),

            "response_bytes": fetched.get(
                "response_bytes"
            ),

            "actual_sha256": actual_sha256,

            "identity_match": identity_match,

            "document_type": document_type,

            "parser": parsed.get(
                "parser"
            ),

            "text_length": len(
                text
            ),

            "target_in_document": (
                target_found
            ),

            "target_contexts": (
                target_contexts[
                    :20
                ]
            ),

            "action_types": (
                action_types
            ),

            "action_evidence": (
                action_evidence
            ),

            "all_notice_numbers": (
                all_notice_numbers
            ),

            "nearest_notice_numbers": (
                nearest_notice_numbers
            ),

            "all_dates": (
                all_dates
            ),

            "nearest_dates": (
                nearest_dates
            ),

            "administrative_regions": (
                administrative_regions
            ),

            "official_context": bool(
                official_context
            ),

            "official_context_evidence": (
                official_context
            ),

            "administrative_duty_reference": (
                administrative_duty_reference
            ),

            "administrative_duty_evidence": (
                administrative_duty_evidence
            ),

            "legal_reference_only": (
                legal_reference_only
            ),

            "legal_reference_evidence": (
                legal_reference_evidence
            ),

            "scope_extraction_status": (
                "SCOPE_EVIDENCE_EXTRACTED"
                if scope_evidence
                else "SCOPE_NOT_EXTRACTED"
            ),

            "scope_evidence": (
                scope_evidence
            ),

            "verified_positive": (
                verified_positive
            ),

            "resolution": resolution,

            # explicit inheritance guards
            "parent_region_evidence_inherited": False,

            "parent_label_evidence_inherited": False,

            "parent_notice_evidence_inherited": False,

            "parent_date_evidence_inherited": False,

            "final_positive": False,
        }

        records.append(
            record
        )

        print(
            "Document type:",
            document_type,
        )

        print(
            "Parser:",
            parsed.get(
                "parser"
            ),
        )

        print(
            "Text length:",
            len(
                text
            ),
        )

        print(
            "Target:",
            target_found,
        )

        print(
            "Action:",
            action_types,
        )

        print(
            "Nearest notice numbers:",
            nearest_notice_numbers,
        )

        print(
            "Nearest dates:",
            nearest_dates,
        )

        print(
            "Regions:",
            administrative_regions,
        )

        print(
            "Scope:",
            (
                "SCOPE_EVIDENCE_EXTRACTED"
                if scope_evidence
                else "SCOPE_NOT_EXTRACTED"
            ),
        )

        print(
            "Verified positive:",
            verified_positive,
        )

        print(
            "Resolution:",
            resolution,
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    verified_documents = [
        item
        for item in records
        if item.get(
            "verified_positive"
        )
        is True
    ]

    target_mention_documents = [
        item
        for item in records
        if item.get(
            "resolution"
        )
        == RESOLUTION_TARGET_MENTION
    ]

    unrelated_documents = [
        item
        for item in records
        if item.get(
            "resolution"
        )
        == RESOLUTION_UNRELATED
    ]

    resolution_counts = Counter(
        item.get(
            "resolution"
        )
        for item in records
    )

    # ========================================================
    # GLOBAL RESOLUTION
    # ========================================================

    if verified_documents:

        resolution = (
            "GAZETTE_RECOVERED_ATTACHMENT_TARGET_DOCUMENT_VERIFIED"
        )

        next_action = (
            "검증된 공보 원문 내 target 인접 고시번호와 날짜를 기준으로 "
            "개별 고시 identity를 확정하고, 지정·변경·해제 관계를 "
            "chronology로 정규화한다. 이후 spatial/PNU evidence를 "
            "역탐색한다."
        )

    elif target_mention_documents:

        resolution = (
            "GAZETTE_RECOVERED_ATTACHMENT_TARGET_MENTION_REQUIRES_REVIEW"
        )

        next_action = (
            "공보 원문에서 개발밀도관리구역 문구는 확인되었으나 "
            "verified positive 요건이 부족하다. target 인접 고시번호, "
            "action 및 지리 문맥을 세부 분석한다."
        )

    elif records:

        resolution = (
            "GAZETTE_RECOVERED_ATTACHMENT_VERIFICATION_COMPLETED_NO_TARGET"
        )

        next_action = (
            "복원된 당진시보 attachment에서는 개발밀도관리구역 "
            "verified positive를 확인하지 못했다. 해당 공보 경로는 "
            "negative evidence로 보존하고 국가기록원·구형 공보·관보·"
            "토지이음 및 과거 고시번호 역탐색으로 확장한다."
        )

    else:

        resolution = (
            "GAZETTE_RECOVERED_ATTACHMENT_VERIFICATION_NO_INPUT"
        )

        next_action = (
            "L-stage recovered attachment가 없어 검증을 수행하지 못했다."
        )

    # ========================================================
    # OUTPUT
    # ========================================================

    output_data = {
        "step": (
            "STEP 17-21-C-16-8-M "
            "Development Density Management Area "
            "Gazette Recovered Attachment Source Verification"
        ),

        "target": {
            "name": TARGET_NAME,
            "standard_code": STANDARD_CODE,
        },

        "input": {
            "path": str(
                INPUT_PATH
            ),

            "l_stage_resolution": (
                input_data.get(
                    "resolution"
                )
            ),
        },

        "method": {
            "l_stage_recovered_attachment_only": True,

            "network_requery_enabled": True,

            "payload_identity_sha256_recheck": True,

            "document_local_evidence_only": True,

            "parent_region_inheritance": False,

            "parent_label_inheritance": False,

            "parent_notice_inheritance": False,

            "parent_date_inheritance": False,

            "target_exact_phrase_required": True,

            "action_context_required": True,

            "notice_number_required": True,

            "official_context_required": True,

            "geographic_context_required": True,

            "scope_extraction": True,

            "scope_required_for_positive": False,

            "nearest_notice_context_extraction": True,

            "nearest_date_context_extraction": True,

            "administrative_duty_false_positive_guard": True,

            "legal_reference_false_positive_guard": True,

            "runtime_registration_allowed": False,

            "site_positive_allowed": False,

            "final_positive_promotion_allowed": False,
        },

        "summary": {
            "verification_input_count": len(
                verification_pool
            ),

            "request_count": (
                request_count
            ),

            "http_success_count": (
                http_success_count
            ),

            "download_failed_count": (
                download_failed_count
            ),

            "parse_failed_count": (
                parse_failed_count
            ),

            "identity_mismatch_count": (
                identity_mismatch_count
            ),

            "verified_positive_count": len(
                verified_documents
            ),

            "target_mention_only_count": len(
                target_mention_documents
            ),

            "unrelated_document_count": len(
                unrelated_documents
            ),
        },

        "resolution_counts": dict(
            sorted(
                resolution_counts.items()
            )
        ),

        "verification_records": records,

        "verified_positive_documents": (
            verified_documents
        ),

        "target_mention_documents": (
            target_mention_documents
        ),

        "resolution": resolution,

        "next_action": next_action,

        "runtime_registration_allowed": False,

        "site_positive_allowed": False,

        "final_positive_promotion_allowed": False,
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            output_data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # ========================================================
    # RESULT
    # ========================================================

    print()

    print(
        "=" * 60
    )

    print(
        "RECOVERED ATTACHMENT VERIFICATION RESULT"
    )

    print(
        "=" * 60
    )

    print(
        "Verification input count:",
        len(
            verification_pool
        ),
    )

    print(
        "Request count:",
        request_count,
    )

    print(
        "HTTP success count:",
        http_success_count,
    )

    print(
        "Download failed count:",
        download_failed_count,
    )

    print(
        "Parse failed count:",
        parse_failed_count,
    )

    print(
        "Identity mismatch count:",
        identity_mismatch_count,
    )

    print(
        "Verified positive count:",
        len(
            verified_documents
        ),
    )

    print(
        "Target mention only count:",
        len(
            target_mention_documents
        ),
    )

    print(
        "Unrelated document count:",
        len(
            unrelated_documents
        ),
    )

    # ========================================================
    # HIGH VALUE
    # ========================================================

    if verified_documents:

        print()

        print(
            "VERIFIED DOCUMENTS"
        )

        print(
            "-" * 60
        )

        for index, item in enumerate(
            verified_documents,
            start=1,
        ):

            print(
                f"[{index}]"
            )

            print(
                "URL:",
                item.get(
                    "document_url"
                ),
            )

            print(
                "Nearest notice numbers:",
                item.get(
                    "nearest_notice_numbers"
                ),
            )

            print(
                "Nearest dates:",
                item.get(
                    "nearest_dates"
                ),
            )

            print(
                "Action:",
                item.get(
                    "action_types"
                ),
            )

            print(
                "Regions:",
                item.get(
                    "administrative_regions"
                ),
            )

            print(
                "Scope:",
                item.get(
                    "scope_evidence"
                ),
            )

            print()

    print()

    print(
        "=" * 60
    )

    print(
        "RESOLUTION"
    )

    print(
        "=" * 60
    )

    print(
        resolution
    )

    print()

    print(
        next_action
    )

    print()

    print(
        "Output:",
        OUTPUT_PATH,
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    verification_keys = {
        (
            item[
                "attachment_identity"
            ][
                "atchFileId"
            ],
            item[
                "attachment_identity"
            ][
                "fileSn"
            ],
        )
        for item in verification_pool
    }

    record_keys = {
        (
            item[
                "attachment_identity"
            ][
                "atchFileId"
            ],
            item[
                "attachment_identity"
            ][
                "fileSn"
            ],
        )
        for item in records
    }

    all_resolutions_valid = all(
        item.get(
            "resolution"
        )
        in VALID_RESOLUTIONS
        for item in records
    )

    parent_evidence_inheritance_leakage = sum(
        1
        for item in records
        if (
            item.get(
                "parent_region_evidence_inherited"
            )
            is not False
            or item.get(
                "parent_label_evidence_inherited"
            )
            is not False
        )
    )

    target_missing_positive_leakage = sum(
        1
        for item in records
        if (
            item.get(
                "verified_positive"
            )
            is True
            and item.get(
                "target_in_document"
            )
            is not True
        )
    )

    no_action_positive_leakage = sum(
        1
        for item in records
        if (
            item.get(
                "verified_positive"
            )
            is True
            and not item.get(
                "action_types"
            )
        )
    )

    no_notice_positive_leakage = sum(
        1
        for item in records
        if (
            item.get(
                "verified_positive"
            )
            is True
            and not (
                item.get(
                    "nearest_notice_numbers"
                )
                or item.get(
                    "all_notice_numbers"
                )
            )
        )
    )

    no_official_positive_leakage = sum(
        1
        for item in records
        if (
            item.get(
                "verified_positive"
            )
            is True
            and item.get(
                "official_context"
            )
            is not True
        )
    )

    no_region_positive_leakage = sum(
        1
        for item in records
        if (
            item.get(
                "verified_positive"
            )
            is True
            and not item.get(
                "administrative_regions"
            )
        )
    )

    admin_positive_leakage = sum(
        1
        for item in records
        if (
            item.get(
                "verified_positive"
            )
            is True
            and item.get(
                "administrative_duty_reference"
            )
            is True
        )
    )

    legal_positive_leakage = sum(
        1
        for item in records
        if (
            item.get(
                "verified_positive"
            )
            is True
            and item.get(
                "legal_reference_only"
            )
            is True
        )
    )

    validations = {
        "target name": (
            TARGET_NAME
            == "개발밀도관리구역"
        ),

        "standard code": (
            STANDARD_CODE
            == "UQQ700"
        ),

        "input exists": (
            INPUT_PATH.exists()
        ),

        "L-stage input parsed": (
            isinstance(
                input_data,
                dict,
            )
        ),

        "L-stage required resolution preserved": (
            normalize_space(
                input_data.get(
                    "resolution"
                )
            )
            == L_STAGE_REQUIRED_RESOLUTION
        ),

        "verification pool loaded": (
            len(
                verification_pool
            )
            > 0
        ),

        "verification pool unique": (
            len(
                verification_keys
            )
            == len(
                verification_pool
            )
        ),

        "verification records unique": (
            len(
                record_keys
            )
            == len(
                records
            )
        ),

        "network requery enabled": (
            output_data[
                "method"
            ][
                "network_requery_enabled"
            ]
            is True
        ),

        "payload SHA-256 identity recheck enabled": (
            output_data[
                "method"
            ][
                "payload_identity_sha256_recheck"
            ]
            is True
        ),

        "document-local evidence only": (
            output_data[
                "method"
            ][
                "document_local_evidence_only"
            ]
            is True
        ),

        "parent region inheritance disabled": (
            output_data[
                "method"
            ][
                "parent_region_inheritance"
            ]
            is False
        ),

        "parent label inheritance disabled": (
            output_data[
                "method"
            ][
                "parent_label_inheritance"
            ]
            is False
        ),

        "nearest notice extraction enabled": (
            output_data[
                "method"
            ][
                "nearest_notice_context_extraction"
            ]
            is True
        ),

        "nearest date extraction enabled": (
            output_data[
                "method"
            ][
                "nearest_date_context_extraction"
            ]
            is True
        ),

        "scope not mandatory for positive": (
            output_data[
                "method"
            ][
                "scope_required_for_positive"
            ]
            is False
        ),

        "all resolutions valid": (
            all_resolutions_valid
        ),

        "parent evidence inheritance leakage zero": (
            parent_evidence_inheritance_leakage
            == 0
        ),

        "target-missing positive leakage zero": (
            target_missing_positive_leakage
            == 0
        ),

        "no-action positive leakage zero": (
            no_action_positive_leakage
            == 0
        ),

        "no-notice positive leakage zero": (
            no_notice_positive_leakage
            == 0
        ),

        "no-official-context positive leakage zero": (
            no_official_positive_leakage
            == 0
        ),

        "no-geographic-context positive leakage zero": (
            no_region_positive_leakage
            == 0
        ),

        "administrative-duty positive leakage zero": (
            admin_positive_leakage
            == 0
        ),

        "legal-reference positive leakage zero": (
            legal_positive_leakage
            == 0
        ),

        "runtime registration remains blocked": (
            output_data[
                "runtime_registration_allowed"
            ]
            is False
        ),

        "SITE TRUE remains blocked": (
            output_data[
                "site_positive_allowed"
            ]
            is False
        ),

        "final positive promotion remains blocked": (
            output_data[
                "final_positive_promotion_allowed"
            ]
            is False
        ),

        "output written": (
            OUTPUT_PATH.exists()
            and OUTPUT_PATH.stat().st_size
            > 0
        ),
    }

    print()

    print(
        "=" * 60
    )

    print(
        "VALIDATION"
    )

    print(
        "=" * 60
    )

    for name, passed in validations.items():

        print(
            f"{name}: {passed}"
        )

    print()

    print(
        "Parent evidence inheritance leakage:",
        parent_evidence_inheritance_leakage,
    )

    print(
        "Target-missing positive leakage:",
        target_missing_positive_leakage,
    )

    print(
        "No-action positive leakage:",
        no_action_positive_leakage,
    )

    print(
        "No-notice positive leakage:",
        no_notice_positive_leakage,
    )

    print(
        "No-official-context positive leakage:",
        no_official_positive_leakage,
    )

    print(
        "No-geographic-context positive leakage:",
        no_region_positive_leakage,
    )

    print(
        "Administrative-duty positive leakage:",
        admin_positive_leakage,
    )

    print(
        "Legal-reference positive leakage:",
        legal_positive_leakage,
    )

    all_pass = all(
        validations.values()
    )

    print()

    print(
        f"all_pass: {all_pass}"
    )

    if not all_pass:

        failed = [
            name
            for name, passed
            in validations.items()
            if not passed
        ]

        print()

        print(
            "FAILED:"
        )

        for name in failed:

            print(
                f"- {name}"
            )

        raise AssertionError(
            "Development density management area "
            "gazette recovered attachment source verification "
            "regression failed"
        )


if __name__ == "__main__":
    main()