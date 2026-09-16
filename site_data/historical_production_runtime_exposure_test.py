"""Reconcile STEP67 service exposure with the verified PNU envelope."""
from __future__ import annotations
import copy
from types import SimpleNamespace
from api_app import SiteAnalysisRequest
from law_data.historical_site_event_builder_injection_payload import CHANNEL,PROVENANCE
from law_data.historical_verified_rule_input_envelope import seal_verified_historical_rule_input
from law_data.rule_evaluation_pipeline import evaluate_site_rules
from site_data.site_analysis_orchestrator import analyze_site_by_parcel
from site_data.site_analysis_service import analyze_site_object

PNU="1168010300100120000"
def check(name,passed):
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
    if not passed:raise AssertionError(name)
def site():return SimpleNamespace(site_id="STEP67-TEST-SITE",address="STEP67 TEST",road_address="",sigungu_cd="11680",bjdong_cd="10300",bun="0012",ji="0000",land=None)
def find_target(result):
    occupied=set(result.get("rule_engine",{}).get("site_registry",{}))
    for rule in evaluate_site_rules().get("rules",[]):
        for c in rule.get("conditions",[]) if isinstance(rule,dict) else []:
            name=str(c.get("name","")).strip() if isinstance(c,dict) else ""
            if name and name not in occupied:return name
    raise AssertionError("No non-spatial Rule Engine condition")
def raw(condition):return {"channel":CHANNEL,"provenance":PROVENANCE,"repairs":[{"condition":condition,"after":"UNKNOWN","new_confidence":"STEP67_TEST","new_source":PROVENANCE,"pnu":PNU}]}
def fields():return getattr(SiteAnalysisRequest,"model_fields",None) or getattr(SiteAnalysisRequest,"__fields__",{})

def main():
    s=site(); legacy=analyze_site_object(s); check("Legacy service path preserved","historical" not in legacy.get("input",{})); target=find_target(legacy); value=raw(target); before=copy.deepcopy(value)
    raw_blocked=False
    try:analyze_site_object(s,historical_rule_input=value)
    except ValueError:raw_blocked=True
    check("Raw historical service injection blocked",raw_blocked)
    env=seal_verified_historical_rule_input(canonical_pnu=PNU,historical_rule_input=value); integrated=analyze_site_object(s,historical_rule_input=env)
    repairs=[r for r in integrated.get("rule_engine",{}).get("site_repairs",[]) if r.get("condition")==target]
    check("Verified service-to-Rule-Engine consumption",bool(repairs) and all(r.get("new_confidence")=="STEP67_TEST" and r.get("new_source")==PROVENANCE for r in repairs)); check("Historical provenance preserved",bool(repairs) and all(r.get("new_source")==PROVENANCE for r in repairs)); check("Dedicated historical input preserved",integrated.get("input",{}).get("historical")==before); check("Caller historical input immutable",value==before)
    cross=False
    try:analyze_site_object(s,historical_rule_input=seal_verified_historical_rule_input(canonical_pnu="1168010300100130000",historical_rule_input=value))
    except ValueError:cross=True
    check("Cross-PNU service envelope blocked",cross)
    runtime=integrated.get("site",{}).get("runtime_conditions",{}); leak=any(isinstance(v,dict) and (v.get("source")==PROVENANCE or v.get("provenance")==PROVENANCE) for v in runtime.values()); check("Historical provenance absent from spatial runtime channel",not leak)
    import inspect
    check("Service historical seam remains internal", "historical_rule_input" in inspect.signature(analyze_site_object).parameters); check("Orchestrator raw historical seam absent","historical_rule_input" not in inspect.signature(analyze_site_by_parcel).parameters); check("API historical field absent","historical_rule_input" not in fields())
    print("HISTORICAL_PRODUCTION_VERIFIED_ENVELOPE_EXPOSURE_PASS")
if __name__=="__main__":main()
