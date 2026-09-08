from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse


QUALIFIED_HISTORICAL_NOTICE_CANDIDATE = "QUALIFIED_HISTORICAL_NOTICE_CANDIDATE"
REJECTED_INVALID_URL = "REJECTED_INVALID_URL"
REJECTED_AUTHORITY_UNQUALIFIED = "REJECTED_AUTHORITY_UNQUALIFIED"
REJECTED_DOCUMENT_ROLE_WEAK = "REJECTED_DOCUMENT_ROLE_WEAK"
REJECTED_TARGET_UNBOUND = "REJECTED_TARGET_UNBOUND"


@dataclass(frozen=True)
class HistoricalNoticeCandidateInput:
    url: str
    title: str = ""
    notice_number: str = ""
    published_date: str = ""
    authority_source_qualified: bool = False
    target_name_present: bool = False
    document_role: str = ""


@dataclass(frozen=True)
class HistoricalNoticeCandidateResult:
    status: str
    url: str
    title: str
    notice_number: str
    published_date: str
    authority_source_qualified: bool
    target_name_present: bool
    document_role: str
    official_designation_identity_verified: bool = False
    current_validity_verified: bool = False
    site_spatial_inclusion_verified: bool = False
    runtime_registration_allowed: bool = False
    dispositive: bool = False


def _valid_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalized_role(role: str) -> str:
    return " ".join(role.strip().upper().split())


def qualify_historical_notice_candidate(
    item: HistoricalNoticeCandidateInput,
) -> HistoricalNoticeCandidateResult:
    """Qualify one historical notice candidate without promoting legal identity.

    This resolver only determines whether a discovered document is suitable to enter
    the later designation-identity verification stage. A qualified candidate is not
    itself proof of designation, current validity, SITE spatial inclusion, legal
    absence, or runtime registration eligibility.
    """

    role = _normalized_role(item.document_role)

    if not _valid_http_url(item.url):
        status = REJECTED_INVALID_URL
    elif item.authority_source_qualified is not True:
        status = REJECTED_AUTHORITY_UNQUALIFIED
    elif role not in {
        "NOTICE",
        "GAZETTE_NOTICE",
        "URBAN_PLANNING_NOTICE",
        "DESIGNATION_NOTICE_CANDIDATE",
    }:
        status = REJECTED_DOCUMENT_ROLE_WEAK
    elif item.target_name_present is not True:
        status = REJECTED_TARGET_UNBOUND
    else:
        status = QUALIFIED_HISTORICAL_NOTICE_CANDIDATE

    return HistoricalNoticeCandidateResult(
        status=status,
        url=item.url,
        title=item.title.strip(),
        notice_number=item.notice_number.strip(),
        published_date=item.published_date.strip(),
        authority_source_qualified=item.authority_source_qualified is True,
        target_name_present=item.target_name_present is True,
        document_role=role,
    )


def collect_historical_notice_candidates(
    items: Iterable[HistoricalNoticeCandidateInput],
) -> list[HistoricalNoticeCandidateResult]:
    """Return deterministic candidate qualification results in input order."""

    return [qualify_historical_notice_candidate(item) for item in items]
