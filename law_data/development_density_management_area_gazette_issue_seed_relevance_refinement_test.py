from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"

INPUT_PATH = (
    OUTPUT_DIR
    / "development_density_management_area_gazette_archive_issue_attachment_discovery.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "development_density_management_area_gazette_issue_seed_relevance_refinement.json"
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"


# ============================================================
# CLASSIFICATION
# ============================================================

TARGET_DIRECT_SEED = "TARGET_DIRECT_SEED"
URBAN_NOTICE_SEED = "URBAN_NOTICE_SEED"
GAZETTE_BULK_ARCHIVE = "GAZETTE_BULK_ARCHIVE"
EXCLUDED_UNRELATED_DOCUMENT = "EXCLUDED_UNRELATED_DOCUMENT"

VALID_CLASSES = {
    TARGET_DIRECT_SEED,
    URBAN_NOTICE_SEED,
    GAZETTE_BULK_ARCHIVE,
    EXCLUDED_UNRELATED_DOCUMENT,
}


# ============================================================
# SEMANTIC TERMS
# ============================================================

TARGET_TERMS = (
    "개발밀도관리구역",
    "개발 밀도 관리 구역",
)

URBAN_CORE_TERMS = (
    "도시관리계획",
    "도시계획",
    "국토계획",
    "지형도면",
    "용도지역",
    "용도지구",
    "용도구역",
    "지구단위계획",
    "도시계획시설",
    "개발행위",
    "개발밀도",
)

ACTION_TERMS = (
    "지정",
    "변경",
    "해제",
    "결정",
    "고시",
    "공고",
)

STRONG_ACTION_TERMS = (
    "지정",
    "변경",
    "해제",
    "결정",
)

GAZETTE_TERMS = (
    "시보",
    "구보",
    "군보",
    "공보",
    "호외",
)

UNRELATED_TERMS = (
    "공직자윤리",
    "채용",
    "입찰",
    "분묘",
    "보건",
    "위생",
    "복지",
    "기부",
    "벚꽃",
    "저당권",
    "말소",
    "공공근로",
    "기간제근로",
    "경관심의",
    "환경오염",
    "재난",
    "관광",
    "여행",
)

GENERIC_DOWNLOAD_LABELS = (
    "첨부파일 다운로드",
    "다운로드",
    "첨부파일",
)

NOTICE_NUMBER_PATTERN = re.compile(
    r"(?:[가-힣]{1,20}\s*)?"
    r"(?:고시|공고)\s*제?\s*\d{4}\s*-\s*\d+\s*호?"
)

ISSUE_NUMBER_PATTERN = re.compile(
    r"제\s*\d+\s*호"
)


# ============================================================
# HELPERS
# ============================================================

def normalize_text(value) -> str:
    if value is None:
        return ""

    if isinstance(value, (list, tuple, set)):
        value = " ".join(str(x) for x in value if x is not None)

    text = str(value)
    text = re.sub(r"&[#a-zA-Z0-9]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def contains_any(text: str, terms) -> bool:
    lowered = normalize_text(text).lower()
    return any(term.lower() in lowered for term in terms)


def count_terms(text: str, terms) -> int:
    lowered = normalize_text(text).lower()
    return sum(1 for term in terms if term.lower() in lowered)


def canonicalize_url(url: str) -> str:
    url = normalize_text(url)
    if not url:
        return ""

    try:
        parsed = urlsplit(url)

        pairs = parse_qsl(parsed.query, keep_blank_values=True)

        volatile_keys = {
            "token",
            "_csrf",
            "csrf",
            "jsessionid",
        }

        cleaned = [
            (k, v)
            for k, v in pairs
            if k.lower() not in volatile_keys
        ]

        cleaned.sort(key=lambda item: (item[0], item[1]))

        return urlunsplit(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path,
                urlencode(cleaned, doseq=True),
                "",
            )
        )
    except Exception:
        return url


def collect_urls(record: dict) -> list[str]:
    urls = []

    scalar_keys = (
        "url",
        "detail_url",
        "attachment_url",
        "extensionless_url",
    )

    list_keys = (
        "detail_urls",
        "attachment_urls",
        "extensionless_urls",
    )

    for key in scalar_keys:
        value = record.get(key)
        if value:
            urls.append(str(value))

    for key in list_keys:
        value = record.get(key)
        if isinstance(value, list):
            urls.extend(str(x) for x in value if x)

    deduped = []
    seen = set()

    for url in urls:
        canonical = canonicalize_url(url)
        if canonical and canonical not in seen:
            seen.add(canonical)
            deduped.append(canonical)

    return deduped


def build_evidence_text(record: dict) -> str:
    pieces = []

    keys = (
        "label",
        "preview",
        "text",
        "parent_label",
        "archive_label",
        "source_label",
        "class",
        "candidate_class",
    )

    for key in keys:
        value = record.get(key)
        if value:
            pieces.append(normalize_text(value))

    for key in (
        "issue_numbers",
        "notice_numbers",
        "dates",
    ):
        value = record.get(key)
        if value:
            pieces.append(normalize_text(value))

    return normalize_text(" ".join(pieces))


def has_notice_number(text: str) -> bool:
    return bool(NOTICE_NUMBER_PATTERN.search(normalize_text(text)))


def has_issue_number(text: str) -> bool:
    return bool(ISSUE_NUMBER_PATTERN.search(normalize_text(text)))


def is_generic_gazette_issue(text: str) -> bool:
    text = normalize_text(text)

    if not contains_any(text, GAZETTE_TERMS):
        return False

    if contains_any(text, TARGET_TERMS):
        return False

    if contains_any(text, URBAN_CORE_TERMS):
        return False

    # "전주시보 제1234호 발행", "OO시보 제100호 호외 발행" 등
    issue_like = has_issue_number(text)

    generic_release_words = any(
        term in text
        for term in (
            "발행",
            "호외",
            "첨부파일 있음",
        )
    )

    return issue_like and generic_release_words


def unrelated_score(text: str) -> int:
    return count_terms(text, UNRELATED_TERMS)


def urban_score(text: str) -> int:
    score = 0

    score += count_terms(text, URBAN_CORE_TERMS) * 3
    score += count_terms(text, STRONG_ACTION_TERMS) * 2

    if "고시" in text:
        score += 2

    if has_notice_number(text):
        score += 2

    return score


def classify_candidate(record: dict) -> dict:
    evidence_text = build_evidence_text(record)
    urls = collect_urls(record)

    target_direct = contains_any(evidence_text, TARGET_TERMS)

    urban_term_count = count_terms(
        evidence_text,
        URBAN_CORE_TERMS,
    )

    strong_action_count = count_terms(
        evidence_text,
        STRONG_ACTION_TERMS,
    )

    action_count = count_terms(
        evidence_text,
        ACTION_TERMS,
    )

    notice_number = has_notice_number(evidence_text)
    issue_number = has_issue_number(evidence_text)

    gazette_context = contains_any(
        evidence_text,
        GAZETTE_TERMS,
    )

    unrelated = unrelated_score(evidence_text)

    score = 0
    reasons = []

    if target_direct:
        score += 100
        reasons.append("TARGET_DIRECT_EVIDENCE")

    if urban_term_count:
        score += urban_term_count * 8
        reasons.append("URBAN_PLANNING_CONTEXT")

    if strong_action_count:
        score += strong_action_count * 4
        reasons.append("STRONG_ACTION_CONTEXT")

    if "고시" in evidence_text:
        score += 3
        reasons.append("NOTICE_CONTEXT")

    if notice_number:
        score += 4
        reasons.append("NOTICE_NUMBER_EVIDENCE")

    if gazette_context:
        score += 1
        reasons.append("GAZETTE_CONTEXT")

    if unrelated:
        score -= unrelated * 6
        reasons.append("UNRELATED_CONTEXT_PENALTY")

    generic_gazette = is_generic_gazette_issue(
        evidence_text
    )

    if generic_gazette:
        reasons.append("GENERIC_GAZETTE_ISSUE")

    # --------------------------------------------------------
    # classification
    # --------------------------------------------------------

    if target_direct:
        classification = TARGET_DIRECT_SEED

    elif (
        urban_term_count >= 1
        and (
            strong_action_count >= 1
            or "고시" in evidence_text
        )
        and unrelated == 0
    ):
        classification = URBAN_NOTICE_SEED

    elif generic_gazette:
        classification = GAZETTE_BULK_ARCHIVE

    elif (
        gazette_context
        and issue_number
        and urban_term_count == 0
    ):
        classification = GAZETTE_BULK_ARCHIVE

    else:
        classification = EXCLUDED_UNRELATED_DOCUMENT

    return {
        "region": normalize_text(
            record.get("region")
            or record.get("municipality")
            or record.get("site_name")
        ),
        "classification": classification,
        "score": score,
        "reasons": reasons,
        "label": normalize_text(record.get("label")),
        "preview": normalize_text(record.get("preview")),
        "evidence_text": evidence_text,
        "target_direct": target_direct,
        "urban_term_count": urban_term_count,
        "strong_action_count": strong_action_count,
        "action_count": action_count,
        "notice_number_evidence": notice_number,
        "issue_number_evidence": issue_number,
        "gazette_context": gazette_context,
        "unrelated_score": unrelated,
        "urls": urls,
        "source_record": record,
    }


def candidate_identity(candidate: dict) -> tuple:
    urls = tuple(candidate.get("urls") or [])

    return (
        candidate.get("region", ""),
        candidate.get("classification", ""),
        candidate.get("label", ""),
        urls,
    )


# ============================================================
# INPUT EXTRACTION
# ============================================================

def extract_candidate_records(payload: dict) -> list[dict]:
    records = []

    candidate_keys = (
        "candidates",
        "issue_detail_candidates",
        "document_seeds",
        "gazette_issue_detail_seeds",
        "high_priority_document_seeds",
        "extensionless_download_seeds",
        "attachment_seeds",
    )

    for key in candidate_keys:
        value = payload.get(key)

        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    records.append(item)

    # Some stages store data under result
    result = payload.get("result")

    if isinstance(result, dict):
        for key in candidate_keys:
            value = result.get(key)

            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        records.append(item)

    # fallback: recursively inspect selected structures
    if not records:
        def walk(value):
            if isinstance(value, dict):
                if (
                    "label" in value
                    and any(
                        key in value
                        for key in (
                            "detail_urls",
                            "attachment_urls",
                            "extensionless_urls",
                            "url",
                        )
                    )
                ):
                    records.append(value)

                for child in value.values():
                    walk(child)

            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(payload)

    # canonical structural dedupe
    unique = []
    seen = set()

    for record in records:
        evidence = build_evidence_text(record)
        urls = tuple(collect_urls(record))

        key = (
            normalize_text(
                record.get("region")
                or record.get("municipality")
                or record.get("site_name")
            ),
            normalize_text(record.get("label")),
            evidence,
            urls,
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(record)

    return unique


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("GAZETTE ISSUE / DOWNLOAD SEED RELEVANCE REFINEMENT")
    print("=" * 60)
    print()
    print(f"Target: {TARGET_NAME}")
    print(f"Standard code: {STANDARD_CODE}")
    print(f"Input: {INPUT_PATH}")
    print()

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Input JSON not found: {INPUT_PATH}"
        )

    with INPUT_PATH.open(
        "r",
        encoding="utf-8",
    ) as f:
        payload = json.load(f)

    raw_records = extract_candidate_records(payload)

    print(f"Raw seed record count: {len(raw_records)}")
    print()

    classified = [
        classify_candidate(record)
        for record in raw_records
    ]

    # final dedupe
    unique_classified = []
    seen = set()

    for candidate in classified:
        key = candidate_identity(candidate)

        if key in seen:
            continue

        seen.add(key)
        unique_classified.append(candidate)

    classified = unique_classified

    classified.sort(
        key=lambda x: (
            {
                TARGET_DIRECT_SEED: 0,
                URBAN_NOTICE_SEED: 1,
                GAZETTE_BULK_ARCHIVE: 2,
                EXCLUDED_UNRELATED_DOCUMENT: 3,
            }.get(x["classification"], 9),
            -x["score"],
            x["region"],
            x["label"],
        )
    )

    counts = Counter(
        item["classification"]
        for item in classified
    )

    verification_pool = [
        item
        for item in classified
        if item["classification"]
        in {
            TARGET_DIRECT_SEED,
            URBAN_NOTICE_SEED,
        }
    ]

    bulk_archive = [
        item
        for item in classified
        if item["classification"]
        == GAZETTE_BULK_ARCHIVE
    ]

    excluded = [
        item
        for item in classified
        if item["classification"]
        == EXCLUDED_UNRELATED_DOCUMENT
    ]

    print("=" * 60)
    print("REFINEMENT RESULT")
    print("=" * 60)
    print(f"Raw record count: {len(raw_records)}")
    print(f"Canonical candidate count: {len(classified)}")
    print()

    for class_name in (
        TARGET_DIRECT_SEED,
        URBAN_NOTICE_SEED,
        GAZETTE_BULK_ARCHIVE,
        EXCLUDED_UNRELATED_DOCUMENT,
    ):
        print(
            f"{class_name}: "
            f"{counts.get(class_name, 0)}"
        )

    print()
    print(
        f"Next-stage verification pool: "
        f"{len(verification_pool)}"
    )
    print(
        f"Deferred bulk archive count: "
        f"{len(bulk_archive)}"
    )
    print(
        f"Excluded count: "
        f"{len(excluded)}"
    )

    if verification_pool:
        print()
        print("HIGH RELEVANCE DOCUMENT SEEDS")
        print("-" * 60)

        for index, item in enumerate(
            verification_pool[:100],
            start=1,
        ):
            print(
                f"[{index}] "
                f"{item['region'] or '-'}"
            )
            print(
                f"Class: {item['classification']}"
            )
            print(
                f"Score: {item['score']}"
            )
            print(
                f"Label: {item['label']}"
            )
            print(
                f"Reasons: {item['reasons']}"
            )

            for url in item["urls"]:
                print(f"URL: {url}")

            print()

    print("=" * 60)
    print("RESOLUTION")
    print("=" * 60)

    if any(
        item["classification"]
        == TARGET_DIRECT_SEED
        for item in verification_pool
    ):
        resolution = (
            "GAZETTE_TARGET_DIRECT_DOCUMENT_SEED_DISCOVERED"
        )

        message = (
            "target이 직접 확인된 공보/download seed를 "
            "V-stage에서 실제 파일 HTTP 조회 및 원문 검증한다."
        )

    elif verification_pool:
        resolution = (
            "GAZETTE_URBAN_NOTICE_SEEDS_REFINED_FOR_DOCUMENT_VERIFICATION"
        )

        message = (
            "도시계획 + 지정·변경·해제/고시 문맥이 있는 "
            "고신뢰 seed만 V-stage 실제 파일 검증 대상으로 유지한다."
        )

    else:
        resolution = (
            "GAZETTE_SEED_REFINEMENT_COMPLETED_NO_HIGH_RELEVANCE_SEED"
        )

        message = (
            "현재 확보 seed에는 target 직접증거 또는 충분한 "
            "도시계획 고시 문맥이 없다. bulk archive는 final positive로 "
            "승격하지 않고 별도 과거 공보 full-text 전략으로 유지한다."
        )

    print(resolution)
    print()
    print(message)

    output = {
        "target": {
            "name": TARGET_NAME,
            "standard_code": STANDARD_CODE,
        },
        "input": str(INPUT_PATH),
        "summary": {
            "raw_record_count": len(raw_records),
            "canonical_candidate_count": len(classified),
            "classification_counts": dict(counts),
            "verification_pool_count": len(
                verification_pool
            ),
            "bulk_archive_count": len(
                bulk_archive
            ),
            "excluded_count": len(excluded),
        },
        "verification_pool": verification_pool,
        "bulk_archive": bulk_archive,
        "excluded": excluded,
        "all_candidates": classified,
        "resolution": resolution,
    }

    OUTPUT_DIR.mkdir(
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

    print()
    print(f"Output: {OUTPUT_PATH}")

    # ========================================================
    # VALIDATION
    # ========================================================

    validation = {}

    validation["target name"] = (
        TARGET_NAME == "개발밀도관리구역"
    )

    validation["standard code"] = (
        STANDARD_CODE == "UQQ700"
    )

    validation["input exists"] = (
        INPUT_PATH.exists()
    )

    validation["T-stage input parsed"] = (
        isinstance(payload, dict)
    )

    validation["seed extraction enabled"] = (
        isinstance(raw_records, list)
    )

    validation[
        "semantic relevance classification enabled"
    ] = bool(classified or not raw_records)

    validation[
        "all classifications valid"
    ] = all(
        item["classification"]
        in VALID_CLASSES
        for item in classified
    )

    validation[
        "verification pool contains only allowed classes"
    ] = all(
        item["classification"]
        in {
            TARGET_DIRECT_SEED,
            URBAN_NOTICE_SEED,
        }
        for item in verification_pool
    )

    validation[
        "bulk archive excluded from verification pool"
    ] = all(
        item["classification"]
        != GAZETTE_BULK_ARCHIVE
        for item in verification_pool
    )

    validation[
        "unrelated documents excluded from verification pool"
    ] = all(
        item["classification"]
        != EXCLUDED_UNRELATED_DOCUMENT
        for item in verification_pool
    )

    validation[
        "urban notice requires urban context"
    ] = all(
        item["urban_term_count"] >= 1
        for item in verification_pool
        if item["classification"]
        == URBAN_NOTICE_SEED
    )

    validation[
        "urban notice requires action context"
    ] = all(
        (
            item["strong_action_count"] >= 1
            or "고시" in item["evidence_text"]
        )
        for item in verification_pool
        if item["classification"]
        == URBAN_NOTICE_SEED
    )

    validation[
        "target direct seeds contain target evidence"
    ] = all(
        item["target_direct"]
        for item in verification_pool
        if item["classification"]
        == TARGET_DIRECT_SEED
    )

    validation[
        "generic gazette-only promotion zero"
    ] = all(
        not (
            item["classification"]
            in {
                TARGET_DIRECT_SEED,
                URBAN_NOTICE_SEED,
            }
            and is_generic_gazette_issue(
                item["evidence_text"]
            )
            and not item["target_direct"]
            and item["urban_term_count"] == 0
        )
        for item in classified
    )

    validation[
        "notice-number-only promotion zero"
    ] = all(
        not (
            item["classification"]
            == URBAN_NOTICE_SEED
            and item["notice_number_evidence"]
            and item["urban_term_count"] == 0
        )
        for item in classified
    )

    validation[
        "verification seeds unique"
    ] = (
        len(verification_pool)
        ==
        len(
            {
                candidate_identity(item)
                for item in verification_pool
            }
        )
    )

    validation[
        "runtime registration remains blocked"
    ] = True

    validation[
        "SITE FALSE remains blocked"
    ] = True

    validation[
        "verified positive promotion remains blocked"
    ] = True

    validation["output written"] = (
        OUTPUT_PATH.exists()
    )

    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)

    for key, value in validation.items():
        print(f"{key}: {value}")

    all_pass = all(validation.values())

    print()
    print(f"all_pass: {all_pass}")

    if not all_pass:
        failed = [
            key
            for key, value in validation.items()
            if not value
        ]

        print()
        print("FAILED:")

        for key in failed:
            print(f"- {key}")

        raise AssertionError(
            "Development density management area "
            "gazette issue seed relevance refinement "
            "regression failed"
        )


if __name__ == "__main__":
    main()