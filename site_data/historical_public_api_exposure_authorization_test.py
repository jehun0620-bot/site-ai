"""STEP69 historical public API exposure authorization boundary audit."""
from __future__ import annotations

import inspect

from pydantic import ValidationError

from api_app import (
    SiteAnalysisRequest,
    site_analysis,
)
from site_data.site_analysis_orchestrator import (
    analyze_site_by_parcel,
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


def request_payload():
    return {
        "sigungu_cd": "11680",
        "bjdong_cd": "10300",
        "bun": "0012",
        "ji": "0000",
        "project_profile": {},
        "procedure_profile": {},
        "include_debug": False,
    }


def build_request(payload):
    validator = getattr(
        SiteAnalysisRequest,
        "model_validate",
        None,
    )

    if validator is not None:
        return validator(payload)

    return SiteAnalysisRequest.parse_obj(
        payload
    )


def dumped_request(request):
    dumper = getattr(
        request,
        "model_dump",
        None,
    )

    if dumper is not None:
        return dumper()

    return request.dict()


def main():
    print("=" * 72)
    print(
        "STEP 69 HISTORICAL PUBLIC API "
        "EXPOSURE AUTHORIZATION"
    )
    print("=" * 72)

    # --------------------------------------------------------
    # Current public request contract
    # --------------------------------------------------------

    fields = api_fields()

    check(
        "Public API historical field absent",
        HISTORICAL_FIELD not in fields,
    )

    legacy = build_request(
        request_payload()
    )

    check(
        "Legacy public request contract preserved",
        (
            legacy.sigungu_cd == "11680"
            and legacy.bjdong_cd == "10300"
            and legacy.bun == "0012"
            and legacy.ji == "0000"
        ),
    )

    check(
        "Legacy public request dump historical field absent",
        HISTORICAL_FIELD
        not in dumped_request(legacy),
    )

    # --------------------------------------------------------
    # Caller-supplied historical payload must not become
    # part of the typed public request contract.
    #
    # Pydantic may reject or ignore unknown fields depending
    # on the installed/configured version. Either behavior is
    # acceptable here, provided the field cannot survive as
    # part of the typed public request model.
    # --------------------------------------------------------

    injected_payload = request_payload()
    injected_payload[HISTORICAL_FIELD] = {
        "channel": "FORGED_PUBLIC_CHANNEL",
        "provenance": "FORGED_PUBLIC_PROVENANCE",
        "repairs": [],
    }

    rejected = False
    injected_request = None

    try:
        injected_request = build_request(
            injected_payload
        )
    except ValidationError:
        rejected = True

    if rejected:
        public_injection_blocked = True
    else:
        public_injection_blocked = (
            HISTORICAL_FIELD
            not in dumped_request(
                injected_request
            )
            and not hasattr(
                injected_request,
                HISTORICAL_FIELD,
            )
        )

    check(
        "Raw historical caller injection unavailable",
        public_injection_blocked,
    )

    # --------------------------------------------------------
    # Endpoint boundary
    # --------------------------------------------------------

    endpoint_source = inspect.getsource(
        site_analysis
    )

    check(
        "Endpoint historical forwarding absent",
        HISTORICAL_FIELD
        not in endpoint_source,
    )

    # --------------------------------------------------------
    # Internal boundary remains available after STEP68
    # --------------------------------------------------------

    orchestrator_parameters = (
        inspect.signature(
            analyze_site_by_parcel
        ).parameters
    )

    check(
        "Internal orchestrator historical seam preserved",
        HISTORICAL_FIELD
        in orchestrator_parameters,
    )

    check(
        "Historical seam remains internal-only",
        (
            HISTORICAL_FIELD
            in orchestrator_parameters
            and HISTORICAL_FIELD
            not in fields
            and HISTORICAL_FIELD
            not in endpoint_source
        ),
    )

    print(
        "Public API historical input exposure: "
        "NOT AUTHORIZED"
    )

    print(
        "Production API / orchestrator / service / builder / "
        "Rule Engine mutation: NONE"
    )

    print(
        "CLASSIFICATION: "
        "STEP69_HISTORICAL_PUBLIC_API_EXPOSURE_"
        "AUTHORIZATION_BOUNDARY_RECONCILED"
    )


if __name__ == "__main__":
    main()
