from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


PROFILE_NAME = "REGULATION_RESOLUTION_PROFILE"

VALID_CONDITION_TYPES = frozenset({"SITE", "SITE_HISTORY"})
VALID_RESOLUTION_TYPES = frozenset(
    {
        "SNAPSHOT",
        "SPATIAL",
        "HYBRID_SPATIAL_NOTICE",
        "HISTORICAL_SITE_EVENT",
    }
)


def _normalize_items(values: Iterable[Any] | None) -> tuple[str, ...]:
    if values is None:
        return ()

    normalized: list[str] = []
    for value in values:
        item = str(value or "").strip()
        if item and item not in normalized:
            normalized.append(item)
    return tuple(normalized)


@dataclass(frozen=True)
class RegulationResolutionProfile:
    """Read-only metadata boundary for regulation resolution policy.

    The profile describes identity and verification requirements only. It does
    not execute a resolver, decide SITE applicability, register runtime logic,
    mutate Rule Engine input, or expose a public API contract.

    Missing or unverified standard-code identity is a valid fail-closed state.
    A profile must never manufacture a code from condition name, resolution
    type, authority requirements, or source requirements.
    """

    name: str
    condition_type: str
    resolution_type: str
    standard_code: str | None = None
    standard_code_verified: bool = False
    authority_requirements: tuple[str, ...] = ()
    source_policy_requirements: tuple[str, ...] = ()
    authority_identity_verified: bool = False
    source_policy_verified: bool = False
    negative_evidence_allowed: bool = False
    legal_absence_inference_allowed: bool = False
    site_promotion_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.name).strip():
            raise ValueError("condition name is required")

        if self.condition_type not in VALID_CONDITION_TYPES:
            raise ValueError(
                f"unsupported condition_type: {self.condition_type!r}"
            )

        if self.resolution_type not in VALID_RESOLUTION_TYPES:
            raise ValueError(
                f"unsupported resolution_type: {self.resolution_type!r}"
            )

        normalized_code = (
            str(self.standard_code).strip()
            if self.standard_code is not None
            else None
        )
        if not normalized_code:
            normalized_code = None

        if self.standard_code_verified and normalized_code is None:
            raise ValueError(
                "standard_code_verified requires an explicit standard_code; "
                "unverified codes must remain absent rather than guessed"
            )

        if (
            self.condition_type == "SITE_HISTORY"
            and self.resolution_type == "SPATIAL"
        ):
            raise ValueError(
                "SITE_HISTORY cannot use SPATIAL resolution_type; historical "
                "semantics must remain distinct from spatial runtime semantics"
            )

        object.__setattr__(self, "name", str(self.name).strip())
        object.__setattr__(self, "standard_code", normalized_code)
        object.__setattr__(
            self,
            "authority_requirements",
            _normalize_items(self.authority_requirements),
        )
        object.__setattr__(
            self,
            "source_policy_requirements",
            _normalize_items(self.source_policy_requirements),
        )
        object.__setattr__(self, "diagnostics", dict(self.diagnostics))

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": PROFILE_NAME,
            "name": self.name,
            "condition_type": self.condition_type,
            "resolution_type": self.resolution_type,
            "standard_code": self.standard_code,
            "standard_code_verified": self.standard_code_verified,
            "authority_requirements": list(self.authority_requirements),
            "source_policy_requirements": list(self.source_policy_requirements),
            "authority_identity_verified": self.authority_identity_verified,
            "source_policy_verified": self.source_policy_verified,
            "negative_evidence_allowed": self.negative_evidence_allowed,
            "legal_absence_inference_allowed": self.legal_absence_inference_allowed,
            "site_promotion_allowed": self.site_promotion_allowed,
            "production_registration_allowed": self.production_registration_allowed,
            "runtime_registration_allowed": self.runtime_registration_allowed,
            "diagnostics": dict(self.diagnostics),
        }


def normalize_regulation_resolution_profile(
    *,
    name: str,
    condition_type: str,
    resolution_type: str,
    standard_code: Any = None,
    standard_code_verified: bool = False,
    authority_requirements: Iterable[Any] | None = None,
    source_policy_requirements: Iterable[Any] | None = None,
    authority_identity_verified: bool = False,
    source_policy_verified: bool = False,
    negative_evidence_allowed: bool = False,
    legal_absence_inference_allowed: bool = False,
    site_promotion_allowed: bool = False,
    production_registration_allowed: bool = False,
    runtime_registration_allowed: bool = False,
    diagnostics: Mapping[str, Any] | None = None,
) -> RegulationResolutionProfile:
    """Normalize profile metadata without inferring identity or permissions."""

    normalized_code = str(standard_code or "").strip() or None
    code_verified = standard_code_verified is True and normalized_code is not None

    return RegulationResolutionProfile(
        name=str(name).strip(),
        condition_type=str(condition_type).strip().upper(),
        resolution_type=str(resolution_type).strip().upper(),
        standard_code=normalized_code,
        standard_code_verified=code_verified,
        authority_requirements=_normalize_items(authority_requirements),
        source_policy_requirements=_normalize_items(source_policy_requirements),
        authority_identity_verified=authority_identity_verified is True,
        source_policy_verified=source_policy_verified is True,
        negative_evidence_allowed=negative_evidence_allowed is True,
        legal_absence_inference_allowed=legal_absence_inference_allowed is True,
        site_promotion_allowed=site_promotion_allowed is True,
        production_registration_allowed=production_registration_allowed is True,
        runtime_registration_allowed=runtime_registration_allowed is True,
        diagnostics=dict(diagnostics or {}),
    )
