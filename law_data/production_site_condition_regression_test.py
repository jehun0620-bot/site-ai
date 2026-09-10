from __future__ import annotations

from law_data.production_site_condition import (
    FALSE,
    TRUE,
    UNKNOWN,
    ProductionSiteCondition,
    normalize_production_site_condition,
    rule_engine_condition_view,
)


CLASSIFICATION = "STEP18_PRODUCTION_SITE_CONDITION_CONTRACT_PASS"


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
    # UNKNOWN must remain UNKNOWN and must not manufacture production eligibility.
    unknown_condition = normalize_production_site_condition(
        name="개발밀도관리구역",
        condition_type="SITE",
        resolution_type="HYBRID_SPATIAL_NOTICE",
        state=UNKNOWN,
        confidence="NONE",
        source="SYNTHETIC_CONTRACT_TEST",
        diagnostics={"search_no_hit": True},
    )
    assert_equal(unknown_condition.state, UNKNOWN, "UNKNOWN preservation")
    assert_false(
        unknown_condition.production_eligible,
        "UNKNOWN does not imply production eligibility",
    )
    assert_false(
        unknown_condition.runtime_registered,
        "UNKNOWN does not imply runtime registration",
    )
    assert_false(
        unknown_condition.negative_evidence_allowed,
        "negative evidence defaults disabled",
    )
    assert_false(
        unknown_condition.legal_absence_inference_allowed,
        "legal absence inference defaults disabled",
    )
    assert_false(
        unknown_condition.site_promotion_allowed,
        "SITE promotion defaults disabled",
    )

    # Malformed/missing resolver state fails closed to UNKNOWN, never FALSE.
    malformed = normalize_production_site_condition(
        name="synthetic malformed",
        condition_type="SITE",
        resolution_type="SNAPSHOT",
        state="NO_HIT",
    )
    assert_equal(malformed.state, UNKNOWN, "malformed state fails closed")

    missing = normalize_production_site_condition(
        name="synthetic missing",
        condition_type="SITE",
        resolution_type="SNAPSHOT",
        state=None,
    )
    assert_equal(missing.state, UNKNOWN, "missing state fails closed")

    # Explicit TRUE/FALSE are preserved, but neither state manufactures eligibility.
    explicit_true = normalize_production_site_condition(
        name="synthetic true",
        condition_type="SITE",
        resolution_type="SPATIAL",
        state=TRUE,
    )
    assert_equal(explicit_true.state, TRUE, "explicit TRUE preservation")
    assert_false(
        explicit_true.production_eligible,
        "TRUE does not imply production eligibility",
    )

    explicit_false = normalize_production_site_condition(
        name="synthetic false",
        condition_type="SITE",
        resolution_type="SPATIAL",
        state=FALSE,
    )
    assert_equal(explicit_false.state, FALSE, "explicit FALSE preservation")
    assert_false(
        explicit_false.production_eligible,
        "FALSE does not imply production eligibility",
    )

    # Eligibility/registration are explicit independent gates.
    eligible_not_registered = normalize_production_site_condition(
        name="synthetic eligible",
        condition_type="SITE",
        resolution_type="SPATIAL",
        state=UNKNOWN,
        production_eligible=True,
        runtime_registered=False,
    )
    assert_true(
        eligible_not_registered.production_eligible,
        "explicit production eligibility preserved",
    )
    assert_false(
        eligible_not_registered.runtime_registered,
        "eligibility does not imply registration",
    )
    assert_equal(
        eligible_not_registered.state,
        UNKNOWN,
        "eligibility does not promote UNKNOWN",
    )

    # SITE_HISTORY cannot masquerade as a spatial runtime condition.
    historical = normalize_production_site_condition(
        name="도시지역편입해제구역",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
        state=UNKNOWN,
    )
    assert_equal(historical.state, UNKNOWN, "historical UNKNOWN preservation")
    assert_false(
        historical.runtime_registered,
        "historical condition not runtime registered by contract",
    )

    spatial_history_rejected = False
    try:
        ProductionSiteCondition(
            name="invalid historical spatial",
            condition_type="SITE_HISTORY",
            resolution_type="SPATIAL",
        )
    except ValueError:
        spatial_history_rejected = True
    assert_true(
        spatial_history_rejected,
        "SITE_HISTORY spatial runtime contract rejected",
    )

    # Rule Engine view keeps existing state/confidence/source semantics only.
    view = rule_engine_condition_view(unknown_condition)
    assert_equal(view["name"], "개발밀도관리구역", "Rule Engine name")
    assert_equal(view["type"], "SITE", "Rule Engine type")
    assert_equal(view["state"], UNKNOWN, "Rule Engine UNKNOWN")
    assert_equal(
        set(view.keys()),
        {"name", "type", "state", "confidence", "source"},
        "Rule Engine minimal view",
    )

    # Diagnostic evidence is preserved but is non-dispositive.
    assert_true(
        unknown_condition.diagnostics.get("search_no_hit") is True,
        "diagnostic evidence preserved",
    )
    assert_equal(
        unknown_condition.state,
        UNKNOWN,
        "diagnostic evidence cannot manufacture FALSE",
    )

    print("=" * 72)
    print("STEP 18 PRODUCTION SITE CONDITION CONTRACT REGRESSION")
    print("=" * 72)
    print("UNKNOWN preservation: PASS")
    print("Malformed/missing state fail-closed: PASS")
    print("TRUE/FALSE do not imply production eligibility: PASS")
    print("Production eligibility does not imply runtime registration: PASS")
    print("SITE_HISTORY spatial runtime registration path blocked: PASS")
    print("Negative/legal absence/SITE promotion defaults disabled: PASS")
    print("Rule Engine minimal state view preserved: PASS")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
