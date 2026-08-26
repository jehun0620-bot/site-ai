# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-L
Development Density Management Area
Gazette Attachment Download Endpoint Recovery

목표
======================================================================
K-stage에서 공보 attachment identity는 확보했으나,
synthetic download endpoint가 HTML permission/error page를 반환한
attachment를 대상으로 실제 원문 download endpoint를 복원한다.

입력:
    law_data/output/
    development_density_management_area_
    gazette_child_document_resolution.json

출력:
    law_data/output/
    development_density_management_area_
    gazette_attachment_download_endpoint_recovery.json

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700

핵심 원칙
======================================================================
1. attachment identity:
       atchFileId
       fileSn
   를 보존한다.

2. parent HTML을 먼저 요청하여 session/cookie를 priming한다.

3. parent HTML의 다음 구조를 분석한다.
    - fn_egov_downFile()
    - onclick
    - window.open()
    - location.href
    - form/action
    - Synap FileViewer
    - attachment identity

4. parent HTML에서 실제 attachment identity와 구조적으로 연결된
   endpoint만 고신뢰 probe 대상으로 사용한다.

5. unrelated generic download endpoint에 atchFileId/fileSn을
   임의로 덧붙인 URL은 성공 후보로 인정하지 않는다.

6. 다음과 같은 known unrelated 다운로드는 차단한다.
    - dangjin_network.pdf
    - 행정전화번호부
    - 대표 홈페이지 공통 다운로드 링크

7. 응답이 PDF/HWP/HWPX라고 해도 다음 조건을 만족해야 한다.
    - endpoint가 attachment identity aware
    - identity가 candidate URL/form에 실제로 결합
    - known unrelated endpoint가 아님
    - filename identity conflict가 없음
    - cross-attachment payload collision이 없음

8. Content-Disposition filename과 parent attachment label을 비교한다.

9. SHA-256을 저장한다.
   서로 다른 attachment identity들이 서로 다른 공보 filename을
   갖고 있는데 동일 payload를 반환하면 identity binding 실패로 본다.

10. Synap viewer HTML 자체는 final document가 아니다.

11. HTML permission/error page는 document recovery가 아니다.

12. 이 단계에서는 target positive 판정을 하지 않는다.
    runtime registration / SITE TRUE / final positive promotion도 금지한다.
"""

from __future__ import annotations

import hashlib
import html
import io
import json
import re
import time
import zipfile

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import (
    parse_qsl,
    urlencode,
    urljoin,
    urlparse,
    urlunparse,
    unquote,
)

import requests


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
        "gazette_child_document_resolution.json"
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
        "gazette_attachment_download_endpoint_recovery.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"


# ============================================================
# HTTP
# ============================================================

TIMEOUT = 30

MAX_RESPONSE_BYTES = (
    40
    * 1024
    * 1024
)

REQUEST_DELAY_SECONDS = 0.03

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


# ============================================================
# DOCUMENT TYPES
# ============================================================

SUPPORTED_DOCUMENT_TYPES = {
    "PDF",
    "HWP",
    "HWPX",
}


# ============================================================
# RESOLUTIONS
# ============================================================

RESOLUTION_RECOVERED = (
    "GAZETTE_ATTACHMENT_DOWNLOAD_ENDPOINT_RECOVERED"
)

RESOLUTION_PARENT_FAILED = (
    "GAZETTE_ATTACHMENT_PARENT_DOWNLOAD_FAILED"
)

RESOLUTION_NO_ENDPOINT = (
    "GAZETTE_ATTACHMENT_DOWNLOAD_ENDPOINT_NOT_DISCOVERED"
)

RESOLUTION_PERMISSION_HTML = (
    "GAZETTE_ATTACHMENT_DOWNLOAD_ENDPOINT_RETURNED_HTML"
)

RESOLUTION_UNRELATED_ENDPOINT = (
    "GAZETTE_ATTACHMENT_UNRELATED_DOWNLOAD_ENDPOINT"
)

RESOLUTION_IDENTITY_NOT_BOUND = (
    "GAZETTE_ATTACHMENT_IDENTITY_NOT_BOUND_TO_RESPONSE"
)

RESOLUTION_FILENAME_CONFLICT = (
    "GAZETTE_ATTACHMENT_FILENAME_IDENTITY_CONFLICT"
)

RESOLUTION_PAYLOAD_COLLISION = (
    "GAZETTE_ATTACHMENT_CROSS_IDENTITY_PAYLOAD_COLLISION"
)

RESOLUTION_UNSUPPORTED_RESPONSE = (
    "GAZETTE_ATTACHMENT_UNSUPPORTED_RESPONSE"
)

RESOLUTION_NETWORK_FAILED = (
    "GAZETTE_ATTACHMENT_NETWORK_FAILED"
)


VALID_RESOLUTIONS = {
    RESOLUTION_RECOVERED,
    RESOLUTION_PARENT_FAILED,
    RESOLUTION_NO_ENDPOINT,
    RESOLUTION_PERMISSION_HTML,
    RESOLUTION_UNRELATED_ENDPOINT,
    RESOLUTION_IDENTITY_NOT_BOUND,
    RESOLUTION_FILENAME_CONFLICT,
    RESOLUTION_PAYLOAD_COLLISION,
    RESOLUTION_UNSUPPORTED_RESPONSE,
    RESOLUTION_NETWORK_FAILED,
}


# ============================================================
# KNOWN UNRELATED
# ============================================================

KNOWN_UNRELATED_FILENAME_TERMS = {
    "dangjin_network.pdf",
    "dangjin_network",
}

KNOWN_UNRELATED_LABEL_TERMS = [
    "행정전화번호부",
    "전화번호부",
]

KNOWN_UNRELATED_PATH_TERMS = [
    "/withrun/filedownload.do",
]


# ============================================================
# HTML PATTERNS
# ============================================================

SCRIPT_PATTERN = re.compile(
    r"<script\b[^>]*>(?P<body>.*?)</script>",
    re.IGNORECASE
    | re.DOTALL,
)

EXTERNAL_SCRIPT_PATTERN = re.compile(
    r"<script\b[^>]*src\s*=\s*[\"'](?P<src>[^\"']+)[\"'][^>]*>",
    re.IGNORECASE,
)

FORM_PATTERN = re.compile(
    r"<form\b(?P<attrs>[^>]*)>(?P<body>.*?)</form>",
    re.IGNORECASE
    | re.DOTALL,
)

ACTION_ATTR_PATTERN = re.compile(
    r"""action\s*=\s*["'](?P<action>[^"']+)["']""",
    re.IGNORECASE,
)

METHOD_ATTR_PATTERN = re.compile(
    r"""method\s*=\s*["'](?P<method>[^"']+)["']""",
    re.IGNORECASE,
)

INPUT_PATTERN = re.compile(
    r"<input\b(?P<attrs>[^>]*)>",
    re.IGNORECASE,
)

NAME_ATTR_PATTERN = re.compile(
    r"""name\s*=\s*["'](?P<name>[^"']+)["']""",
    re.IGNORECASE,
)

VALUE_ATTR_PATTERN = re.compile(
    r"""value\s*=\s*["'](?P<value>[^"']*)["']""",
    re.IGNORECASE,
)

ANCHOR_PATTERN = re.compile(
    r"<a\b(?P<attrs>[^>]*)>"
    r"(?P<body>.*?)"
    r"</a>",
    re.IGNORECASE
    | re.DOTALL,
)

HREF_PATTERN = re.compile(
    r"""href\s*=\s*["'](?P<href>[^"']+)["']""",
    re.IGNORECASE,
)

ONCLICK_PATTERN = re.compile(
    r"""onclick\s*=\s*["'](?P<onclick>[^"']+)["']""",
    re.IGNORECASE,
)

TAG_PATTERN = re.compile(
    r"<[^>]+>",
    re.DOTALL,
)

SCRIPT_STYLE_STRIP_PATTERN = re.compile(
    r"<(?:script|style)\b.*?</(?:script|style)>",
    re.IGNORECASE
    | re.DOTALL,
)

HTML_COMMENT_PATTERN = re.compile(
    r"<!--.*?-->",
    re.DOTALL,
)


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


def strip_html(
    raw_html: str,
) -> str:

    text = HTML_COMMENT_PATTERN.sub(
        " ",
        raw_html,
    )

    text = SCRIPT_STYLE_STRIP_PATTERN.sub(
        " ",
        text,
    )

    text = TAG_PATTERN.sub(
        " ",
        text,
    )

    text = html.unescape(
        text
    )

    return normalize_space(
        text
    )


def sha256_bytes(
    data: bytes,
) -> str:

    return hashlib.sha256(
        data
    ).hexdigest()


# ============================================================
# URL
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

JSESSIONID_PATTERN = re.compile(
    r";jsessionid=[^/?]+",
    re.IGNORECASE,
)


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

    scheme = (
        parsed.scheme
        or "https"
    ).lower()

    host = (
        parsed.hostname
        or ""
    ).lower()

    try:

        port = parsed.port

    except ValueError:

        port = None

    if (
        port
        and not (
            scheme == "https"
            and port == 443
        )
        and not (
            scheme == "http"
            and port == 80
        )
    ):

        netloc = (
            f"{host}:{port}"
        )

    else:

        netloc = host

    path = (
        parsed.path
        or "/"
    )

    path = JSESSIONID_PATTERN.sub(
        "",
        path,
    )

    path = re.sub(
        r"/{2,}",
        "/",
        path,
    )

    query_items = []
    seen = set()

    for key, value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        key = normalize_space(
            key
        )

        lowered = key.lower()

        if not key:
            continue

        if lowered in VOLATILE_QUERY_KEYS:
            continue

        if lowered in TRACKING_QUERY_KEYS:
            continue

        if "csrf" in lowered:
            continue

        if "session" in lowered:
            continue

        pair = (
            key,
            value,
        )

        if pair in seen:
            continue

        seen.add(
            pair
        )

        query_items.append(
            pair
        )

    query_items.sort(
        key=lambda item: (
            item[0].lower(),
            item[1],
        )
    )

    return urlunparse(
        (
            scheme,
            netloc,
            path,
            "",
            urlencode(
                query_items,
                doseq=True,
            ),
            "",
        )
    )


# ============================================================
# INPUT EXTRACTION
# ============================================================

def normalize_attachment_identity(
    value: Any,
) -> Dict[str, str]:

    if not isinstance(
        value,
        dict,
    ):

        return {}

    atch_file_id = normalize_space(
        value.get(
            "atchFileId"
        )
        or value.get(
            "atch_file_id"
        )
        or ""
    )

    file_sn = normalize_space(
        value.get(
            "fileSn"
        )
        or value.get(
            "file_sn"
        )
        or "0"
    )

    if not atch_file_id:
        return {}

    return {
        "atchFileId": atch_file_id,
        "fileSn": file_sn,
    }


def load_recovery_targets(
    data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    """
    K-stage output 전체를 순회하여 attachment identity와
    parent URL을 가진 child record를 수집한다.
    """

    found: List[
        Dict[str, Any]
    ] = []

    def walk(
        value: Any,
    ) -> None:

        if isinstance(
            value,
            dict,
        ):

            identity = normalize_attachment_identity(
                value.get(
                    "attachment_identity"
                )
            )

            parent_url = canonicalize_url(
                value.get(
                    "parent_url"
                )
                or ""
            )

            if (
                identity
                and parent_url
            ):

                found.append(
                    {
                        "parent_region": normalize_space(
                            value.get(
                                "parent_region"
                            )
                            or value.get(
                                "region"
                            )
                            or ""
                        ),
                        "parent_url": parent_url,
                        "child_label": normalize_space(
                            value.get(
                                "child_label"
                            )
                            or value.get(
                                "label"
                            )
                            or ""
                        ),
                        "prior_child_url": canonicalize_url(
                            value.get(
                                "child_url"
                            )
                            or ""
                        ),
                        "attachment_identity": identity,
                        "attachment_source": normalize_space(
                            value.get(
                                "attachment_source"
                            )
                            or ""
                        ),
                        "prior_resolution": normalize_space(
                            value.get(
                                "resolution"
                            )
                            or ""
                        ),
                    }
                )

            for child in value.values():

                if isinstance(
                    child,
                    (
                        dict,
                        list,
                    ),
                ):

                    walk(
                        child
                    )

        elif isinstance(
            value,
            list,
        ):

            for item in value:

                if isinstance(
                    item,
                    (
                        dict,
                        list,
                    ),
                ):

                    walk(
                        item
                    )

    walk(
        data
    )

    result: List[
        Dict[str, Any]
    ] = []

    seen: Set[
        Tuple[
            str,
            str,
            str,
        ]
    ] = set()

    for item in found:

        identity = item[
            "attachment_identity"
        ]

        key = (
            item[
                "parent_url"
            ],
            identity[
                "atchFileId"
            ],
            identity[
                "fileSn"
            ],
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            item
        )

    result.sort(
        key=lambda item: (
            item.get(
                "parent_region"
            )
            or "",
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
    )

    return result


# ============================================================
# FETCH
# ============================================================

def fetch_bytes(
    session: requests.Session,
    url: str,
    *,
    method: str = "GET",
    referer: str = "",
    data: Optional[
        Dict[str, str]
    ] = None,
) -> Dict[str, Any]:

    result = {
        "requested_url": url,
        "method": method,
        "http_status": None,
        "final_url": "",
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

        if method.upper() == "POST":

            response_context = session.post(
                url,
                data=(
                    data
                    or {}
                ),
                headers=headers,
                timeout=TIMEOUT,
                allow_redirects=True,
                stream=True,
            )

        else:

            response_context = session.get(
                url,
                headers=headers,
                timeout=TIMEOUT,
                allow_redirects=True,
                stream=True,
            )

        with response_context as response:

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
# HTML DECODE
# ============================================================

def decode_html_bytes(
    data: bytes,
) -> Tuple[str, str]:

    for encoding in [
        "utf-8",
        "cp949",
        "euc-kr",
    ]:

        try:

            return (
                data.decode(
                    encoding
                ),
                encoding,
            )

        except UnicodeDecodeError:
            pass

    return (
        data.decode(
            "utf-8",
            errors="replace",
        ),
        "utf-8-replace",
    )


# ============================================================
# FILENAME
# ============================================================

def extract_filename_from_content_disposition(
    value: str,
) -> str:

    text = normalize_space(
        value
    )

    if not text:
        return ""

    patterns = [
        re.compile(
            r"""filename\*\s*=\s*UTF-8''([^;]+)""",
            re.IGNORECASE,
        ),
        re.compile(
            r'''filename\s*=\s*"([^"]+)"''',
            re.IGNORECASE,
        ),
        re.compile(
            r"""filename\s*=\s*'([^']+)'""",
            re.IGNORECASE,
        ),
        re.compile(
            r"""filename\s*=\s*([^;]+)""",
            re.IGNORECASE,
        ),
    ]

    for pattern in patterns:

        match = pattern.search(
            text
        )

        if not match:
            continue

        filename = normalize_space(
            unquote(
                match.group(1)
            )
        )

        if filename:

            return filename

    return ""


def extract_expected_filename(
    label: str,
) -> str:

    text = normalize_space(
        label
    )

    if not text:
        return ""

    match = re.search(
        r"([^/\\]+?"
        r"\.(?:pdf|hwp|hwpx|doc|docx|xls|xlsx))",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return ""

    return normalize_space(
        match.group(1)
    )


def normalize_filename_for_compare(
    filename: str,
) -> str:

    value = normalize_space(
        filename
    ).lower()

    value = re.sub(
        r"\s+",
        "",
        value,
    )

    value = re.sub(
        r"\([^)]*\)",
        "",
        value,
    )

    return value


def filename_identity_conflict(
    expected: str,
    actual: str,
) -> bool:

    expected_n = normalize_filename_for_compare(
        expected
    )

    actual_n = normalize_filename_for_compare(
        actual
    )

    if not expected_n:
        return False

    if not actual_n:
        return False

    if expected_n == actual_n:
        return False

    expected_stem = re.sub(
        r"\.[^.]+$",
        "",
        expected_n,
    )

    actual_stem = re.sub(
        r"\.[^.]+$",
        "",
        actual_n,
    )

    if (
        expected_stem
        and actual_stem
        and (
            expected_stem in actual_stem
            or actual_stem in expected_stem
        )
    ):

        return False

    return True


# ============================================================
# DOCUMENT TYPE
# ============================================================

def detect_document_type(
    *,
    final_url: str,
    content_type: str,
    content_disposition: str,
    data: bytes,
) -> str:

    filename = (
        extract_filename_from_content_disposition(
            content_disposition
        )
    )

    path = (
        urlparse(
            final_url
        ).path
        or ""
    ).lower()

    filename_lower = (
        filename.lower()
    )

    content_type_lower = (
        content_type.lower()
    )

    for source in [
        path,
        filename_lower,
    ]:

        if source.endswith(
            ".pdf"
        ):
            return "PDF"

        if source.endswith(
            ".hwpx"
        ):
            return "HWPX"

        if source.endswith(
            ".hwp"
        ):
            return "HWP"

    if "application/pdf" in content_type_lower:
        return "PDF"

    if (
        "application/haansofthwp"
        in content_type_lower
        or "application/x-hwp"
        in content_type_lower
    ):
        return "HWP"

    if (
        "application/vnd.hancom.hwpx"
        in content_type_lower
    ):
        return "HWPX"

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

    prefix = data[
        :4096
    ].lstrip().lower()

    if (
        prefix.startswith(
            b"<!doctype html"
        )
        or prefix.startswith(
            b"<html"
        )
        or b"<html" in prefix
    ):

        return "HTML"

    if (
        "text/html"
        in content_type_lower
        or "application/xhtml"
        in content_type_lower
    ):

        return "HTML"

    return "UNKNOWN"


# ============================================================
# UNRELATED GUARD
# ============================================================

def is_known_unrelated_download(
    *,
    label: str,
    url: str,
    filename: str,
) -> Tuple[
    bool,
    List[str],
]:

    evidence: List[str] = []

    label_lower = normalize_space(
        label
    ).lower()

    url_lower = normalize_space(
        url
    ).lower()

    filename_lower = normalize_space(
        filename
    ).lower()

    for term in KNOWN_UNRELATED_LABEL_TERMS:

        if term.lower() in label_lower:

            evidence.append(
                f"label:{term}"
            )

    for term in KNOWN_UNRELATED_FILENAME_TERMS:

        if term.lower() in filename_lower:

            evidence.append(
                f"filename:{term}"
            )

        if term.lower() in url_lower:

            evidence.append(
                f"url:{term}"
            )

    for term in KNOWN_UNRELATED_PATH_TERMS:

        if term.lower() in url_lower:

            evidence.append(
                f"path:{term}"
            )

    return (
        bool(
            evidence
        ),
        unique_strings(
            evidence
        ),
    )


# ============================================================
# FUNCTION EXTRACTION
# ============================================================

def extract_fn_egov_downfile_implementation(
    javascript: str,
) -> str:

    patterns = [
        re.compile(
            r"function\s+fn_egov_downFile\s*"
            r"\([^)]*\)\s*\{(?P<body>.*?)\}",
            re.IGNORECASE
            | re.DOTALL,
        ),
        re.compile(
            r"fn_egov_downFile\s*=\s*function\s*"
            r"\([^)]*\)\s*\{(?P<body>.*?)\}",
            re.IGNORECASE
            | re.DOTALL,
        ),
    ]

    for pattern in patterns:

        match = pattern.search(
            javascript
        )

        if match:

            return normalize_space(
                match.group(0)
            )

    return ""


def build_fn_egov_endpoint(
    *,
    parent_url: str,
    implementation: str,
    identity: Dict[str, str],
) -> str:

    """
    다음 형태 지원:

    window.open(
        "/cmm/fms/FileDown.do?atchFileId="
        +atchFileId+
        "&fileSn="
        +fileSn
    );

    literal path를 식별하고 identity를 실제 parameter 위치에 결합한다.
    """

    if not implementation:
        return ""

    atch_file_id = identity[
        "atchFileId"
    ]

    file_sn = identity[
        "fileSn"
    ]

    path_match = re.search(
        r"""["'](
            [^"']*
            FileDown\.do
            [^"']*
        )["']""",
        implementation,
        flags=(
            re.IGNORECASE
            | re.VERBOSE
        ),
    )

    if not path_match:

        return ""

    literal = html.unescape(
        path_match.group(1)
    )

    # 가장 일반적인 eGov FileDown endpoint
    parsed_literal = urlparse(
        urljoin(
            parent_url,
            literal,
        )
    )

    query = dict(
        parse_qsl(
            parsed_literal.query,
            keep_blank_values=True,
        )
    )

    query[
        "atchFileId"
    ] = atch_file_id

    query[
        "fileSn"
    ] = file_sn

    return canonicalize_url(
        urlunparse(
            (
                parsed_literal.scheme,
                parsed_literal.netloc,
                parsed_literal.path,
                "",
                urlencode(
                    query
                ),
                "",
            )
        )
    )


# ============================================================
# DIRECT URL DISCOVERY
# ============================================================

def url_has_attachment_identity_parameters(
    url: str,
) -> bool:

    try:

        query = {
            key.lower(): value
            for key, value
            in parse_qsl(
                urlparse(
                    url
                ).query,
                keep_blank_values=True,
            )
        }

    except Exception:

        return False

    return (
        "atchfileid"
        in query
        and "filesn"
        in query
    )


def url_matches_attachment_identity(
    url: str,
    identity: Dict[str, str],
) -> bool:

    try:

        query = {
            key.lower(): value
            for key, value
            in parse_qsl(
                urlparse(
                    url
                ).query,
                keep_blank_values=True,
            )
        }

    except Exception:

        return False

    return (
        query.get(
            "atchfileid"
        )
        == identity[
            "atchFileId"
        ]
        and query.get(
            "filesn"
        )
        == identity[
            "fileSn"
        ]
    )


def extract_direct_identity_urls(
    parent_url: str,
    raw_html: str,
    identity: Dict[str, str],
) -> List[str]:

    result: List[str] = []

    patterns = [
        r"""["']([^"']*FileDown\.do[^"']*)["']""",
        r"""href\s*=\s*["']([^"']+)["']""",
        r"""window\.open\s*\(\s*["']([^"']+)["']""",
        r"""location\.href\s*=\s*["']([^"']+)["']""",
    ]

    for pattern in patterns:

        for match in re.finditer(
            pattern,
            raw_html,
            flags=re.IGNORECASE,
        ):

            raw_url = html.unescape(
                normalize_space(
                    match.group(1)
                )
            )

            if not raw_url:
                continue

            absolute = canonicalize_url(
                urljoin(
                    parent_url,
                    raw_url,
                )
            )

            if not absolute:
                continue

            if not url_has_attachment_identity_parameters(
                absolute
            ):
                continue

            if not url_matches_attachment_identity(
                absolute,
                identity,
            ):
                continue

            result.append(
                absolute
            )

    return unique_strings(
        result
    )


# ============================================================
# FORM DISCOVERY
# ============================================================

def extract_identity_bound_forms(
    parent_url: str,
    raw_html: str,
    identity: Dict[str, str],
) -> List[Dict[str, Any]]:

    results: List[
        Dict[str, Any]
    ] = []

    for match in FORM_PATTERN.finditer(
        raw_html
    ):

        attrs = match.group(
            "attrs"
        )

        body = match.group(
            "body"
        )

        action_match = ACTION_ATTR_PATTERN.search(
            attrs
        )

        if not action_match:
            continue

        action = canonicalize_url(
            urljoin(
                parent_url,
                html.unescape(
                    action_match.group(
                        "action"
                    )
                ),
            )
        )

        if not action:
            continue

        method_match = METHOD_ATTR_PATTERN.search(
            attrs
        )

        method = (
            normalize_space(
                method_match.group(
                    "method"
                )
            ).upper()
            if method_match
            else "GET"
        )

        fields: Dict[str, str] = {}

        for input_match in INPUT_PATTERN.finditer(
            body
        ):

            input_attrs = input_match.group(
                "attrs"
            )

            name_match = NAME_ATTR_PATTERN.search(
                input_attrs
            )

            if not name_match:
                continue

            name = normalize_space(
                name_match.group(
                    "name"
                )
            )

            value_match = VALUE_ATTR_PATTERN.search(
                input_attrs
            )

            value = (
                normalize_space(
                    value_match.group(
                        "value"
                    )
                )
                if value_match
                else ""
            )

            fields[
                name
            ] = value

        lowered = {
            key.lower(): value
            for key, value
            in fields.items()
        }

        if (
            "atchfileid"
            not in lowered
            or "filesn"
            not in lowered
        ):

            continue

        fields[
            next(
                key
                for key
                in fields
                if key.lower()
                == "atchfileid"
            )
        ] = identity[
            "atchFileId"
        ]

        fields[
            next(
                key
                for key
                in fields
                if key.lower()
                == "filesn"
            )
        ] = identity[
            "fileSn"
        ]

        results.append(
            {
                "method": (
                    method
                    if method in {
                        "GET",
                        "POST",
                    }
                    else "POST"
                ),
                "url": action,
                "data": fields,
                "source": (
                    "IDENTITY_BOUND_FORM"
                ),
                "identity_bound": True,
            }
        )

    return results


# ============================================================
# ENDPOINT CANDIDATES
# ============================================================

def build_endpoint_candidates(
    *,
    parent_url: str,
    raw_html: str,
    external_scripts: List[str],
    identity: Dict[str, str],
) -> Tuple[
    List[Dict[str, Any]],
    Dict[str, Any],
]:

    candidates: List[
        Dict[str, Any]
    ] = []

    diagnostics = {
        "fn_egov_downFile_found": False,
        "fn_egov_downFile_implementation": "",
        "direct_identity_url_count": 0,
        "identity_bound_form_count": 0,
    }

    combined_javascript = "\n".join(
        [
            match.group(
                "body"
            )
            for match
            in SCRIPT_PATTERN.finditer(
                raw_html
            )
        ]
        + external_scripts
    )

    implementation = (
        extract_fn_egov_downfile_implementation(
            combined_javascript
        )
    )

    if implementation:

        diagnostics[
            "fn_egov_downFile_found"
        ] = True

        diagnostics[
            "fn_egov_downFile_implementation"
        ] = implementation

        fn_url = build_fn_egov_endpoint(
            parent_url=parent_url,
            implementation=implementation,
            identity=identity,
        )

        if fn_url:

            candidates.append(
                {
                    "method": "GET",
                    "url": fn_url,
                    "data": {},
                    "source": (
                        "FN_EGOV_DOWNFILE_IMPLEMENTATION"
                    ),
                    "identity_bound": (
                        url_matches_attachment_identity(
                            fn_url,
                            identity,
                        )
                    ),
                }
            )

    direct_urls = extract_direct_identity_urls(
        parent_url,
        raw_html,
        identity,
    )

    diagnostics[
        "direct_identity_url_count"
    ] = len(
        direct_urls
    )

    for url in direct_urls:

        candidates.append(
            {
                "method": "GET",
                "url": url,
                "data": {},
                "source": (
                    "DIRECT_PARENT_IDENTITY_URL"
                ),
                "identity_bound": True,
            }
        )

    forms = extract_identity_bound_forms(
        parent_url,
        raw_html,
        identity,
    )

    diagnostics[
        "identity_bound_form_count"
    ] = len(
        forms
    )

    candidates.extend(
        forms
    )

    # --------------------------------------------------------
    # Dedupe
    # --------------------------------------------------------

    result: List[
        Dict[str, Any]
    ] = []

    seen: Set[
        Tuple[
            str,
            str,
            str,
        ]
    ] = set()

    for item in candidates:

        method = normalize_space(
            item.get(
                "method"
            )
        ).upper()

        url = canonicalize_url(
            item.get(
                "url"
            )
            or ""
        )

        data_json = json.dumps(
            item.get(
                "data"
            )
            or {},
            sort_keys=True,
            ensure_ascii=False,
        )

        key = (
            method,
            url,
            data_json,
        )

        if not url:
            continue

        if key in seen:
            continue

        seen.add(
            key
        )

        normalized = dict(
            item
        )

        normalized[
            "method"
        ] = method

        normalized[
            "url"
        ] = url

        result.append(
            normalized
        )

    return (
        result,
        diagnostics,
    )


# ============================================================
# EXTERNAL SCRIPT
# ============================================================

def fetch_external_scripts(
    session: requests.Session,
    *,
    parent_url: str,
    raw_html: str,
) -> Tuple[
    List[str],
    int,
    int,
]:

    scripts: List[str] = []

    request_count = 0
    success_count = 0

    seen: Set[str] = set()

    for match in EXTERNAL_SCRIPT_PATTERN.finditer(
        raw_html
    ):

        src = canonicalize_url(
            urljoin(
                parent_url,
                html.unescape(
                    match.group(
                        "src"
                    )
                ),
            )
        )

        if not src:
            continue

        if src in seen:
            continue

        seen.add(
            src
        )

        request_count += 1

        fetched = fetch_bytes(
            session,
            src,
            referer=parent_url,
        )

        if fetched.get(
            "http_status"
        ) == 200:

            success_count += 1

        if fetched.get(
            "error"
        ):

            continue

        data = fetched.get(
            "data"
        ) or b""

        if not data:
            continue

        text, _ = decode_html_bytes(
            data
        )

        scripts.append(
            text
        )

    return (
        scripts,
        request_count,
        success_count,
    )


# ============================================================
# PROBE
# ============================================================

def probe_candidate(
    session: requests.Session,
    *,
    candidate: Dict[str, Any],
    parent_url: str,
    child_label: str,
    identity: Dict[str, str],
) -> Dict[str, Any]:

    method = (
        candidate.get(
            "method"
        )
        or "GET"
    )

    url = candidate[
        "url"
    ]

    data = (
        candidate.get(
            "data"
        )
        or {}
    )

    identity_bound = bool(
        candidate.get(
            "identity_bound"
        )
    )

    fetched = fetch_bytes(
        session,
        url,
        method=method,
        referer=parent_url,
        data=data,
    )

    response_data = (
        fetched.get(
            "data"
        )
        or b""
    )

    final_url = (
        fetched.get(
            "final_url"
        )
        or url
    )

    content_disposition = normalize_space(
        fetched.get(
            "content_disposition"
        )
    )

    filename = (
        extract_filename_from_content_disposition(
            content_disposition
        )
    )

    document_type = detect_document_type(
        final_url=final_url,
        content_type=normalize_space(
            fetched.get(
                "content_type"
            )
        ),
        content_disposition=content_disposition,
        data=response_data,
    )

    expected_filename = (
        extract_expected_filename(
            child_label
        )
    )

    unrelated, unrelated_evidence = (
        is_known_unrelated_download(
            label=child_label,
            url=final_url,
            filename=filename,
        )
    )

    filename_conflict = (
        filename_identity_conflict(
            expected_filename,
            filename,
        )
    )

    response_hash = (
        sha256_bytes(
            response_data
        )
        if response_data
        else ""
    )

    html_preview = ""

    if document_type == "HTML":

        decoded, _ = decode_html_bytes(
            response_data
        )

        html_preview = strip_html(
            decoded
        )[
            :500
        ]

    valid_supported_document = (
        document_type
        in SUPPORTED_DOCUMENT_TYPES
    )

    strict_success = (
        not fetched.get(
            "error"
        )
        and fetched.get(
            "http_status"
        )
        == 200
        and valid_supported_document
        and identity_bound
        and not unrelated
        and not filename_conflict
    )

    if fetched.get(
        "error"
    ):

        preliminary_resolution = (
            RESOLUTION_NETWORK_FAILED
        )

    elif document_type == "HTML":

        preliminary_resolution = (
            RESOLUTION_PERMISSION_HTML
        )

    elif unrelated:

        preliminary_resolution = (
            RESOLUTION_UNRELATED_ENDPOINT
        )

    elif not identity_bound:

        preliminary_resolution = (
            RESOLUTION_IDENTITY_NOT_BOUND
        )

    elif filename_conflict:

        preliminary_resolution = (
            RESOLUTION_FILENAME_CONFLICT
        )

    elif not valid_supported_document:

        preliminary_resolution = (
            RESOLUTION_UNSUPPORTED_RESPONSE
        )

    elif strict_success:

        preliminary_resolution = (
            RESOLUTION_RECOVERED
        )

    else:

        preliminary_resolution = (
            RESOLUTION_UNSUPPORTED_RESPONSE
        )

    return {
        "candidate_source": candidate.get(
            "source"
        ),

        "method": method,

        "requested_url": url,

        "request_data": data,

        "identity_bound": identity_bound,

        "attachment_identity": dict(
            identity
        ),

        "http_status": fetched.get(
            "http_status"
        ),

        "final_url": final_url,

        "content_type": fetched.get(
            "content_type"
        ),

        "content_disposition": (
            content_disposition
        ),

        "response_bytes": fetched.get(
            "response_bytes"
        ),

        "response_sha256": response_hash,

        "document_type": document_type,

        "expected_filename": (
            expected_filename
        ),

        "response_filename": filename,

        "filename_identity_conflict": (
            filename_conflict
        ),

        "known_unrelated_download": (
            unrelated
        ),

        "known_unrelated_evidence": (
            unrelated_evidence
        ),

        "html_response_preview": (
            html_preview
        ),

        "network_error": fetched.get(
            "error"
        ),

        "strict_success": (
            strict_success
        ),

        "preliminary_resolution": (
            preliminary_resolution
        ),
    }


# ============================================================
# BEST PROBE
# ============================================================

PROBE_PRIORITY = {
    RESOLUTION_RECOVERED: 100,
    RESOLUTION_FILENAME_CONFLICT: 70,
    RESOLUTION_IDENTITY_NOT_BOUND: 65,
    RESOLUTION_UNRELATED_ENDPOINT: 60,
    RESOLUTION_PERMISSION_HTML: 50,
    RESOLUTION_UNSUPPORTED_RESPONSE: 40,
    RESOLUTION_NETWORK_FAILED: 20,
}


def choose_best_probe(
    probes: List[
        Dict[str, Any]
    ],
) -> Optional[
    Dict[str, Any]
]:

    if not probes:
        return None

    ordered = sorted(
        probes,
        key=lambda item: (
            -PROBE_PRIORITY.get(
                item.get(
                    "preliminary_resolution"
                ),
                0,
            ),
            -int(
                item.get(
                    "identity_bound"
                )
                is True
            ),
            -int(
                item.get(
                    "http_status"
                )
                == 200
            ),
            -int(
                item.get(
                    "response_bytes"
                )
                or 0
            ),
        ),
    )

    return dict(
        ordered[
            0
        ]
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
        "GAZETTE ATTACHMENT DOWNLOAD ENDPOINT RECOVERY"
    )

    print(
        "=" * 60
    )

    print()

    print(
        f"Target: {TARGET_NAME}"
    )

    print(
        f"Standard code: {STANDARD_CODE}"
    )

    print(
        f"Input: {INPUT_PATH}"
    )

    print()

    # ========================================================
    # INPUT
    # ========================================================

    if not INPUT_PATH.exists():

        raise FileNotFoundError(
            "K-stage output not found: "
            f"{INPUT_PATH}"
        )

    input_data = json.loads(
        INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        input_data,
        dict,
    ):

        raise TypeError(
            "K-stage output must be JSON object."
        )

    targets = load_recovery_targets(
        input_data
    )

    print(
        "Attachment recovery target count:",
        len(
            targets
        ),
    )

    print()

    # ========================================================
    # SESSION
    # ========================================================

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
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

    # ========================================================
    # COUNTERS
    # ========================================================

    parent_request_count = 0
    parent_http_success_count = 0

    script_request_count = 0
    script_http_success_count = 0

    endpoint_candidate_count = 0
    probe_count = 0

    html_response_count = 0
    network_error_count = 0

    records: List[
        Dict[str, Any]
    ] = []

    # ========================================================
    # TARGET LOOP
    # ========================================================

    for index, target in enumerate(
        targets,
        start=1,
    ):

        parent_region = normalize_space(
            target.get(
                "parent_region"
            )
        )

        parent_url = canonicalize_url(
            target.get(
                "parent_url"
            )
            or ""
        )

        child_label = normalize_space(
            target.get(
                "child_label"
            )
        )

        identity = normalize_attachment_identity(
            target.get(
                "attachment_identity"
            )
        )

        print(
            "-" * 60
        )

        print(
            f"TARGET {index}"
        )

        print(
            "Region:",
            parent_region,
        )

        print(
            "Parent URL:",
            parent_url,
        )

        print(
            "Label:",
            child_label,
        )

        print(
            "Attachment identity:",
            identity,
        )

        parent_request_count += 1

        parent_fetch = fetch_bytes(
            session,
            parent_url,
        )

        if parent_fetch.get(
            "http_status"
        ) == 200:

            parent_http_success_count += 1

        if parent_fetch.get(
            "error"
        ):

            record = {
                "target_index": index,
                "parent_region": parent_region,
                "parent_url": parent_url,
                "child_label": child_label,
                "attachment_identity": identity,
                "endpoint_candidates": [],
                "probe_results": [],
                "recovered": False,
                "resolution": (
                    RESOLUTION_PARENT_FAILED
                ),
                "error": parent_fetch.get(
                    "error"
                ),
            }

            records.append(
                record
            )

            print(
                "Recovered:",
                False,
            )

            print(
                "Resolution:",
                RESOLUTION_PARENT_FAILED,
            )

            continue

        raw_html, html_encoding = (
            decode_html_bytes(
                parent_fetch.get(
                    "data"
                )
                or b""
            )
        )

        (
            external_scripts,
            current_script_requests,
            current_script_success,
        ) = fetch_external_scripts(
            session,
            parent_url=parent_url,
            raw_html=raw_html,
        )

        script_request_count += (
            current_script_requests
        )

        script_http_success_count += (
            current_script_success
        )

        (
            candidates,
            diagnostics,
        ) = build_endpoint_candidates(
            parent_url=parent_url,
            raw_html=raw_html,
            external_scripts=external_scripts,
            identity=identity,
        )

        endpoint_candidate_count += len(
            candidates
        )

        print(
            "fn_egov_downFile implementation found:",
            diagnostics[
                "fn_egov_downFile_found"
            ],
        )

        if diagnostics[
            "fn_egov_downFile_found"
        ]:

            print(
                "Function preview:",
                diagnostics[
                    "fn_egov_downFile_implementation"
                ][
                    :500
                ],
            )

        print(
            "Endpoint candidates:",
            len(
                candidates
            ),
        )

        probe_results: List[
            Dict[str, Any]
        ] = []

        for candidate in candidates:

            probe_count += 1

            probe = probe_candidate(
                session,
                candidate=candidate,
                parent_url=parent_url,
                child_label=child_label,
                identity=identity,
            )

            probe_results.append(
                probe
            )

            if (
                probe.get(
                    "document_type"
                )
                == "HTML"
            ):

                html_response_count += 1

            if probe.get(
                "network_error"
            ):

                network_error_count += 1

            if REQUEST_DELAY_SECONDS > 0:

                time.sleep(
                    REQUEST_DELAY_SECONDS
                )

        best_probe = choose_best_probe(
            probe_results
        )

        if best_probe is None:

            resolution = (
                RESOLUTION_NO_ENDPOINT
            )

            recovered = False

        else:

            resolution = (
                best_probe[
                    "preliminary_resolution"
                ]
            )

            recovered = (
                best_probe.get(
                    "strict_success"
                )
                is True
            )

        record = {
            "target_index": index,

            "parent_region": parent_region,

            "parent_url": parent_url,

            "child_label": child_label,

            "expected_filename": (
                extract_expected_filename(
                    child_label
                )
            ),

            "attachment_identity": (
                identity
            ),

            "attachment_source": (
                target.get(
                    "attachment_source"
                )
            ),

            "prior_child_url": (
                target.get(
                    "prior_child_url"
                )
            ),

            "prior_resolution": (
                target.get(
                    "prior_resolution"
                )
            ),

            "parent_http_status": (
                parent_fetch.get(
                    "http_status"
                )
            ),

            "parent_html_encoding": (
                html_encoding
            ),

            "fn_egov_downFile_found": (
                diagnostics[
                    "fn_egov_downFile_found"
                ]
            ),

            "fn_egov_downFile_implementation": (
                diagnostics[
                    "fn_egov_downFile_implementation"
                ]
            ),

            "direct_identity_url_count": (
                diagnostics[
                    "direct_identity_url_count"
                ]
            ),

            "identity_bound_form_count": (
                diagnostics[
                    "identity_bound_form_count"
                ]
            ),

            "endpoint_candidate_count": len(
                candidates
            ),

            "endpoint_candidates": (
                candidates
            ),

            "probe_results": (
                probe_results
            ),

            "best_probe": (
                best_probe
            ),

            "recovered": recovered,

            "resolution": resolution,

            # collision evaluation later
            "cross_attachment_payload_collision": False,

            "collision_attachment_identities": [],

            "final_positive": False,
        }

        records.append(
            record
        )

        print(
            "Recovered:",
            recovered,
        )

        if best_probe:

            print(
                "Method:",
                best_probe.get(
                    "method"
                ),
            )

            print(
                "URL:",
                best_probe.get(
                    "final_url"
                )
                or best_probe.get(
                    "requested_url"
                ),
            )

            print(
                "Identity bound:",
                best_probe.get(
                    "identity_bound"
                ),
            )

            print(
                "Document type:",
                best_probe.get(
                    "document_type"
                ),
            )

            print(
                "Content-Type:",
                best_probe.get(
                    "content_type"
                ),
            )

            print(
                "Expected filename:",
                best_probe.get(
                    "expected_filename"
                ),
            )

            print(
                "Response filename:",
                best_probe.get(
                    "response_filename"
                ),
            )

            print(
                "SHA-256:",
                best_probe.get(
                    "response_sha256"
                ),
            )

            if best_probe.get(
                "html_response_preview"
            ):

                print(
                    "HTML response preview:",
                    best_probe.get(
                        "html_response_preview"
                    ),
                )

        print(
            "Resolution:",
            resolution,
        )

    # ========================================================
    # CROSS-ATTACHMENT PAYLOAD COLLISION GUARD
    # ========================================================

    hash_groups: Dict[
        str,
        List[
            Dict[str, Any]
        ],
    ] = defaultdict(
        list
    )

    for record in records:

        if not record.get(
            "recovered"
        ):

            continue

        best_probe = (
            record.get(
                "best_probe"
            )
            or {}
        )

        response_hash = normalize_space(
            best_probe.get(
                "response_sha256"
            )
        )

        if not response_hash:
            continue

        hash_groups[
            response_hash
        ].append(
            record
        )

    collision_group_count = 0

    for response_hash, group in hash_groups.items():

        if len(
            group
        ) < 2:

            continue

        identities = {
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
            for item in group
        }

        expected_filenames = {
            normalize_filename_for_compare(
                item.get(
                    "expected_filename"
                )
                or ""
            )
            for item in group
            if item.get(
                "expected_filename"
            )
        }

        if len(
            identities
        ) < 2:

            continue

        # 서로 다른 identity이며 서로 다른 공보 filename인데
        # payload가 완전히 같으면 identity binding 실패로 간주
        if len(
            expected_filenames
        ) < 2:

            continue

        collision_group_count += 1

        identity_strings = [
            (
                f"{atch_file_id}:{file_sn}"
            )
            for atch_file_id, file_sn
            in sorted(
                identities
            )
        ]

        for item in group:

            item[
                "cross_attachment_payload_collision"
            ] = True

            item[
                "collision_attachment_identities"
            ] = identity_strings

            item[
                "recovered"
            ] = False

            item[
                "resolution"
            ] = (
                RESOLUTION_PAYLOAD_COLLISION
            )

    # ========================================================
    # FINAL RECOVERED
    # ========================================================

    recovered_documents = [
        item
        for item in records
        if item.get(
            "recovered"
        )
        is True
        and item.get(
            "resolution"
        )
        == RESOLUTION_RECOVERED
    ]

    # ========================================================
    # CANONICAL RECOVERY DEDUPE
    # ========================================================

    canonical_recovered: List[
        Dict[str, Any]
    ] = []

    seen_recovery_keys: Set[
        Tuple[
            str,
            str,
            str,
        ]
    ] = set()

    for item in recovered_documents:

        identity = item[
            "attachment_identity"
        ]

        best_probe = (
            item.get(
                "best_probe"
            )
            or {}
        )

        key = (
            identity[
                "atchFileId"
            ],
            identity[
                "fileSn"
            ],
            normalize_space(
                best_probe.get(
                    "response_sha256"
                )
            ),
        )

        if key in seen_recovery_keys:
            continue

        seen_recovery_keys.add(
            key
        )

        canonical_recovered.append(
            item
        )

    # ========================================================
    # COUNTS
    # ========================================================

    resolution_counts = Counter(
        item.get(
            "resolution"
        )
        for item in records
    )

    filename_conflict_count = sum(
        1
        for item in records
        if item.get(
            "resolution"
        )
        == RESOLUTION_FILENAME_CONFLICT
    )

    unrelated_endpoint_count = sum(
        1
        for item in records
        if item.get(
            "resolution"
        )
        == RESOLUTION_UNRELATED_ENDPOINT
    )

    identity_not_bound_count = sum(
        1
        for item in records
        if item.get(
            "resolution"
        )
        == RESOLUTION_IDENTITY_NOT_BOUND
    )

    payload_collision_count = sum(
        1
        for item in records
        if item.get(
            "resolution"
        )
        == RESOLUTION_PAYLOAD_COLLISION
    )

    # ========================================================
    # GLOBAL RESOLUTION
    # ========================================================

    if canonical_recovered:

        resolution = (
            "GAZETTE_ATTACHMENT_DOWNLOAD_ENDPOINT_RECOVERED"
        )

        next_action = (
            "attachment identity와 실제 응답의 결합이 검증된 "
            "PDF/HWP/HWPX만 대상으로 document-local evidence를 "
            "재검증하여 개발밀도관리구역 target, 지정·변경·해제 action, "
            "고시번호, 고시일, 행정구역 및 scope를 검증한다."
        )

    elif (
        payload_collision_count
        or filename_conflict_count
        or unrelated_endpoint_count
        or identity_not_bound_count
    ):

        resolution = (
            "GAZETTE_ATTACHMENT_FALSE_RECOVERY_REJECTED"
        )

        next_action = (
            "PDF/HWP 응답 자체는 확보되었으나 attachment identity와 "
            "실제 payload의 결합이 검증되지 않아 recovery를 차단했다. "
            "fn_egov_downFile의 실제 요청 조건, 인증/Referer/session, "
            "별도 file service endpoint 및 Synap backend metadata를 "
            "추가 분석한다."
        )

    elif records:

        resolution = (
            "GAZETTE_ATTACHMENT_DOWNLOAD_ENDPOINT_RECOVERY_UNRESOLVED"
        )

        next_action = (
            "현재 parent HTML 분석으로 실제 attachment 원문 endpoint를 "
            "복원하지 못했다. fn_egov_downFile 서버 동작, POST/form, "
            "session cookie 및 Synap attachment backend를 분석한다."
        )

    else:

        resolution = (
            "GAZETTE_ATTACHMENT_DOWNLOAD_ENDPOINT_RECOVERY_NO_TARGET"
        )

        next_action = (
            "K-stage에서 attachment recovery 대상을 찾지 못했다."
        )

    # ========================================================
    # OUTPUT
    # ========================================================

    output_data = {
        "step": (
            "STEP 17-21-C-16-8-L "
            "Development Density Management Area "
            "Gazette Attachment Download Endpoint Recovery"
        ),

        "target": {
            "name": TARGET_NAME,
            "standard_code": STANDARD_CODE,
        },

        "input": {
            "path": str(
                INPUT_PATH
            ),
            "k_stage_resolution": (
                input_data.get(
                    "resolution"
                )
            ),
        },

        "method": {
            "attachment_identity_only": True,

            "parent_session_priming": True,

            "referer_probe": True,

            "parent_html_analysis": True,

            "inline_javascript_analysis": True,

            "external_javascript_analysis": True,

            "fn_egov_downFile_analysis": True,

            "identity_bound_endpoint_only": True,

            "generic_download_parameter_injection_allowed": False,

            "known_unrelated_download_guard": True,

            "filename_identity_guard": True,

            "response_sha256_enabled": True,

            "cross_attachment_payload_collision_guard": True,

            "synap_viewer_final_document_allowed": False,

            "html_permission_page_allowed": False,

            "magic_byte_verification": True,

            "runtime_registration_allowed": False,

            "site_positive_allowed": False,

            "final_positive_promotion_allowed": False,
        },

        "summary": {
            "recovery_target_count": len(
                targets
            ),

            "parent_request_count": (
                parent_request_count
            ),

            "parent_http_success_count": (
                parent_http_success_count
            ),

            "script_request_count": (
                script_request_count
            ),

            "script_http_success_count": (
                script_http_success_count
            ),

            "endpoint_candidate_count": (
                endpoint_candidate_count
            ),

            "probe_count": (
                probe_count
            ),

            "html_response_count": (
                html_response_count
            ),

            "network_error_count": (
                network_error_count
            ),

            "filename_conflict_count": (
                filename_conflict_count
            ),

            "unrelated_endpoint_count": (
                unrelated_endpoint_count
            ),

            "identity_not_bound_count": (
                identity_not_bound_count
            ),

            "payload_collision_record_count": (
                payload_collision_count
            ),

            "payload_collision_group_count": (
                collision_group_count
            ),

            "canonical_recovered_document_count": len(
                canonical_recovered
            ),
        },

        "resolution_counts": dict(
            sorted(
                resolution_counts.items()
            )
        ),

        "recovery_records": records,

        "recovered_documents": (
            canonical_recovered
        ),

        "next_stage_verification_pool": (
            canonical_recovered
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
        "DOWNLOAD ENDPOINT RECOVERY RESULT"
    )

    print(
        "=" * 60
    )

    print(
        "Recovery target count:",
        len(
            targets
        ),
    )

    print(
        "Parent request count:",
        parent_request_count,
    )

    print(
        "Parent HTTP success count:",
        parent_http_success_count,
    )

    print(
        "Script request count:",
        script_request_count,
    )

    print(
        "Script HTTP success count:",
        script_http_success_count,
    )

    print(
        "Endpoint candidate count:",
        endpoint_candidate_count,
    )

    print(
        "Probe count:",
        probe_count,
    )

    print(
        "HTML response count:",
        html_response_count,
    )

    print(
        "Network error count:",
        network_error_count,
    )

    print(
        "Filename conflict count:",
        filename_conflict_count,
    )

    print(
        "Unrelated endpoint count:",
        unrelated_endpoint_count,
    )

    print(
        "Identity-not-bound count:",
        identity_not_bound_count,
    )

    print(
        "Payload collision record count:",
        payload_collision_count,
    )

    print(
        "Payload collision group count:",
        collision_group_count,
    )

    print(
        "Canonical recovered document count:",
        len(
            canonical_recovered
        ),
    )

    # ========================================================
    # RECOVERED
    # ========================================================

    if canonical_recovered:

        print()

        print(
            "RECOVERED ATTACHMENTS"
        )

        print(
            "-" * 60
        )

        for index, item in enumerate(
            canonical_recovered,
            start=1,
        ):

            best_probe = (
                item.get(
                    "best_probe"
                )
                or {}
            )

            print(
                f"[{index}]",
                item.get(
                    "parent_region"
                ),
            )

            print(
                "Label:",
                item.get(
                    "child_label"
                ),
            )

            print(
                "Identity:",
                item.get(
                    "attachment_identity"
                ),
            )

            print(
                "URL:",
                best_probe.get(
                    "final_url"
                )
                or best_probe.get(
                    "requested_url"
                ),
            )

            print(
                "Document type:",
                best_probe.get(
                    "document_type"
                ),
            )

            print(
                "Filename:",
                best_probe.get(
                    "response_filename"
                ),
            )

            print(
                "SHA-256:",
                best_probe.get(
                    "response_sha256"
                ),
            )

            print()

    # ========================================================
    # RESOLUTION
    # ========================================================

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

    recovery_identity_keys = {
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
        for item in canonical_recovered
    }

    all_resolutions_valid = all(
        item.get(
            "resolution"
        )
        in VALID_RESOLUTIONS
        for item in records
    )

    recovered_identity_missing_leakage = sum(
        1
        for item in canonical_recovered
        if not normalize_attachment_identity(
            item.get(
                "attachment_identity"
            )
        )
    )

    recovered_identity_not_bound_leakage = sum(
        1
        for item in canonical_recovered
        if (
            item.get(
                "best_probe"
            )
            or {}
        ).get(
            "identity_bound"
        )
        is not True
    )

    recovered_unrelated_leakage = sum(
        1
        for item in canonical_recovered
        if (
            item.get(
                "best_probe"
            )
            or {}
        ).get(
            "known_unrelated_download"
        )
        is True
    )

    recovered_filename_conflict_leakage = sum(
        1
        for item in canonical_recovered
        if (
            item.get(
                "best_probe"
            )
            or {}
        ).get(
            "filename_identity_conflict"
        )
        is True
    )

    recovered_payload_collision_leakage = sum(
        1
        for item in canonical_recovered
        if item.get(
            "cross_attachment_payload_collision"
        )
        is True
    )

    recovered_html_leakage = sum(
        1
        for item in canonical_recovered
        if (
            item.get(
                "best_probe"
            )
            or {}
        ).get(
            "document_type"
        )
        == "HTML"
    )

    recovered_unsupported_leakage = sum(
        1
        for item in canonical_recovered
        if (
            item.get(
                "best_probe"
            )
            or {}
        ).get(
            "document_type"
        )
        not in SUPPORTED_DOCUMENT_TYPES
    )

    dangjin_network_positive_leakage = sum(
        1
        for item in canonical_recovered
        if (
            "dangjin_network"
            in normalize_space(
                (
                    item.get(
                        "best_probe"
                    )
                    or {}
                ).get(
                    "response_filename"
                )
            ).lower()
            or "dangjin_network"
            in normalize_space(
                (
                    item.get(
                        "best_probe"
                    )
                    or {}
                ).get(
                    "final_url"
                )
            ).lower()
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

        "K-stage input parsed": (
            isinstance(
                input_data,
                dict,
            )
        ),

        "recovery targets loaded": (
            len(
                targets
            )
            > 0
        ),

        "attachment identity only": (
            output_data[
                "method"
            ][
                "attachment_identity_only"
            ]
            is True
        ),

        "parent session priming enabled": (
            output_data[
                "method"
            ][
                "parent_session_priming"
            ]
            is True
        ),

        "Referer probe enabled": (
            output_data[
                "method"
            ][
                "referer_probe"
            ]
            is True
        ),

        "parent HTML analysis enabled": (
            output_data[
                "method"
            ][
                "parent_html_analysis"
            ]
            is True
        ),

        "inline javascript analysis enabled": (
            output_data[
                "method"
            ][
                "inline_javascript_analysis"
            ]
            is True
        ),

        "external javascript analysis enabled": (
            output_data[
                "method"
            ][
                "external_javascript_analysis"
            ]
            is True
        ),

        "fn_egov_downFile analysis enabled": (
            output_data[
                "method"
            ][
                "fn_egov_downFile_analysis"
            ]
            is True
        ),

        "identity-bound endpoint required": (
            output_data[
                "method"
            ][
                "identity_bound_endpoint_only"
            ]
            is True
        ),

        "generic parameter injection disabled": (
            output_data[
                "method"
            ][
                "generic_download_parameter_injection_allowed"
            ]
            is False
        ),

        "known unrelated download guard enabled": (
            output_data[
                "method"
            ][
                "known_unrelated_download_guard"
            ]
            is True
        ),

        "filename identity guard enabled": (
            output_data[
                "method"
            ][
                "filename_identity_guard"
            ]
            is True
        ),

        "response SHA-256 enabled": (
            output_data[
                "method"
            ][
                "response_sha256_enabled"
            ]
            is True
        ),

        "cross attachment payload collision guard enabled": (
            output_data[
                "method"
            ][
                "cross_attachment_payload_collision_guard"
            ]
            is True
        ),

        "all recovery record resolutions valid": (
            all_resolutions_valid
        ),

        "canonical recovered identities unique": (
            len(
                recovery_identity_keys
            )
            == len(
                canonical_recovered
            )
        ),

        "recovered identity missing leakage zero": (
            recovered_identity_missing_leakage
            == 0
        ),

        "recovered identity-not-bound leakage zero": (
            recovered_identity_not_bound_leakage
            == 0
        ),

        "recovered unrelated endpoint leakage zero": (
            recovered_unrelated_leakage
            == 0
        ),

        "recovered filename conflict leakage zero": (
            recovered_filename_conflict_leakage
            == 0
        ),

        "recovered payload collision leakage zero": (
            recovered_payload_collision_leakage
            == 0
        ),

        "HTML recovered document leakage zero": (
            recovered_html_leakage
            == 0
        ),

        "unsupported recovered document leakage zero": (
            recovered_unsupported_leakage
            == 0
        ),

        "dangjin network false-positive leakage zero": (
            dangjin_network_positive_leakage
            == 0
        ),

        "next-stage pool final positive prohibited": all(
            item.get(
                "final_positive"
            )
            is False
            for item in canonical_recovered
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
        "Recovered identity missing leakage:",
        recovered_identity_missing_leakage,
    )

    print(
        "Recovered identity-not-bound leakage:",
        recovered_identity_not_bound_leakage,
    )

    print(
        "Recovered unrelated endpoint leakage:",
        recovered_unrelated_leakage,
    )

    print(
        "Recovered filename conflict leakage:",
        recovered_filename_conflict_leakage,
    )

    print(
        "Recovered payload collision leakage:",
        recovered_payload_collision_leakage,
    )

    print(
        "HTML recovered document leakage:",
        recovered_html_leakage,
    )

    print(
        "Dangjin network false-positive leakage:",
        dangjin_network_positive_leakage,
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
            "gazette attachment download endpoint recovery "
            "regression failed"
        )


if __name__ == "__main__":
    main()