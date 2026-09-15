"""STEP70 historical internal source authorization boundary audit."""
from __future__ import annotations

import inspect

from api_app import SiteAnalysisRequest
from site_data.site_analysis_orchestrator import (
    analyze_site_by_parcel,
)
from site_data.site_analysis_service import (
    analyze_site_object,
)


HISTORICAL_FIELD = "historical_rule_input"


def check(name, passed):
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

    if not passed:
        raise AssertionError(name)


def api_fields():
    fields = getattr(
        SiteAnalysisRequest,
        "model_fields",
        None,
    )

    if fields is None:
        fields = getattr(
            SiteAnalysisRequest,
            "__fields__",
            {},
        )

    return fields


def parameter(function, name):
    return inspect.signature(
        function
    ).parameters.get(name)


def annotation_is_any_optional(parameter_value):
    if parameter_value is None:
        return False

    annotation_text = str(
        parameter_value.annotation
    )

    return (
        "Any" in annotation_text
        and (
            "Optional" in annotation_text
            or "None" in annotation_text
        )
    )


def main():
    print("=" * 72)
    print(
        "STEP 70 HISTORICAL INTERNAL SOURCE "
        "AUTHORIZATION"
    )
    print("=" * 72)

    # --------------------------------------------------------
    # Existing internal seams
    # --------------------------------------------------------

    orchestrator_parameter = parameter(
        analyze_site_by_parcel,
        HISTORICAL_FIELD,
    )

    service_parameter = parameter(
        analyze_site_object,
        HISTORICAL_FIELD,
    )

    check(
        "Historical orchestrator seam present",
        orchestrator_parameter is not None,
    )

    check(
        "Historical service seam present",
        service_parameter is not None,
    )

    # --------------------------------------------------------
    # Public API remains closed after STEP69
    # --------------------------------------------------------

    check(
        "Public API historical seam absent",
        HISTORICAL_FIELD not in api_fields(),
    )

    # --------------------------------------------------------
    # Current internal seam is generic transport, not a
    # trusted producer/source authorization contract.
    #
    # STEP70 does not authorize a producer merely because
    # downstream historical validation is fail-closed.
    # --------------------------------------------------------

    check(
        "Orchestrator historical seam remains generic",
        annotation_is_any_optional(
            orchestrator_parameter
        ),
    )

    check(
        "Service historical seam remains generic",
        annotation_is_any_optional(
            service_parameter
        ),
    )

    orchestrator_source = inspect.getsource(
        analyze_site_by_parcel
    )

    service_source = inspect.getsource(
        analyze_site_object
    )

    producer_authorization_markers = (
        "historical_source_authorization",
        "historical_producer_authorization",
        "trusted_historical_source",
        "trusted_historical_producer",
    )

    trusted_wiring_absent = not any(
        marker in orchestrator_source
        or marker in service_source
        for marker in producer_authorization_markers
    )

    check(
        "Trusted production source/producer wiring absent",
        trusted_wiring_absent,
    )

    check(
        "Internal seam does not itself establish source trust",
        (
            orchestrator_parameter is not None
            and service_parameter is not None
            and annotation_is_any_optional(
                orchestrator_parameter
            )
            and annotation_is_any_optional(
                service_parameter
            )
            and trusted_wiring_absent
        ),
    )

    print(
        "Raw internal historical producer authorization: "
        "NOT YET AUTHORIZED"
    )

    print(
        "Public API exposure / production source wiring / "
        "spatial runtime registration: NONE"
    )

    print(
        "Production wiring mutation: NONE"
    )

    print(
        "CLASSIFICATION: "
        "STEP70_HISTORICAL_INTERNAL_SOURCE_"
        "AUTHORIZATION_BOUNDARY_RECONCILED"
    )


if __name__ == "__main__":
    main()
