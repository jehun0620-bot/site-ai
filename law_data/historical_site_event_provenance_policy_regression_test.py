from __future__ import annotations

from law_data.historical_site_event_provenance_policy import (
    HistoricalSiteEventProvenanceEvidence,
    evaluate_historical_site_event_provenance_policy,
)


def main() -> None:
    print("=" * 72)
    print("HISTORICAL SITE EVENT PROVENANCE POLICY")
    print("=" * 72)

    empty = evaluate_historical_site_event_provenance_policy(
        HistoricalSiteEventProvenanceEvidence()
    )

    all_verified = evaluate_historical_site_event_provenance_policy(
        HistoricalSiteEventProvenanceEvidence(
            source_authority_identity_verified=True,
            source_role_explicit=True,
            document_identity_traceable=True,
            original_document_traceable=True,
            site_applicability_traceable=True,
            temporal_relation_traceable=True,
        )
    )

    weak_diagnostics = evaluate_historical_site_event_provenance_policy(
        HistoricalSiteEventProvenanceEvidence(),
        candidate_hit=True,
        title_match=True,
        http_200=True,
        source_url_present=True,
        archive_candidate_present=True,
    )

    each_gate_required = True
    gate_names = list(all_verified["gates"])
    for missing_gate in gate_names:
        kwargs = {name: True for name in gate_names}
        kwargs[missing_gate] = False
        result = evaluate_historical_site_event_provenance_policy(
            HistoricalSiteEventProvenanceEvidence(**kwargs)
        )
        each_gate_required = each_gate_required and (
            result["provenance_policy_verified"] is False
            and missing_gate in result["missing_gates"]
        )

    checks = {
        "empty provenance evidence is blocked": empty["provenance_policy_verified"] is False,
        "all six provenance gates are required": each_gate_required,
        "all six verified gates satisfy provenance policy": all_verified["provenance_policy_verified"] is True,
        "verified gate count is six": all_verified["verified_gate_count"] == 6,
        "required gate count is six": all_verified["required_gate_count"] == 6,
        "verified provenance has no missing gates": all_verified["missing_gates"] == [],
        "weak diagnostics cannot manufacture provenance": weak_diagnostics["provenance_policy_verified"] is False,
        "diagnostics remain non-dispositive": weak_diagnostics["diagnostics"]["dispositive"] is False,
        "candidate cannot manufacture authority identity": weak_diagnostics["promotion_guards"]["candidate_promoted_to_authority_identity"] is False,
        "title cannot manufacture document identity": weak_diagnostics["promotion_guards"]["title_promoted_to_document_identity"] is False,
        "HTTP 200 cannot manufacture authority identity": weak_diagnostics["promotion_guards"]["http_200_promoted_to_authority_identity"] is False,
        "URL cannot manufacture source role": weak_diagnostics["promotion_guards"]["source_url_promoted_to_source_role"] is False,
        "archive candidate cannot manufacture original traceability": weak_diagnostics["promotion_guards"]["archive_candidate_promoted_to_original_traceability"] is False,
        "provenance cannot manufacture verified event identity": all_verified["promotion_guards"]["provenance_promoted_to_verified_event_identity"] is False,
        "provenance cannot manufacture SITE applicability": all_verified["promotion_guards"]["provenance_promoted_to_site_applicability"] is False,
        "provenance cannot manufacture temporal relation": all_verified["promotion_guards"]["provenance_promoted_to_temporal_relation"] is False,
        "provenance cannot manufacture history completeness": all_verified["promotion_guards"]["provenance_promoted_to_history_completeness"] is False,
        "negative and legal absence inference remain disabled": all_verified["negative_evidence_inference_allowed"] is False and all_verified["legal_absence_inference_allowed"] is False,
        "verified provenance never applies SITE promotion": all_verified["site_promotion_applied"] is False,
        "verified provenance never applies production wiring": all_verified["production_wiring_applied"] is False,
        "verified provenance never mutates overlay": all_verified["overlay_mutated"] is False,
        "verified provenance never mutates runtime registry": all_verified["runtime_registry_mutated"] is False,
    }

    for label, passed in checks.items():
        print(f"{label}: {passed}")

    all_pass = all(checks.values())

    print("-" * 72)
    print(f"all_pass: {all_pass}")
    print(
        "CLASSIFICATION: "
        + (
            "HISTORICAL_SITE_EVENT_PROVENANCE_POLICY_PASS"
            if all_pass
            else "HISTORICAL_SITE_EVENT_PROVENANCE_POLICY_FAIL"
        )
    )

    if not all_pass:
        raise AssertionError("historical provenance policy regression failed")


if __name__ == "__main__":
    main()
