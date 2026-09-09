from __future__ import annotations

import sys
from pathlib import Path


LAW_DATA_DIR = Path(__file__).resolve().parent
if str(LAW_DATA_DIR) not in sys.path:
    sys.path.insert(0, str(LAW_DATA_DIR))

from historical_site_event_history_completeness_verifier import (  # noqa: E402
    HistoricalHistoryCompletenessEvidence,
    verify_history_completeness,
)


def main() -> int:
    all_true = verify_history_completeness(
        HistoricalHistoryCompletenessEvidence(
            official_historical_source_set_verified=True,
            authority_time_scope_completeness_verified=True,
            required_original_documents_resolved=True,
            candidate_universe_exhaustively_enumerated=True,
        )
    )

    missing_source_set = verify_history_completeness(
        HistoricalHistoryCompletenessEvidence(
            official_historical_source_set_verified=False,
            authority_time_scope_completeness_verified=True,
            required_original_documents_resolved=True,
            candidate_universe_exhaustively_enumerated=True,
        )
    )

    missing_scope = verify_history_completeness(
        HistoricalHistoryCompletenessEvidence(
            official_historical_source_set_verified=True,
            authority_time_scope_completeness_verified=False,
            required_original_documents_resolved=True,
            candidate_universe_exhaustively_enumerated=True,
        )
    )

    missing_originals = verify_history_completeness(
        HistoricalHistoryCompletenessEvidence(
            official_historical_source_set_verified=True,
            authority_time_scope_completeness_verified=True,
            required_original_documents_resolved=False,
            candidate_universe_exhaustively_enumerated=True,
        )
    )

    missing_universe = verify_history_completeness(
        HistoricalHistoryCompletenessEvidence(
            official_historical_source_set_verified=True,
            authority_time_scope_completeness_verified=True,
            required_original_documents_resolved=True,
            candidate_universe_exhaustively_enumerated=False,
        )
    )

    diagnostics_only = verify_history_completeness(
        HistoricalHistoryCompletenessEvidence(),
        search_no_hit=True,
        http_200=True,
        fetched_row_count=43508,
        negative_evidence={
            "all_candidates_non_target": True,
            "unresolved_candidates": 0,
        },
    )

    checks = {
        "all four positive gates verify history completeness": (
            all_true["history_scope_complete_verified"] is True
            and all_true["positive_gate_count"] == 4
        ),
        "missing official source set fails closed": (
            missing_source_set["history_scope_complete_verified"] is False
        ),
        "missing authority/time scope fails closed": (
            missing_scope["history_scope_complete_verified"] is False
        ),
        "missing required originals fails closed": (
            missing_originals["history_scope_complete_verified"] is False
        ),
        "missing candidate universe enumeration fails closed": (
            missing_universe["history_scope_complete_verified"] is False
        ),
        "row count and no-hit cannot manufacture completeness": (
            diagnostics_only["history_scope_complete_verified"] is False
            and diagnostics_only["positive_gate_count"] == 0
        ),
        "diagnostic discovery remains non-dispositive": (
            diagnostics_only["diagnostic_discovery"]["dispositive"] is False
        ),
        "generic negative inference stays disabled": all(
            result["generic_negative_inference_allowed"] is False
            for result in (
                all_true,
                missing_source_set,
                missing_scope,
                missing_originals,
                missing_universe,
                diagnostics_only,
            )
        ),
        "discovery cannot infer legal absence": all(
            result["legal_absence_inference_from_discovery_allowed"] is False
            for result in (
                all_true,
                missing_source_set,
                missing_scope,
                missing_originals,
                missing_universe,
                diagnostics_only,
            )
        ),
        "verifier remains production-unwired": all(
            result["production_wiring_applied"] is False
            and result["runtime_registry_mutated"] is False
            for result in (
                all_true,
                missing_source_set,
                missing_scope,
                missing_originals,
                missing_universe,
                diagnostics_only,
            )
        ),
    }

    all_pass = all(checks.values())

    print("=" * 72)
    print("HISTORICAL SITE EVENT HISTORY COMPLETENESS VERIFIER")
    print("=" * 72)
    for name, passed in checks.items():
        print(f"{name}: {passed}")
    print("-" * 72)
    print(f"all_pass: {all_pass}")
    print(
        "CLASSIFICATION: "
        + (
            "HISTORICAL_SITE_EVENT_HISTORY_COMPLETENESS_VERIFIER_PASS"
            if all_pass
            else "HISTORICAL_SITE_EVENT_HISTORY_COMPLETENESS_VERIFIER_FAIL"
        )
    )

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
