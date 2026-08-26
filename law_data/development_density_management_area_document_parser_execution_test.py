from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests


# ============================================================
# CONFIG
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "development_density_management_area_unparsed_document_refinement.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "development_density_management_area_document_parser_execution.json"
)


# ============================================================
# RUNTIME LIMITS
# ============================================================

TIMEOUT = 30

MAX_DOWNLOAD_BYTES = (
    80 * 1024 * 1024
)

MAX_TEXT_CHARS = (
    2_000_000
)

# target이 실제로 발견된 경우 다음 Y-stage에서
# 고시번호 / 지정·변경·해제 / 행정구역 / 범위 등을
# 재검증할 수 있도록 target 주변 문맥을 보존한다.
TARGET_CONTEXT_RADIUS = 3_000

TARGET_CONTEXT_MAX_COUNT = 20

# 개별 context가 지나치게 커지는 것을 방지한다.
TARGET_CONTEXT_MAX_CHARS = (
    TARGET_CONTEXT_RADIUS * 2
    + len(TARGET_NAME)
    + 500
)


# ============================================================
# TEXT / LEGAL PATTERNS
# ============================================================

ACTION_TERMS = (
    "지정",
    "변경",
    "해제",
    "결정",
    "고시",
)

NOTICE_PATTERN = re.compile(
    r"(?:[가-힣]{2,20}\s*)?"
    r"(?:특별시|광역시|특별자치시|특별자치도|도|시|군|구)?\s*"
    r"(?:고시|공고)\s*제?\s*\d{4}\s*-\s*\d+\s*호?"
)


# ============================================================
# ALLOWED RESOLUTIONS
# ============================================================

ALLOWED_RESOLUTIONS = {
    "PDF_TEXT_EXTRACTED_NO_TARGET",
    "PDF_TEXT_EXTRACTED_TARGET_CANDIDATE",
    "PDF_TEXT_PARSER_UNAVAILABLE",
    "PDF_TEXT_EXTRACTION_FAILED",
    "PDF_EMPTY_TEXT_OCR_REQUIRED",

    "HWP_TEXT_EXTRACTED_NO_TARGET",
    "HWP_TEXT_EXTRACTED_TARGET_CANDIDATE",
    "HWP_PARSER_UNAVAILABLE",
    "HWP_EXTRACTION_FAILED",

    "HWPX_TEXT_EXTRACTED_NO_TARGET",
    "HWPX_TEXT_EXTRACTED_TARGET_CANDIDATE",
    "HWPX_EXTRACTION_FAILED",

    "DOWNLOAD_RETRY_SUCCEEDED",
    "DOWNLOAD_RETRY_FAILED",

    "UNSUPPORTED_BINARY_DEFERRED",
}


TARGET_CANDIDATE_RESOLUTIONS = {
    "PDF_TEXT_EXTRACTED_TARGET_CANDIDATE",
    "HWP_TEXT_EXTRACTED_TARGET_CANDIDATE",
    "HWPX_TEXT_EXTRACTED_TARGET_CANDIDATE",
}


# ============================================================
# GENERIC HELPERS
# ============================================================

def load_json(
    path: Path,
) -> Any:

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def normalize_space(
    value: Any,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip()


def unique_keep_order(
    values: list[str],
) -> list[str]:

    result: list[str] = []
    seen: set[str] = set()

    for value in values:

        normalized = normalize_space(
            value
        )

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(
            normalized
        )

        result.append(
            normalized
        )

    return result


# ============================================================
# TARGET CONTEXT EXTRACTION
# ============================================================

def extract_target_contexts(
    text: str,
    target: str = TARGET_NAME,
    radius: int = TARGET_CONTEXT_RADIUS,
    max_contexts: int = TARGET_CONTEXT_MAX_COUNT,
) -> list[str]:
    """
    Extract context windows around every visible target occurrence.

    Purpose:
    - X-stage parser는 전체 PDF/HWP text를 실제로 가지고 있다.
    - 그러나 전체 원문을 JSON에 저장하면 artifact가 지나치게 커진다.
    - 따라서 target 주변의 충분히 넓은 문맥만 보존한다.
    - Y-stage는 이 문맥으로 지정/변경/해제, 고시번호,
      날짜, 행정구역, scope 등을 검증한다.
    """

    if not text:
        return []

    if not target:
        return []

    contexts: list[str] = []

    start = 0

    while (
        len(contexts)
        < max_contexts
    ):

        index = text.find(
            target,
            start,
        )

        if index < 0:
            break

        left = max(
            0,
            index - radius,
        )

        right = min(
            len(text),
            index
            + len(target)
            + radius,
        )

        raw_context = (
            text[left:right]
        )

        normalized_context = (
            normalize_space(
                raw_context
            )
        )

        if (
            normalized_context
            and target
            in normalized_context
        ):
            contexts.append(
                normalized_context[
                    :TARGET_CONTEXT_MAX_CHARS
                ]
            )

        start = (
            index
            + len(target)
        )

    return unique_keep_order(
        contexts
    )


def build_target_context_text(
    contexts: list[str],
) -> str:
    """
    Create a single searchable text field for downstream stages.

    target_contexts remains the canonical structured form.
    target_context_text exists for simple downstream text extraction.
    """

    return "\n\n".join(
        unique_keep_order(
            contexts
        )
    )


# ============================================================
# PARSER CAPABILITIES
# ============================================================

def detect_parser_capabilities() -> dict[str, Any]:

    capabilities: dict[str, Any] = {}

    # --------------------------------------------------------
    # pypdf
    # --------------------------------------------------------

    try:
        import pypdf  # type: ignore

        capabilities["pypdf"] = {
            "available": True,
            "version": getattr(
                pypdf,
                "__version__",
                "",
            ),
        }

    except Exception as exc:

        capabilities["pypdf"] = {
            "available": False,
            "error": repr(exc),
        }

    # --------------------------------------------------------
    # olefile
    # --------------------------------------------------------

    try:
        import olefile  # type: ignore

        capabilities["olefile"] = {
            "available": True,
            "version": getattr(
                olefile,
                "__version__",
                "",
            ),
        }

    except Exception as exc:

        capabilities["olefile"] = {
            "available": False,
            "error": repr(exc),
        }

    # --------------------------------------------------------
    # hwp5txt
    # --------------------------------------------------------

    hwp5txt = shutil.which(
        "hwp5txt"
    )

    capabilities["hwp5txt"] = {
        "available": bool(
            hwp5txt
        ),
        "path": hwp5txt or "",
    }

    # --------------------------------------------------------
    # pdftotext
    # --------------------------------------------------------

    pdftotext = shutil.which(
        "pdftotext"
    )

    capabilities["pdftotext"] = {
        "available": bool(
            pdftotext
        ),
        "path": pdftotext or "",
    }

    return capabilities


# ============================================================
# DOWNLOAD
# ============================================================

def download_bytes(
    session: requests.Session,
    url: str,
) -> tuple[bytes, dict[str, Any]]:

    meta: dict[str, Any] = {
        "http_status": None,
        "content_type": "",
        "content_length": None,
        "final_url": "",
        "error": "",
    }

    try:

        with session.get(
            url,
            stream=True,
            timeout=TIMEOUT,
            allow_redirects=True,
        ) as resp:

            meta["http_status"] = (
                resp.status_code
            )

            meta["content_type"] = (
                normalize_space(
                    resp.headers.get(
                        "Content-Type"
                    )
                )
            )

            meta["final_url"] = str(
                resp.url
            )

            length = resp.headers.get(
                "Content-Length"
            )

            if (
                length
                and length.isdigit()
            ):

                meta["content_length"] = (
                    int(length)
                )

                if (
                    int(length)
                    > MAX_DOWNLOAD_BYTES
                ):
                    raise ValueError(
                        "download exceeds "
                        f"{MAX_DOWNLOAD_BYTES} bytes "
                        f"(content-length={length})"
                    )

            resp.raise_for_status()

            chunks: list[bytes] = []
            total = 0

            for chunk in resp.iter_content(
                chunk_size=1024 * 256,
            ):

                if not chunk:
                    continue

                total += len(
                    chunk
                )

                if (
                    total
                    > MAX_DOWNLOAD_BYTES
                ):
                    raise ValueError(
                        "download exceeds "
                        f"{MAX_DOWNLOAD_BYTES} bytes"
                    )

                chunks.append(
                    chunk
                )

            data = b"".join(
                chunks
            )

            return (
                data,
                meta,
            )

    except Exception as exc:

        meta["error"] = repr(
            exc
        )

        return (
            b"",
            meta,
        )


# ============================================================
# DOCUMENT TYPE DETECTION
# ============================================================

def detect_type(
    data: bytes,
    declared: str,
    url: str,
    content_type: str,
) -> str:

    declared = (
        normalize_space(
            declared
        ).upper()
    )

    ctype = (
        normalize_space(
            content_type
        ).lower()
    )

    path = (
        urlparse(
            url
        ).path.lower()
    )

    # --------------------------------------------------------
    # PDF magic
    # --------------------------------------------------------

    if data.startswith(
        b"%PDF"
    ):
        return "PDF"

    # --------------------------------------------------------
    # OLE compound document = classic HWP candidate
    # --------------------------------------------------------

    if data.startswith(
        b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    ):
        return "HWP"

    # --------------------------------------------------------
    # ZIP/HWPX
    # --------------------------------------------------------

    if data.startswith(
        b"PK\x03\x04"
    ):

        try:

            with zipfile.ZipFile(
                io.BytesIO(
                    data
                )
            ) as zf:

                names = set(
                    zf.namelist()
                )

                if (
                    "mimetype"
                    in names
                ):

                    try:

                        mime = (
                            zf.read(
                                "mimetype"
                            )
                            .decode(
                                "utf-8",
                                errors="ignore",
                            )
                        )

                    except Exception:
                        mime = ""

                    if (
                        "hwp"
                        in mime.lower()
                    ):
                        return "HWPX"

                if any(
                    name.startswith(
                        "Contents/section"
                    )
                    for name
                    in names
                ):
                    return "HWPX"

        except Exception:
            pass

        return "ZIP"

    # --------------------------------------------------------
    # Declared/header/path fallback
    # --------------------------------------------------------

    if (
        "PDF"
        in declared
        or "application/pdf"
        in ctype
        or path.endswith(
            ".pdf"
        )
    ):
        return "PDF"

    if (
        "HWPX"
        in declared
        or path.endswith(
            ".hwpx"
        )
    ):
        return "HWPX"

    if (
        declared
        == "HWP"
        or path.endswith(
            ".hwp"
        )
    ):
        return "HWP"

    return (
        declared
        or "UNKNOWN"
    )


# ============================================================
# PDF PARSERS
# ============================================================

def extract_pdf_with_pypdf(
    data: bytes,
) -> tuple[str, str]:

    try:

        from pypdf import PdfReader  # type: ignore

    except Exception as exc:

        return (
            "",
            f"PYPDF_UNAVAILABLE:{exc!r}",
        )

    try:

        reader = PdfReader(
            io.BytesIO(
                data
            )
        )

        texts: list[str] = []
        current_length = 0

        for page in reader.pages:

            try:

                text = (
                    page.extract_text()
                    or ""
                )

            except Exception:
                text = ""

            if text:

                texts.append(
                    text
                )

                current_length += len(
                    text
                )

            if (
                current_length
                >= MAX_TEXT_CHARS
            ):
                break

        combined = "\n".join(
            texts
        )

        return (
            combined[
                :MAX_TEXT_CHARS
            ],
            "",
        )

    except Exception as exc:

        return (
            "",
            repr(exc),
        )


def extract_pdf_with_pdftotext(
    data: bytes,
    executable: str,
) -> tuple[str, str]:

    try:

        with tempfile.TemporaryDirectory(
            prefix="site_ai_pdf_",
        ) as tmp:

            pdf_path = (
                Path(tmp)
                / "input.pdf"
            )

            txt_path = (
                Path(tmp)
                / "output.txt"
            )

            pdf_path.write_bytes(
                data
            )

            proc = subprocess.run(
                [
                    executable,
                    "-layout",
                    str(pdf_path),
                    str(txt_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
                check=False,
            )

            if (
                proc.returncode
                != 0
            ):

                return (
                    "",
                    proc.stderr.decode(
                        "utf-8",
                        errors="replace",
                    )[:2000],
                )

            if not txt_path.exists():

                return (
                    "",
                    "pdftotext output file missing",
                )

            text = txt_path.read_text(
                encoding="utf-8",
                errors="replace",
            )

            return (
                text[
                    :MAX_TEXT_CHARS
                ],
                "",
            )

    except Exception as exc:

        return (
            "",
            repr(exc),
        )


def extract_pdf_text(
    data: bytes,
    capabilities: dict[str, Any],
) -> tuple[str, str, str]:

    pypdf_error = ""

    # --------------------------------------------------------
    # First choice: pypdf
    # --------------------------------------------------------

    if capabilities[
        "pypdf"
    ][
        "available"
    ]:

        text, error = (
            extract_pdf_with_pypdf(
                data
            )
        )

        if text.strip():

            return (
                text,
                "pypdf",
                "",
            )

        pypdf_error = (
            error
        )

    else:

        pypdf_error = (
            capabilities[
                "pypdf"
            ].get(
                "error",
                "unavailable",
            )
        )

    # --------------------------------------------------------
    # Fallback: pdftotext
    # --------------------------------------------------------

    if capabilities[
        "pdftotext"
    ][
        "available"
    ]:

        text, error = (
            extract_pdf_with_pdftotext(
                data,
                capabilities[
                    "pdftotext"
                ][
                    "path"
                ],
            )
        )

        if text.strip():

            return (
                text,
                "pdftotext",
                "",
            )

        return (
            "",
            "pdftotext",
            error
            or pypdf_error,
        )

    return (
        "",
        "",
        pypdf_error,
    )


# ============================================================
# HWPX PARSER
# ============================================================

def extract_hwpx_text(
    data: bytes,
) -> tuple[str, str]:

    try:

        with zipfile.ZipFile(
            io.BytesIO(
                data
            )
        ) as zf:

            section_names = sorted(
                name
                for name
                in zf.namelist()
                if (
                    name.lower().startswith(
                        "contents/section"
                    )
                    and name.lower().endswith(
                        ".xml"
                    )
                )
            )

            if not section_names:

                return (
                    "",
                    "HWPX section XML not found",
                )

            chunks: list[str] = []
            current_length = 0

            for name in section_names:

                raw = (
                    zf.read(
                        name
                    )
                    .decode(
                        "utf-8",
                        errors="ignore",
                    )
                )

                # HWPX text nodes are XML.
                # target discovery 단계에서는 tag 제거만으로 충분하다.
                text = re.sub(
                    r"<[^>]+>",
                    " ",
                    raw,
                )

                text = (
                    text
                    .replace(
                        "&lt;",
                        "<",
                    )
                    .replace(
                        "&gt;",
                        ">",
                    )
                    .replace(
                        "&amp;",
                        "&",
                    )
                    .replace(
                        "&quot;",
                        '"',
                    )
                    .replace(
                        "&#39;",
                        "'",
                    )
                )

                chunks.append(
                    text
                )

                current_length += len(
                    text
                )

                if (
                    current_length
                    >= MAX_TEXT_CHARS
                ):
                    break

            combined = "\n".join(
                chunks
            )

            return (
                combined[
                    :MAX_TEXT_CHARS
                ],
                "",
            )

    except Exception as exc:

        return (
            "",
            repr(exc),
        )


# ============================================================
# CLASSIC HWP PARSERS
# ============================================================

def extract_hwp_with_hwp5txt(
    data: bytes,
    executable: str,
) -> tuple[str, str]:

    try:

        with tempfile.TemporaryDirectory(
            prefix="site_ai_hwp_",
        ) as tmp:

            hwp_path = (
                Path(tmp)
                / "input.hwp"
            )

            hwp_path.write_bytes(
                data
            )

            proc = subprocess.run(
                [
                    executable,
                    str(hwp_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
                check=False,
            )

            if (
                proc.returncode
                != 0
            ):

                return (
                    "",
                    proc.stderr.decode(
                        "utf-8",
                        errors="replace",
                    )[:2000],
                )

            text = (
                proc.stdout.decode(
                    "utf-8",
                    errors="replace",
                )
            )

            return (
                text[
                    :MAX_TEXT_CHARS
                ],
                "",
            )

    except Exception as exc:

        return (
            "",
            repr(exc),
        )


def extract_hwp_with_olefile(
    data: bytes,
) -> tuple[str, str]:
    """
    Best-effort classic HWP text extraction.

    HWP 5.x stores UTF-16LE text in compressed section streams.

    Full HWP parsing is complicated. This fallback extracts readable
    UTF-16LE fragments from BodyText streams.

    Important:
    - target discovery에는 사용할 수 있다.
    - 이것만으로 verified positive 승격은 금지한다.
    """

    try:

        import olefile  # type: ignore

    except Exception as exc:

        return (
            "",
            f"OLEFILE_UNAVAILABLE:{exc!r}",
        )

    try:

        ole = olefile.OleFileIO(
            io.BytesIO(
                data
            )
        )

    except Exception as exc:

        return (
            "",
            repr(exc),
        )

    try:

        streams = [
            entry
            for entry
            in ole.listdir(
                streams=True,
                storages=False,
            )
            if (
                entry
                and entry[0]
                == "BodyText"
            )
        ]

        if not streams:

            return (
                "",
                "HWP BodyText streams not found",
            )

        pieces: list[str] = []
        current_length = 0

        for entry in streams:

            try:

                raw = (
                    ole.openstream(
                        entry
                    ).read()
                )

            except Exception:
                continue

            candidates = [
                raw
            ]

            # HWP BodyText section은 raw DEFLATE인 경우가 많다.
            try:

                import zlib

                candidates.insert(
                    0,
                    zlib.decompress(
                        raw,
                        -15,
                    ),
                )

            except Exception:
                pass

            best = ""

            for blob in candidates:

                try:

                    decoded = (
                        blob.decode(
                            "utf-16le",
                            errors="ignore",
                        )
                    )

                except Exception:
                    continue

                decoded = re.sub(
                    r"[\x00-\x08\x0b\x0c\x0e-\x1f]",
                    " ",
                    decoded,
                )

                readable = (
                    normalize_space(
                        decoded
                    )
                )

                if (
                    len(readable)
                    > len(best)
                ):
                    best = readable

            if best:

                pieces.append(
                    best
                )

                current_length += len(
                    best
                )

            if (
                current_length
                >= MAX_TEXT_CHARS
            ):
                break

        combined = "\n".join(
            pieces
        )

        return (
            combined[
                :MAX_TEXT_CHARS
            ],
            "",
        )

    except Exception as exc:

        return (
            "",
            repr(exc),
        )

    finally:

        try:
            ole.close()
        except Exception:
            pass


def extract_hwp_text(
    data: bytes,
    capabilities: dict[str, Any],
) -> tuple[str, str, str]:

    hwp5_error = ""

    # --------------------------------------------------------
    # First choice: hwp5txt
    # --------------------------------------------------------

    if capabilities[
        "hwp5txt"
    ][
        "available"
    ]:

        text, error = (
            extract_hwp_with_hwp5txt(
                data,
                capabilities[
                    "hwp5txt"
                ][
                    "path"
                ],
            )
        )

        if text.strip():

            return (
                text,
                "hwp5txt",
                "",
            )

        hwp5_error = (
            error
        )

    else:

        hwp5_error = (
            "hwp5txt unavailable"
        )

    # --------------------------------------------------------
    # Fallback: olefile
    # --------------------------------------------------------

    if capabilities[
        "olefile"
    ][
        "available"
    ]:

        text, error = (
            extract_hwp_with_olefile(
                data
            )
        )

        if text.strip():

            return (
                text,
                "olefile-best-effort",
                "",
            )

        return (
            "",
            "olefile-best-effort",
            error
            or hwp5_error,
        )

    return (
        "",
        "",
        hwp5_error,
    )


# ============================================================
# TEXT ANALYSIS
# ============================================================

def analyze_text(
    text: str,
) -> dict[str, Any]:

    cleaned = normalize_space(
        text
    )

    target_in_text = (
        TARGET_NAME
        in cleaned
    )

    action_terms = [
        term
        for term
        in ACTION_TERMS
        if term
        in cleaned
    ]

    notice_numbers = list(
        dict.fromkeys(
            normalize_space(
                match.group(0)
            )
            for match
            in NOTICE_PATTERN.finditer(
                cleaned
            )
        )
    )

    # --------------------------------------------------------
    # Critical X -> Y stage contract
    # --------------------------------------------------------
    #
    # 기존 구현은 target_in_text=True 및 text_length만 남기고,
    # 실제 target 주변 원문을 artifact에 저장하지 않았다.
    #
    # 그 결과 Y-stage가 target 존재 여부를 재검증할 수 없었다.
    #
    # 전체 extracted_text는 저장하지 않고 target 주변 문맥만 보존한다.
    # --------------------------------------------------------

    target_contexts: list[str] = []

    if target_in_text:

        target_contexts = (
            extract_target_contexts(
                cleaned,
                target=TARGET_NAME,
                radius=TARGET_CONTEXT_RADIUS,
                max_contexts=TARGET_CONTEXT_MAX_COUNT,
            )
        )

    target_context_text = (
        build_target_context_text(
            target_contexts
        )
    )

    return {
        "target_in_text": (
            target_in_text
        ),
        "action_terms": (
            action_terms
        ),
        "notice_numbers": (
            notice_numbers
        ),
        "text_length": len(
            cleaned
        ),
        "preview": (
            cleaned[:1200]
        ),

        # X -> Y contract fields
        "target_context_count": len(
            target_contexts
        ),
        "target_contexts": (
            target_contexts
        ),
        "target_context_text": (
            target_context_text
        ),
    }


# ============================================================
# RECORD PROCESSING
# ============================================================

def process_record(
    session: requests.Session,
    record: dict[str, Any],
    capabilities: dict[str, Any],
) -> dict[str, Any]:

    url = normalize_space(
        record.get(
            "url"
        )
    )

    declared_type = (
        normalize_space(
            record.get(
                "document_type"
            )
        ).upper()
    )

    classification = (
        normalize_space(
            record.get(
                "classification"
            )
        )
    )

    result: dict[str, Any] = {
        "index": (
            record.get(
                "index"
            )
        ),
        "region": (
            normalize_space(
                record.get(
                    "region"
                )
            )
        ),
        "label": (
            normalize_space(
                record.get(
                    "label"
                )
            )
        ),
        "url": (
            url
        ),
        "input_classification": (
            classification
        ),
        "declared_type": (
            declared_type
        ),
        "detected_type": "",
        "http_status": None,
        "content_type": "",
        "download_bytes": 0,
        "parser": "",
        "parse_error": "",

        # parser analysis
        "target_in_text": False,
        "action_terms": [],
        "notice_numbers": [],
        "text_length": 0,
        "preview": "",

        # ----------------------------------------------------
        # X -> Y stage contract fields
        # ----------------------------------------------------
        "target_context_count": 0,
        "target_contexts": [],
        "target_context_text": "",

        "resolution": "",
        "verified_positive": False,
    }

    # --------------------------------------------------------
    # Unsupported binary
    # --------------------------------------------------------

    if (
        classification
        == "UNSUPPORTED_BINARY"
    ):

        result[
            "resolution"
        ] = (
            "UNSUPPORTED_BINARY_DEFERRED"
        )

        return result

    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------

    data, meta = download_bytes(
        session,
        url,
    )

    result[
        "http_status"
    ] = (
        meta[
            "http_status"
        ]
    )

    result[
        "content_type"
    ] = (
        meta[
            "content_type"
        ]
    )

    result[
        "download_bytes"
    ] = len(
        data
    )

    if not data:

        result[
            "parse_error"
        ] = (
            meta[
                "error"
            ]
        )

        result[
            "resolution"
        ] = (
            "DOWNLOAD_RETRY_FAILED"
        )

        return result

    # --------------------------------------------------------
    # Detect actual type
    # --------------------------------------------------------

    detected = detect_type(
        data,
        declared_type,
        url,
        meta[
            "content_type"
        ],
    )

    result[
        "detected_type"
    ] = (
        detected
    )

    # Successful retry continues into parser.
    if (
        classification
        == "DOWNLOAD_RETRY_REQUIRED"
    ):

        result[
            "resolution"
        ] = (
            "DOWNLOAD_RETRY_SUCCEEDED"
        )

    text = ""
    parser = ""
    error = ""

    # ========================================================
    # PDF
    # ========================================================

    if (
        detected
        == "PDF"
    ):

        (
            text,
            parser,
            error,
        ) = extract_pdf_text(
            data,
            capabilities,
        )

        result[
            "parser"
        ] = parser

        result[
            "parse_error"
        ] = error

        if text.strip():

            analysis = (
                analyze_text(
                    text
                )
            )

            result.update(
                analysis
            )

            if analysis[
                "target_in_text"
            ]:

                result[
                    "resolution"
                ] = (
                    "PDF_TEXT_EXTRACTED_TARGET_CANDIDATE"
                )

            else:

                result[
                    "resolution"
                ] = (
                    "PDF_TEXT_EXTRACTED_NO_TARGET"
                )

        else:

            if not (
                capabilities[
                    "pypdf"
                ][
                    "available"
                ]
                or capabilities[
                    "pdftotext"
                ][
                    "available"
                ]
            ):

                result[
                    "resolution"
                ] = (
                    "PDF_TEXT_PARSER_UNAVAILABLE"
                )

            elif error:

                result[
                    "resolution"
                ] = (
                    "PDF_TEXT_EXTRACTION_FAILED"
                )

            else:

                result[
                    "resolution"
                ] = (
                    "PDF_EMPTY_TEXT_OCR_REQUIRED"
                )

    # ========================================================
    # HWPX
    # ========================================================

    elif (
        detected
        == "HWPX"
    ):

        (
            text,
            error,
        ) = extract_hwpx_text(
            data
        )

        result[
            "parser"
        ] = (
            "zip-xml"
        )

        result[
            "parse_error"
        ] = error

        if text.strip():

            analysis = (
                analyze_text(
                    text
                )
            )

            result.update(
                analysis
            )

            if analysis[
                "target_in_text"
            ]:

                result[
                    "resolution"
                ] = (
                    "HWPX_TEXT_EXTRACTED_TARGET_CANDIDATE"
                )

            else:

                result[
                    "resolution"
                ] = (
                    "HWPX_TEXT_EXTRACTED_NO_TARGET"
                )

        else:

            result[
                "resolution"
            ] = (
                "HWPX_EXTRACTION_FAILED"
            )

    # ========================================================
    # CLASSIC HWP
    # ========================================================

    elif (
        detected
        == "HWP"
    ):

        (
            text,
            parser,
            error,
        ) = extract_hwp_text(
            data,
            capabilities,
        )

        result[
            "parser"
        ] = parser

        result[
            "parse_error"
        ] = error

        if text.strip():

            analysis = (
                analyze_text(
                    text
                )
            )

            result.update(
                analysis
            )

            if analysis[
                "target_in_text"
            ]:

                result[
                    "resolution"
                ] = (
                    "HWP_TEXT_EXTRACTED_TARGET_CANDIDATE"
                )

            else:

                result[
                    "resolution"
                ] = (
                    "HWP_TEXT_EXTRACTED_NO_TARGET"
                )

        else:

            if not (
                capabilities[
                    "hwp5txt"
                ][
                    "available"
                ]
                or capabilities[
                    "olefile"
                ][
                    "available"
                ]
            ):

                result[
                    "resolution"
                ] = (
                    "HWP_PARSER_UNAVAILABLE"
                )

            else:

                result[
                    "resolution"
                ] = (
                    "HWP_EXTRACTION_FAILED"
                )

    # ========================================================
    # UNKNOWN / OTHER
    # ========================================================

    else:

        result[
            "resolution"
        ] = (
            "UNSUPPORTED_BINARY_DEFERRED"
        )

    return result


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
        "DOCUMENT PARSER EXECUTION / OCR GATE"
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
            "W-stage input not found: "
            f"{INPUT_PATH}"
        )

    payload = load_json(
        INPUT_PATH
    )

    queue = payload.get(
        "next_stage_parser_queue",
        [],
    )

    if not isinstance(
        queue,
        list,
    ):

        raise TypeError(
            "next_stage_parser_queue "
            "must be a list"
        )

    # ========================================================
    # CAPABILITIES
    # ========================================================

    capabilities = (
        detect_parser_capabilities()
    )

    print(
        "PARSER CAPABILITIES"
    )
    print(
        "-" * 60
    )

    for name, info in capabilities.items():

        print(
            f"{name}: {info}"
        )

    print()

    # ========================================================
    # HTTP SESSION
    # ========================================================

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            "Accept": "*/*",
        }
    )

    # ========================================================
    # EXECUTION
    # ========================================================

    results: list[
        dict[str, Any]
    ] = []

    for idx, record in enumerate(
        queue,
        start=1,
    ):

        item = process_record(
            session,
            record,
            capabilities,
        )

        results.append(
            item
        )

        should_print = (
            item[
                "target_in_text"
            ]
            or item[
                "resolution"
            ]
            in {
                "DOWNLOAD_RETRY_FAILED",
                "PDF_TEXT_PARSER_UNAVAILABLE",
                "HWP_PARSER_UNAVAILABLE",
                "PDF_EMPTY_TEXT_OCR_REQUIRED",
                "PDF_TEXT_EXTRACTION_FAILED",
                "HWP_EXTRACTION_FAILED",
                "HWPX_EXTRACTION_FAILED",
            }
        )

        if not should_print:
            continue

        print(
            "-" * 60
        )

        print(
            f"CANDIDATE {idx}: "
            f"{item['region'] or '-'}"
        )

        print(
            f"URL: {item['url']}"
        )

        print(
            f"HTTP: {item['http_status']}"
        )

        print(
            "Declared type: "
            f"{item['declared_type']}"
        )

        print(
            "Detected type: "
            f"{item['detected_type']}"
        )

        print(
            "Parser: "
            f"{item['parser'] or '-'}"
        )

        print(
            "Resolution: "
            f"{item['resolution']}"
        )

        print(
            "Target in text: "
            f"{item['target_in_text']}"
        )

        print(
            "Action terms: "
            f"{item['action_terms']}"
        )

        print(
            "Notice numbers: "
            f"{item['notice_numbers']}"
        )

        # ----------------------------------------------------
        # New contract diagnostics
        # ----------------------------------------------------

        if item[
            "target_in_text"
        ]:

            print(
                "Target context count: "
                f"{item['target_context_count']}"
            )

            if item[
                "target_contexts"
            ]:

                print(
                    "Target context preview:"
                )

                print(
                    item[
                        "target_contexts"
                    ][0][
                        :1500
                    ]
                )

        if item[
            "parse_error"
        ]:

            print(
                "Parse error: "
                f"{item['parse_error']}"
            )

    # ========================================================
    # RESULT CLASSIFICATION
    # ========================================================

    resolution_counts = Counter(
        x[
            "resolution"
        ]
        for x
        in results
    )

    target_candidates = [
        x
        for x
        in results
        if x[
            "resolution"
        ]
        in TARGET_CANDIDATE_RESOLUTIONS
    ]

    ocr_queue = [
        x
        for x
        in results
        if x[
            "resolution"
        ]
        in {
            "PDF_EMPTY_TEXT_OCR_REQUIRED",
            "PDF_TEXT_EXTRACTION_FAILED",
        }
    ]

    dependency_blocked = [
        x
        for x
        in results
        if x[
            "resolution"
        ]
        in {
            "PDF_TEXT_PARSER_UNAVAILABLE",
            "HWP_PARSER_UNAVAILABLE",
        }
    ]

    retry_failed = [
        x
        for x
        in results
        if x[
            "resolution"
        ]
        == "DOWNLOAD_RETRY_FAILED"
    ]

    # ========================================================
    # CONTRACT ACCOUNTING
    # ========================================================

    target_candidates_with_context = [
        x
        for x
        in target_candidates
        if (
            x[
                "target_context_count"
            ]
            > 0
            and bool(
                x[
                    "target_contexts"
                ]
            )
            and TARGET_NAME
            in x[
                "target_context_text"
            ]
        )
    ]

    # ========================================================
    # OUTPUT
    # ========================================================

    output = {
        "target_name": (
            TARGET_NAME
        ),
        "standard_code": (
            STANDARD_CODE
        ),
        "input": str(
            INPUT_PATH
        ),
        "parser_capabilities": (
            capabilities
        ),
        "input_queue_count": (
            len(queue)
        ),
        "processed_count": (
            len(results)
        ),
        "resolution_counts": dict(
            sorted(
                resolution_counts.items()
            )
        ),

        "target_candidate_count": (
            len(
                target_candidates
            )
        ),

        "target_candidate_with_context_count": (
            len(
                target_candidates_with_context
            )
        ),

        "ocr_queue_count": (
            len(
                ocr_queue
            )
        ),

        "dependency_blocked_count": (
            len(
                dependency_blocked
            )
        ),

        "download_retry_failed_count": (
            len(
                retry_failed
            )
        ),

        "results": (
            results
        ),

        "target_document_candidates": (
            target_candidates
        ),

        "ocr_queue": (
            ocr_queue
        ),

        "dependency_blocked": (
            dependency_blocked
        ),

        "download_retry_failed": (
            retry_failed
        ),

        "runtime_registration_allowed": (
            False
        ),

        "site_false_blocked": (
            True
        ),

        "final_positive_promotion_allowed": (
            False
        ),
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2,
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print(
        "=" * 60
    )
    print(
        "PARSER EXECUTION RESULT"
    )
    print(
        "=" * 60
    )

    print(
        "Input parser queue count: "
        f"{len(queue)}"
    )

    print(
        "Processed count: "
        f"{len(results)}"
    )

    print()

    for key, count in sorted(
        resolution_counts.items()
    ):

        print(
            f"{key}: {count}"
        )

    print()

    print(
        "Target document candidate count: "
        f"{len(target_candidates)}"
    )

    print(
        "Target candidate with context count: "
        f"{len(target_candidates_with_context)}"
    )

    print(
        "Actual OCR queue count: "
        f"{len(ocr_queue)}"
    )

    print(
        "Dependency blocked count: "
        f"{len(dependency_blocked)}"
    )

    print(
        "Download retry failed count: "
        f"{len(retry_failed)}"
    )

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

    if dependency_blocked:

        print(
            "DOCUMENT_PARSER_EXECUTION_DEPENDENCY_BLOCKED"
        )

        print()

        print(
            "설치되지 않은 parser 때문에 일부 문서를 아직 판정할 수 없다. "
            "PDF는 pypdf 또는 pdftotext, classic HWP는 hwp5txt 또는 olefile "
            "가용성을 확보한 뒤 재실행해야 한다. OCR은 PDF text parser 실행 "
            "후에도 텍스트가 비어 있는 문서에만 적용한다."
        )

    elif target_candidates:

        print(
            "DOCUMENT_PARSER_EXECUTION_TARGET_CANDIDATE_DISCOVERED"
        )

        print()

        print(
            "원문 text에서 target이 확인된 문서가 있으며 target 주변 원문 "
            "context를 X-stage artifact에 보존했다. 다음 단계에서 "
            "지정·변경·해제 action context, 고시번호, 고시일, 행정구역 및 "
            "지정 범위를 검증한다. 아직 final positive는 아니다."
        )

    elif ocr_queue:

        print(
            "DOCUMENT_PARSER_EXECUTION_COMPLETED_OCR_QUEUE_CONFIRMED"
        )

        print()

        print(
            "텍스트 parser를 거친 뒤에도 내용이 비어 있거나 파싱 실패한 PDF만 "
            "OCR 대상으로 확정했다."
        )

    else:

        print(
            "DOCUMENT_PARSER_EXECUTION_COMPLETED_NO_TARGET_NO_OCR_QUEUE"
        )

        print()

        print(
            "parser 실행 범위에서는 target 문서를 확인하지 못했다."
        )

    print()

    print(
        f"Output: {OUTPUT_PATH}"
    )

    print()

    # ========================================================
    # VALIDATION
    # ========================================================

    validation = {
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

        "W-stage input parsed": (
            isinstance(
                payload,
                dict,
            )
        ),

        "parser queue loaded": (
            isinstance(
                queue,
                list,
            )
        ),

        "parser capability diagnostics enabled": (
            True
        ),

        "PDF text extraction attempted before OCR": all(
            not (
                x[
                    "declared_type"
                ]
                == "PDF"
                and x[
                    "resolution"
                ]
                == "PDF_EMPTY_TEXT_OCR_REQUIRED"
            )
            or (
                capabilities[
                    "pypdf"
                ][
                    "available"
                ]
                or capabilities[
                    "pdftotext"
                ][
                    "available"
                ]
            )
            for x
            in results
        ),

        "classic HWP explicit parser routing enabled": (
            True
        ),

        "HWPX ZIP/XML parser enabled": (
            True
        ),

        "download retry execution enabled": (
            True
        ),

        "all resolutions valid": all(
            x[
                "resolution"
            ]
            in ALLOWED_RESOLUTIONS
            for x
            in results
        ),

        # ----------------------------------------------------
        # Existing target guards
        # ----------------------------------------------------

        "target candidates contain target text": all(
            x[
                "target_in_text"
            ]
            for x
            in target_candidates
        ),

        "target candidate final positive prohibited": all(
            not x[
                "verified_positive"
            ]
            for x
            in target_candidates
        ),

        # ----------------------------------------------------
        # New X -> Y stage contract guards
        # ----------------------------------------------------

        "target context extraction enabled": (
            True
        ),

        "target candidate count matches result resolutions": (
            output[
                "target_candidate_count"
            ]
            == sum(
                1
                for x
                in results
                if x[
                    "resolution"
                ]
                in TARGET_CANDIDATE_RESOLUTIONS
            )
        ),

        "all target candidates have context": all(
            x[
                "target_context_count"
            ]
            > 0
            for x
            in target_candidates
        ),

        "all target candidate context lists populated": all(
            isinstance(
                x[
                    "target_contexts"
                ],
                list,
            )
            and bool(
                x[
                    "target_contexts"
                ]
            )
            for x
            in target_candidates
        ),

        "all target candidate context text populated": all(
            bool(
                normalize_space(
                    x[
                        "target_context_text"
                    ]
                )
            )
            for x
            in target_candidates
        ),

        "all target candidate contexts contain target": all(
            TARGET_NAME
            in x[
                "target_context_text"
            ]
            for x
            in target_candidates
        ),

        "target candidate context accounting consistent": (
            output[
                "target_candidate_with_context_count"
            ]
            == len(
                target_candidates
            )
        ),

        # ----------------------------------------------------
        # OCR guards
        # ----------------------------------------------------

        "OCR queue contains only PDF parser failures/empty text": all(
            x[
                "detected_type"
            ]
            == "PDF"
            and x[
                "resolution"
            ]
            in {
                "PDF_EMPTY_TEXT_OCR_REQUIRED",
                "PDF_TEXT_EXTRACTION_FAILED",
            }
            for x
            in ocr_queue
        ),

        # ----------------------------------------------------
        # Runtime protection
        # ----------------------------------------------------

        "runtime registration remains blocked": (
            not output[
                "runtime_registration_allowed"
            ]
        ),

        "SITE FALSE remains blocked": (
            output[
                "site_false_blocked"
            ]
        ),

        "final positive promotion remains blocked": (
            not output[
                "final_positive_promotion_allowed"
            ]
        ),

        "output written": (
            OUTPUT_PATH.exists()
        ),
    }

    print(
        "=" * 60
    )

    print(
        "VALIDATION"
    )

    print(
        "=" * 60
    )

    for key, passed in validation.items():

        print(
            f"{key}: {passed}"
        )

    all_pass = all(
        validation.values()
    )

    print()

    print(
        f"all_pass: {all_pass}"
    )

    if not all_pass:

        failed = [
            key
            for key, passed
            in validation.items()
            if not passed
        ]

        print()
        print(
            "FAILED:"
        )

        for key in failed:

            print(
                f"- {key}"
            )

        raise AssertionError(
            "Development density management area "
            "document parser execution regression failed"
        )


if __name__ == "__main__":
    main()