from __future__ import annotations

from law_data.historical_site_event_resolver import (
    HistoricalSiteEventEvidenceState,
    resolve_historical_site_event,
)
from law_data.production_historical_site_event_adapter import (
    ADAPTER_NAME,
    adapt_historical_site_event_to_production_contract,
)
from law_data.production_site_condition import FALSE, UNKNOWN


CLASSIFICATION = "STEP18_PRODUCTION_HISTORICAL_SITE_EVENT_ADAPTER_PASS"


def assert_equal(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected={expected!r}, actual={actual!r}")


def assert_true(value, label: str) -> None:
    if value is not True:
        raise AssertionError(f"{label}: expected True, actual={value!r}")


def assert_false(value, label: str) -> None:
    if value is not False:
        raise AssertionError(f"{label}: expected False, actual={value!r}")


def main() -> None:
    # Positive historical evidence produces TRUE_CANDIDATE at resolver level,
    # but this adapter must not promote that candidate to production TRUE.
    true_candidate_result = resolve_historical_site_event(
        HistoricalSiteEventEvidenceState(
            verified_qualifying_event_present=True,
        ),
        search_hit=True,
        http_200=True,
        candidate_count=1,
    )
    true_candidate = adapt_historical_site_event_to_production_contract(
        name="synthetic historical positive",
        resolver_result=true_candidate_result,
        confidence="HIGH",
        source="SYNTHETIC_HISTORICAL_RESOLVER",
    )
    assert_equal(
        true_candidate_result["resolution"],
        "TRUE_CANDIDATE",
        "resolver positive remains TRUE_CANDIDATE",
    )
    assert_equal(
        true_candidate.state,
        UNKNOWN,
        "TRUE_CANDIDATE is not promoted to production TRUE",
    )
    assert_equal(
        true_candidate.provenance["resolver_resolution"],
        "TRUE_CANDIDATE",
        "TRUE_CANDIDATE preserved in provenance",
    )

    # Ordinary insufficient historical evidence remains UNKNOWN.
    unknown_result = resolve_historical_site_event(
        HistoricalSiteEventEvidenceState(),
        search_hit=False,
        http_200=True,
        candidate_count=0,
        negative_evidence={"no_hit": True},
    )
    unknown = adapt_historical_site_event_to_production_contract(
        name="synthetic historical unknown",
        resolver_result=unknown_result,
        confidence="MEDIUM",
    )
    assert_equal(unknown.state, UNKNOWN, "UNKNOWN preserved")
    assert_equal(
        unknown.diagnostics["diagnostic_discovery"]["negative_evidence"]["no_hit"],
        True,
        "negative discovery diagnostic preserved",
    )
    assert_equal(
        unknown.state,
        UNKNOWN,
        "negative discovery cannot manufacture FALSE",
    )

    # FALSE is production-dispositive only when exhaustive disproof is positively
    # verified by the historical resolver contract.
    exhaustive_false_result = resolve_historical_site_event(
        HistoricalSiteEventEvidenceState(
            verified_qualifying_event_present=False,
            official_history_source_verified=True,
            history_scope_complete_verified=True,
            required_originals_resolved=True,
            candidate_universe_exhaustively_enumerated=True,
            all_candidates_classified_non_target=True,
            unresolved_historical_source_present=False,
        )
    )
    exhaustive_false = adapt_historical_site_event_to_production_contract(
        name="synthetic historical exhaustive false",
        resolver_result=exhaustive_false_result,
        confidence="HIGH",
    )
    assert_equal(
        exhaustive_false_result["resolution"],
        FALSE,
        "resolver exhaustive disproof FALSE",
    )
    assert_true(
        exhaustive_false_result["exhaustive_disproof_verified"],
        "resolver exhaustive disproof verified",
    )
    assert_equal(
        exhaustive_false.state,
        FALSE,
        "verified exhaustive FALSE preserved",
    )

    # A forged/partial FALSE without the exhaustive gate must fail closed.
    unverified_false = adapt_historical_site_event_to_production_contract(
        name="synthetic historical unverified false",
        resolver_result={
            "resolution_type": "HISTORICAL_SITE_EVENT",
            "resolution": FALSE,
            "resolution_basis": "SYNTHETIC_UNVERIFIED_FALSE",
            "exhaustive_disproof_verified": False,
            "diagnostic_discovery": {"dispositive": False},
        },
    )
    assert_equal(
        unverified_false.state,
        UNKNOWN,
        "unverified FALSE fails closed",
    )

    malformed = adapt_historical_site_event_to_production_contract(
        name="synthetic historical malformed",
        resolver_result={
            "resolution": "NO_HIT",
            "exhaustive_disproof_verified": False,
        },
    )
    assert_equal(malformed.state, UNKNOWN, "malformed resolution fails closed")

    missing = adapt_historical_site_event_to_production_contract(
        name="synthetic historical missing",
        resolver_result=None,
    )
    assert_equal(missing.state, UNKNOWN, "missing resolver result fails closed")

    # Explicit production metadata remains independent and cannot promote UNKNOWN.
    explicit_gates = adapt_historical_site_event_to_production_contract(
        name="synthetic historical explicit gates",
        resolver_result=true_candidate_result,
        production_eligible=True,
        runtime_registered=True,
    )
    assert_true(explicit_gates.production_eligible, "explicit eligibility preserved")
    assert_true(explicit_gates.runtime_registered, "explicit registration preserved")
    assert_equal(
        explicit_gates.state,
        UNKNOWN,
        "explicit gates cannot promote TRUE_CANDIDATE",
    )

    for condition, label in (
        (true_candidate, "TRUE_CANDIDATE"),
        (unknown, "UNKNOWN"),
        (exhaustive_false, "FALSE"),
        (unverified_false, "UNVERIFIED_FALSE"),
        (malformed, "MALFORMED"),
        (missing, "MISSING"),
    ):
        assert_equal(
            condition.condition_type,
            "SITE_HISTORY",
            f"{label} condition type",
        )
        assert_equal(
            condition.resolution_type,
            "HISTORICAL_SITE_EVENT",
            f"{label} resolution type",
        )
        assert_false(
            condition.negative_evidence_allowed,
            f"{label} negative evidence disabled",
        )
        assert_false(
            condition.legal_absence_inference_allowed,
            f"{label} legal absence inference disabled",
        )
        assert_false(
            condition.site_promotion_allowed,
            f"{label} SITE promotion disabled",
        )

    assert_equal(
        true_candidate.provenance["adapter"],
        ADAPTER_NAME,
        "adapter provenance preserved",
    )
    assert_equal(
        true_candidate.diagnostics["evidence_state"],
        true_candidate_result["evidence_state"],
        "historical evidence state preserved",
    )
    assert_false(
        true_candidate.production_eligible,
        "TRUE_CANDIDATE does not imply production eligibility",
    )
    assert_false(
        true_candidate.runtime_registered,
        "TRUE_CANDIDATE does not imply runtime registration",
    )

    print("=" * 72)
    print("STEP 18 PRODUCTION HISTORICAL SITE EVENT ADAPTER REGRESSION")
    print("=" * 72)
    print("TRUE_CANDIDATE -> production UNKNOWN: PASS")
    print("Resolver UNKNOWN preservation: PASS")
    print("Verified exhaustive-disproof FALSE preservation: PASS")
    print("Unverified FALSE fail-closed: PASS")
    print("Malformed/missing resolution fail-closed: PASS")
    print("Historical evidence/provenance preservation: PASS")
    print("Production eligibility/runtime registration remain independent: PASS")
    print("Negative/legal absence/SITE promotion disabled: PASS")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
