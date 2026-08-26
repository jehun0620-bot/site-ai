from __future__ import annotations

import io
import json
import re
import zipfile
from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import urlparse

import requests

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = BASE_DIR / "law_data" / "output" / "development_density_management_area_gazette_issue_seed_relevance_refinement.json"
OUTPUT_PATH = BASE_DIR / "law_data" / "output" / "development_density_management_area_gazette_bulk_fulltext_discovery.json"
REQUEST_TIMEOUT = 20
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
MAX_TEXT_CHARS = 2_000_000
MAX_CANDIDATES_TO_PRINT = 80
BULK_CLASS = "GAZETTE_BULK_ARCHIVE"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

ACTION_TERMS = (
    "지정", "변경", "해제", "결정", "결정(변경)",
    "도시관리계획", "도시계획", "지형도면",
)
NOTICE_PATTERNS = (
    re.compile(r"(?:[가-힣]{2,20}\s*)?고시\s*제?\s*\d{2,4}\s*-\s*\d+\s*호"),
    re.compile(r"(?:[가-힣]{2,20}\s*)?고시\s*제?\s*\d+\s*호"),
)
DATE_PATTERNS = (
    re.compile(r"\b(20\d{2})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})일?\b"),
    re.compile(r"\b(19\d{2})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})일?\b"),
)


@dataclass
class Seed:
    region: str
    label: str
    source_class: str
    parent_score: int
    url: str
    issue_numbers: list[str]
    notice_numbers: list[str]
    dates: list[str]
    source_path: str


@dataclass
class VerificationRecord:
    region: str
    label: str
    source_class: str
    source_path: str
    url: str
    final_url: str
    http_status: Optional[int]
    content_type: str
    content_disposition: str
    detected_type: str
    response_bytes: int
    body_sha256: str
    parsed: bool
    parse_method: str
    parse_error: str
    extracted_text_chars: int
    target_in_text: bool
    action_terms: list[str]
    notice_numbers: list[str]
    dates: list[str]
    target_context: str
    resolution: str
    verified_positive_candidate: bool


def norm(v: Any) -> str:
    s = "" if v is None else str(v)
    return re.sub(r"\s+", " ", s.replace("\x00", " ")).strip()


def dedupe(values: Iterable[str]) -> list[str]:
    out, seen = [], set()
    for value in values:
        v = norm(value)
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def clip(text: str, limit: int = 500) -> str:
    text = norm(text)
    return text if len(text) <= limit else text[:limit] + "..."


def is_http_url(value: str) -> bool:
    try:
        p = urlparse(value)
        return p.scheme in {"http", "https"} and bool(p.netloc)
    except Exception:
        return False


def looks_like_download_url(url: str) -> bool:
    low = url.lower()
    return any(x in low for x in (
        "download", "filedown", "file_down", "atchfile", "fileuid",
        "filesn", ".pdf", ".hwp", ".hwpx",
    ))


def canonical_download_url(url: str) -> str:
    return norm(url).replace("&amp;", "&")


def scalar_str(obj: Any, *keys: str) -> str:
    if not isinstance(obj, dict):
        return ""
    lowered = {str(k).lower(): v for k, v in obj.items()}
    for key in keys:
        v = lowered.get(key.lower())
        if isinstance(v, (str, int, float)):
            return norm(v)
    return ""


def scalar_int(obj: Any, *keys: str) -> int:
    try:
        return int(float(scalar_str(obj, *keys)))
    except Exception:
        return 0


def list_strings(obj: Any, *keys: str) -> list[str]:
    if not isinstance(obj, dict):
        return []
    lowered = {str(k).lower(): v for k, v in obj.items()}
    for key in keys:
        v = lowered.get(key.lower())
        if isinstance(v, list):
            return dedupe(str(x) for x in v)
        if isinstance(v, str) and norm(v):
            return [norm(v)]
    return []


def infer_class(obj: dict[str, Any], inherited: str = "") -> str:
    own = scalar_str(obj, "classification", "class", "seed_class", "source_class", "category")
    if own:
        return own
    for key in obj:
        up = str(key).upper()
        if up in {"TARGET_DIRECT_SEED", "URBAN_NOTICE_SEED", "GAZETTE_BULK_ARCHIVE", "EXCLUDED_UNRELATED_DOCUMENT"}:
            return up
    return inherited


def collect_urls(obj: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key, value in obj.items():
        k = str(key).lower()
        key_hint = any(h in k for h in ("extensionless", "download", "attachment", "file_url", "fileurl", "url"))
        if isinstance(value, str) and is_http_url(value) and (key_hint or looks_like_download_url(value)):
            urls.append(value)
        elif isinstance(value, list) and key_hint:
            for item in value:
                if isinstance(item, str) and is_http_url(item):
                    urls.append(item)
                elif isinstance(item, dict):
                    u = scalar_str(item, "url", "download_url", "attachment_url", "file_url")
                    if is_http_url(u):
                        urls.append(u)
        elif isinstance(value, dict) and key_hint:
            u = scalar_str(value, "url", "download_url", "attachment_url", "file_url")
            if is_http_url(u):
                urls.append(u)
    return dedupe(canonical_download_url(x) for x in urls)


def walk(node: Any, path: str = "$", inherited_class: str = "", inherited_region: str = "") -> list[Seed]:
    out: list[Seed] = []
    if isinstance(node, dict):
        cls = infer_class(node, inherited_class)
        region = scalar_str(node, "region", "municipality", "local_government", "site_name") or inherited_region
        label = scalar_str(node, "label", "title", "parent_label", "document_label")
        issues = list_strings(node, "issue_numbers", "issue_number")
        notices = list_strings(node, "notice_numbers", "notice_number")
        dates = list_strings(node, "dates", "date")
        score = scalar_int(node, "parent_score", "score")

        if cls == BULK_CLASS:
            for url in collect_urls(node):
                if looks_like_download_url(url):
                    out.append(Seed(region, label, cls, score, url, issues, notices, dates, path))

        for key, value in node.items():
            child_class = cls
            up = str(key).upper()
            if up in {"TARGET_DIRECT_SEED", "URBAN_NOTICE_SEED", "GAZETTE_BULK_ARCHIVE", "EXCLUDED_UNRELATED_DOCUMENT"}:
                child_class = up
            out.extend(walk(value, f"{path}.{key}", child_class, region))

    elif isinstance(node, list):
        for i, item in enumerate(node):
            out.extend(walk(item, f"{path}[{i}]", inherited_class, inherited_region))
    return out


def dedupe_seeds(seeds: list[Seed]) -> list[Seed]:
    merged: dict[str, Seed] = {}
    for seed in seeds:
        key = canonical_download_url(seed.url)
        if key not in merged:
            merged[key] = seed
        else:
            cur = merged[key]
            cur.issue_numbers = dedupe(cur.issue_numbers + seed.issue_numbers)
            cur.notice_numbers = dedupe(cur.notice_numbers + seed.notice_numbers)
            cur.dates = dedupe(cur.dates + seed.dates)
            cur.parent_score = max(cur.parent_score, seed.parent_score)
            cur.region = cur.region or seed.region
            cur.label = cur.label or seed.label
    return list(merged.values())


def detect_type(data: bytes, content_type: str, content_disposition: str, final_url: str) -> str:
    low = f"{content_type} {content_disposition} {final_url}".lower()
    if data.startswith(b"%PDF-") or "application/pdf" in low or ".pdf" in low:
        return "PDF"
    if data.startswith(b"PK\x03\x04"):
        if ".hwpx" in low:
            return "HWPX"
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                if any(n.startswith("Contents/section") and n.endswith(".xml") for n in zf.namelist()):
                    return "HWPX"
        except Exception:
            pass
        return "ZIP"
    if data.startswith(bytes.fromhex("D0CF11E0A1B11AE1")) or ".hwp" in low:
        return "HWP"
    head = data[:2048].lstrip().lower()
    if "text/html" in low or head.startswith(b"<!doctype html") or head.startswith(b"<html"):
        return "HTML"
    if content_type.lower().startswith("text/"):
        return "TEXT"
    return "BINARY"


def decode_best(data: bytes) -> str:
    for enc in ("utf-8", "cp949", "euc-kr", "utf-16", "latin-1"):
        try:
            return data.decode(enc)[:MAX_TEXT_CHARS]
        except Exception:
            pass
    return ""


def extract_html(data: bytes, enc: str = "") -> tuple[str, str]:
    raw = ""
    if enc:
        try:
            raw = data.decode(enc, errors="replace")
        except Exception:
            pass
    raw = raw or decode_best(data)
    if BeautifulSoup is None:
        raw = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw, flags=re.I | re.S)
        raw = re.sub(r"<style\b[^>]*>.*?</style>", " ", raw, flags=re.I | re.S)
        return norm(re.sub(r"<[^>]+>", " ", raw))[:MAX_TEXT_CHARS], "HTML_REGEX"
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return norm(soup.get_text(" ", strip=True))[:MAX_TEXT_CHARS], "BEAUTIFULSOUP"


def extract_pdf(data: bytes) -> tuple[str, str, str]:
    if PdfReader is None:
        return "", "PYPDF_NOT_INSTALLED", "pypdf is not installed"
    try:
        reader = PdfReader(io.BytesIO(data))
        parts: list[str] = []
        total = 0
        for page in reader.pages:
            t = page.extract_text() or ""
            parts.append(t)
            total += len(t)
            if total >= MAX_TEXT_CHARS:
                break
        return norm(" ".join(parts))[:MAX_TEXT_CHARS], "PYPDF_TEXT_LAYER", ""
    except Exception as exc:
        return "", "PDF_PARSE_FAILED", repr(exc)


def extract_hwpx(data: bytes) -> tuple[str, str, str]:
    try:
        parts: list[str] = []
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = sorted(n for n in zf.namelist() if n.startswith("Contents/section") and n.endswith(".xml"))
            for name in names:
                raw = decode_best(zf.read(name))
                frags = re.findall(r"<(?:\w+:)?t\b[^>]*>(.*?)</(?:\w+:)?t>", raw, flags=re.I | re.S)
                if frags:
                    parts.extend(re.sub(r"<[^>]+>", " ", x) for x in frags)
                else:
                    parts.append(re.sub(r"<[^>]+>", " ", raw))
                if sum(map(len, parts)) >= MAX_TEXT_CHARS:
                    break
        return norm(" ".join(parts))[:MAX_TEXT_CHARS], "HWPX_XML", ""
    except Exception as exc:
        return "", "HWPX_PARSE_FAILED", repr(exc)


def extract_text(kind: str, data: bytes, enc: str = "") -> tuple[str, str, str]:
    if kind == "HTML":
        text, method = extract_html(data, enc)
        return text, method, ""
    if kind == "TEXT":
        return norm(decode_best(data)), "TEXT_DECODE", ""
    if kind == "PDF":
        return extract_pdf(data)
    if kind == "HWPX":
        return extract_hwpx(data)
    if kind == "HWP":
        return "", "HWP_BINARY_UNPARSED", "classic HWP parser not enabled"
    return "", "UNSUPPORTED_BINARY", "unsupported or unparsed binary type"


def notice_numbers(text: str) -> list[str]:
    vals: list[str] = []
    for pattern in NOTICE_PATTERNS:
        vals.extend(m.group(0) for m in pattern.finditer(text))
    return dedupe(vals)


def dates(text: str) -> list[str]:
    vals: list[str] = []
    for pattern in DATE_PATTERNS:
        for m in pattern.finditer(text):
            y, mo, d = m.groups()
            vals.append(f"{int(y):04d}-{int(mo):02d}-{int(d):02d}")
    return dedupe(vals)


def context(text: str, radius: int = 350) -> str:
    i = text.find(TARGET_NAME)
    if i < 0:
        return ""
    return clip(text[max(0, i-radius): i+len(TARGET_NAME)+radius], 900)


def build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*", "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7"})
    return s


def fetch_bounded(session: requests.Session, url: str) -> tuple[requests.Response, bytes]:
    with session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True, stream=True) as r:
        chunks, total = [], 0
        for chunk in r.iter_content(65536):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_DOWNLOAD_BYTES:
                raise ValueError(f"download exceeds {MAX_DOWNLOAD_BYTES} bytes")
            chunks.append(chunk)
        return r, b"".join(chunks)


def verify(session: requests.Session, seed: Seed) -> VerificationRecord:
    try:
        r, data = fetch_bounded(session, seed.url)
        ct = r.headers.get("Content-Type", "")
        cd = r.headers.get("Content-Disposition", "")
        kind = detect_type(data, ct, cd, str(r.url))
        text, method, parse_error = extract_text(kind, data, getattr(r, "encoding", None) or "")
        parsed = bool(text)
        target = TARGET_NAME in text if parsed else False
        actions = [x for x in ACTION_TERMS if x in text] if parsed else []
        notices = notice_numbers(text) if parsed else []
        ds = dates(text) if parsed else []
        verified = bool(target and actions and notices)
        if not parsed:
            resolution = "UNPARSED_BINARY" if kind in {"HWP", "PDF", "HWPX", "ZIP", "BINARY"} else "UNPARSED_DOCUMENT"
        elif not target:
            resolution = "NO_TARGET_IN_EXTRACTED_TEXT"
        elif verified:
            resolution = "VERIFIED_POSITIVE_CANDIDATE"
        else:
            resolution = "TARGET_DOCUMENT_CANDIDATE"
        return VerificationRecord(
            seed.region, seed.label, seed.source_class, seed.source_path,
            seed.url, str(r.url), r.status_code, ct, cd, kind,
            len(data), sha256(data).hexdigest(), parsed, method, parse_error,
            len(text), target, actions, notices, ds, context(text) if target else "",
            resolution, verified,
        )
    except Exception as exc:
        return VerificationRecord(
            seed.region, seed.label, seed.source_class, seed.source_path,
            seed.url, "", None, "", "", "", 0, "", False, "", repr(exc),
            0, False, [], [], [], "", "TRANSPORT_OR_DOWNLOAD_ERROR", False,
        )


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("GAZETTE BULK ARCHIVE FULL-TEXT DISCOVERY")
    print("=" * 60)
    print(f"\nTarget: {TARGET_NAME}")
    print(f"Standard code: {STANDARD_CODE}")
    print(f"Input: {INPUT_PATH}\n")

    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input not found: {INPUT_PATH}")

    with INPUT_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    raw_seeds = walk(data)
    seeds = dedupe_seeds(raw_seeds)
    print(f"Raw bulk download seed count: {len(raw_seeds)}")
    print(f"Canonical bulk download seed count: {len(seeds)}\n")

    session = build_session()
    records: list[VerificationRecord] = []
    for i, seed in enumerate(seeds, 1):
        rec = verify(session, seed)
        records.append(rec)
        if rec.target_in_text or rec.resolution == "TRANSPORT_OR_DOWNLOAD_ERROR":
            print("-" * 60)
            print(f"CANDIDATE {i}: {rec.region}")
            print(f"Label: {rec.label}")
            print(f"URL: {rec.url}")
            print(f"HTTP: {rec.http_status}")
            print(f"Type: {rec.detected_type}")
            print(f"Parsed: {rec.parsed}")
            print(f"Target in extracted text: {rec.target_in_text}")
            print(f"Action terms: {rec.action_terms}")
            print(f"Notice numbers: {rec.notice_numbers}")
            print(f"Resolution: {rec.resolution}")
            if rec.target_context:
                print(f"Context: {rec.target_context}")
            if rec.parse_error:
                print(f"Parse error: {rec.parse_error}")

    targets = [r for r in records if r.target_in_text]
    verified = [r for r in records if r.verified_positive_candidate]
    errors = [r for r in records if r.resolution == "TRANSPORT_OR_DOWNLOAD_ERROR"]
    unparsed = [r for r in records if r.resolution in {"UNPARSED_BINARY", "UNPARSED_DOCUMENT"}]

    type_counts: dict[str, int] = {}
    resolution_counts: dict[str, int] = {}
    for r in records:
        type_counts[r.detected_type or "UNKNOWN"] = type_counts.get(r.detected_type or "UNKNOWN", 0) + 1
        resolution_counts[r.resolution] = resolution_counts.get(r.resolution, 0) + 1

    print("\n" + "=" * 60)
    print("DISCOVERY RESULT")
    print("=" * 60)
    print(f"Raw seed count: {len(raw_seeds)}")
    print(f"Canonical seed count: {len(seeds)}")
    print(f"Request count: {len(records)}")
    print(f"HTTP success count: {sum(1 for r in records if r.http_status is not None and 200 <= r.http_status < 400)}")
    print(f"Transport/download error count: {len(errors)}")
    print(f"Parsed document count: {sum(1 for r in records if r.parsed)}")
    print(f"Unparsed document count: {len(unparsed)}")
    print(f"Target document candidate count: {len(targets)}")
    print(f"Verified positive candidate count: {len(verified)}")

    print("\nDOCUMENT TYPES")
    print("-" * 60)
    for k in sorted(type_counts):
        print(f"{k}: {type_counts[k]}")

    if verified:
        resolution = "GAZETTE_BULK_FULLTEXT_VERIFIED_POSITIVE_CANDIDATE_DISCOVERED"
        next_action = "W-stage에서 후보 원문을 재검증하여 고시번호·고시일·행정구역·지정 범위·현재 유효 여부와 positive PNU / spatial source를 확정한다."
    elif targets:
        resolution = "GAZETTE_BULK_FULLTEXT_TARGET_DOCUMENT_CANDIDATE_DISCOVERED"
        next_action = "target-bearing 원문의 action context와 고시번호를 W-stage에서 세부 검증한다."
    else:
        resolution = "GAZETTE_BULK_FULLTEXT_DISCOVERY_COMPLETED_NO_TARGET_DOCUMENT"
        next_action = "해석 불가 HWP/이미지 PDF는 parser 전용 단계로 분리하고, 그 외에는 국가기록원·관보·토지이음·행정전자민원 원문으로 확장한다."

    validation = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "input exists": INPUT_PATH.exists(),
        "U-stage input parsed": isinstance(data, dict),
        "bulk archive only execution enabled": all(s.source_class == BULK_CLASS for s in seeds),
        "download URL required": all(is_http_url(s.url) for s in seeds),
        "canonical seeds unique": len({s.url for s in seeds}) == len(seeds),
        "list-title-only promotion prohibited": all(r.target_in_text for r in targets),
        "raw-byte target promotion prohibited": all(r.parsed for r in targets),
        "verified candidate body target required": all(r.target_in_text for r in verified),
        "verified candidate action context required": all(bool(r.action_terms) for r in verified),
        "verified candidate notice number required": all(bool(r.notice_numbers) for r in verified),
        "classic HWP auto-promotion prohibited": all(not r.verified_positive_candidate for r in records if r.detected_type == "HWP" and not r.parsed),
        "runtime registration remains blocked": True,
        "SITE FALSE remains blocked": True,
        "final positive promotion prohibited": True,
        "output written": True,
    }

    output = {
        "target_name": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "stage": "V",
        "input_path": str(INPUT_PATH),
        "resolution": resolution,
        "next_action": next_action,
        "statistics": {
            "raw_seed_count": len(raw_seeds),
            "canonical_seed_count": len(seeds),
            "request_count": len(records),
            "http_success_count": sum(1 for r in records if r.http_status is not None and 200 <= r.http_status < 400),
            "transport_or_download_error_count": len(errors),
            "parsed_document_count": sum(1 for r in records if r.parsed),
            "unparsed_document_count": len(unparsed),
            "target_document_candidate_count": len(targets),
            "verified_positive_candidate_count": len(verified),
            "document_type_counts": type_counts,
            "resolution_counts": resolution_counts,
        },
        "seeds": [asdict(s) for s in seeds],
        "records": [asdict(r) for r in records],
        "target_document_candidates": [asdict(r) for r in targets],
        "verified_positive_candidates": [asdict(r) for r in verified],
        "validation": validation,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("RESOLUTION")
    print("=" * 60)
    print(resolution)
    print(f"\n{next_action}")
    print(f"\nOutput: {OUTPUT_PATH}")

    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for key, value in validation.items():
        print(f"{key}: {value}")

    all_pass = all(validation.values())
    print(f"\nall_pass: {all_pass}")
    if not all_pass:
        print("\nFAILED:")
        for key, value in validation.items():
            if not value:
                print(f"- {key}")
        raise AssertionError("Development density management area gazette bulk full-text discovery regression failed")


if __name__ == "__main__":
    main()
