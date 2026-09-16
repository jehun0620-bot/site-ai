"""STEP69 historical public API exposure authorization boundary audit."""
from __future__ import annotations

import inspect

from pydantic import ValidationError

from api_app import SiteAnalysisRequest, site_analysis
from site_data.site_analysis_orchestrator import analyze_site_by_parcel

RAW_FIELD = "historical_rule_input"
HANDOFF_FIELD = "historical_handoff_authorization"
APPLICABILITY_FIELD = "historical_site_applicability_admission"


def check(name, passed):
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
    if not passed:
        raise AssertionError(name)


def api_fields():
    fields = getattr(SiteAnalysisRequest, "model_fields", None)
    if fields is None:
        fields = getattr(SiteAnalysisRequest, "__fields__", {})
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
    validator = getattr(SiteAnalysisRequest, "model_validate", None)
    if validator is not None:
        return validator(payload)
    return SiteAnalysisRequest.parse_obj(payload)


def dumped_request(request):
    dumper = getattr(request, "model_dump", None)
    if dumper is not None:
        return dumper()
    return request.dict()


def main():
    print("=" * 72)
    print("STEP 69 HISTORICAL PUBLIC API EXPOSURE AUTHORIZATION")
    print("=" * 72)

    fields = api_fields()
    for field in (RAW_FIELD, HANDOFF_FIELD, APPLICABILITY_FIELD):
        check(f"Public API {field} absent", field not in fields)

    legacy = build_request(request_payload())
    check(
        "Legacy public request contract preserved",
        legacy.sigungu_cd == "11680" and legacy.bjdong_cd == "10300"
        and legacy.bun == "0012" and legacy.ji == "0000",
    )

    for field in (RAW_FIELD, HANDOFF_FIELD, APPLICABILITY_FIELD):
        injected = request_payload()
        injected[field] = {"forged": True}
        rejected = False
        request = None
        try:
            request = build_request(injected)
        except ValidationError:
            rejected = True
        blocked = rejected or (
            field not in dumped_request(request) and not hasattr(request, field)
        )
        check(f"Public caller injection blocked: {field}", blocked)

    endpoint_source = inspect.getsource(site_analysis)
    for field in (RAW_FIELD, HANDOFF_FIELD, APPLICABILITY_FIELD):
        check(f"Endpoint forwarding absent: {field}", field not in endpoint_source)

    parameters = inspect.signature(analyze_site_by_parcel).parameters
    check("Raw historical orchestrator seam removed", RAW_FIELD not in parameters)
    check("Typed handoff internal seam preserved", HANDOFF_FIELD in parameters)
    check(
        "Typed SITE applicability internal seam preserved",
        APPLICABILITY_FIELD in parameters,
    )
    check(
        "Historical seams remain internal-only",
        HANDOFF_FIELD not in fields
        and APPLICABILITY_FIELD not in fields
        and HANDOFF_FIELD not in endpoint_source
        and APPLICABILITY_FIELD not in endpoint_source,
    )

    print("Public API historical input exposure: NOT AUTHORIZED")
    print("Production API mutation / spatial runtime registration: NONE")
    print(
        "CLASSIFICATION: "
        "STEP69_HISTORICAL_PUBLIC_API_EXPOSURE_"
        "AUTHORIZATION_BOUNDARY_RECONCILED"
    )


if __name__ == "__main__":
    main()
