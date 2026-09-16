"""Reconcile STEP66 builder historical handoff with the verified PNU envelope."""
from __future__ import annotations
import copy
from law_data.historical_site_event_builder_injection_payload import CHANNEL, PROVENANCE
from law_data.historical_verified_rule_input_envelope import seal_verified_historical_rule_input
from law_data.rule_evaluation_pipeline import evaluate_site_rules
from law_data.site_analysis_builder import build_site_analysis

PNU="1168010300100120000"
SITE_INPUT={"sigungu_code":"11680","bjdong_code":"10300","main_no":"0012","sub_no":"0000","pnu":PNU}

def check(name,passed):
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
    if not passed: raise AssertionError(name)
def find_target(result):
    occupied=set(result.get("rule_engine",{}).get("site_registry",{}))
    for rule in evaluate_site_rules().get("rules",[]):
        for c in rule.get("conditions",[]) if isinstance(rule,dict) else []:
            name=str(c.get("name","")).strip() if isinstance(c,dict) else ""
            if name and name not in occupied:return name
    raise AssertionError("No non-spatial Rule Engine condition")
def raw(condition,state="UNKNOWN",confidence="STEP66_TEST",source=PROVENANCE):
    return {"channel":CHANNEL,"provenance":PROVENANCE,"repairs":[{"condition":condition,"after":state,"new_confidence":confidence,"new_source":source,"pnu":PNU}]}
def envelope(value,pnu=PNU):return seal_verified_historical_rule_input(canonical_pnu=pnu,historical_rule_input=value)

def main():
    legacy=build_site_analysis(site_input=SITE_INPUT); check("Legacy builder path preserved","historical" not in legacy.get("input",{}))
    target=find_target(legacy); value=raw(target); before=copy.deepcopy(value)
    raw_blocked=False
    try:build_site_analysis(site_input=SITE_INPUT,historical_rule_input=value)
    except ValueError:raw_blocked=True
    check("Raw historical builder injection blocked",raw_blocked)
    integrated=build_site_analysis(site_input=SITE_INPUT,historical_rule_input=envelope(value))
    repairs=[r for r in integrated.get("rule_engine",{}).get("site_repairs",[]) if r.get("condition")==target]
    check("Verified historical builder-to-Rule-Engine consumption",bool(repairs) and all(r.get("new_confidence")=="STEP66_TEST" and r.get("new_source")==PROVENANCE for r in repairs))
    check("Historical input preserved",integrated.get("input",{}).get("historical")==before); check("Caller input immutable",value==before)
    wrong_pnu=False
    try:build_site_analysis(site_input=SITE_INPUT,historical_rule_input=envelope(value,"1168010300100130000"))
    except ValueError:wrong_pnu=True
    check("Cross-PNU envelope blocked",wrong_pnu)
    malformed=False
    try:build_site_analysis(site_input=SITE_INPUT,historical_rule_input=envelope(raw(target,source="FORGED_SOURCE")))
    except ValueError:malformed=True
    check("Malformed sealed input fail-closed",malformed)
    spatial=evaluate_site_rules().get("site_registry",{})
    if not spatial:raise AssertionError("No spatial registry entry for collision test")
    name=next(iter(spatial)); state="FALSE" if spatial[name].get("state")!="FALSE" else "TRUE"; collision=False
    try:build_site_analysis(site_input=SITE_INPUT,historical_rule_input=envelope(raw(name,state,"STEP66_COLLISION_TEST")))
    except ValueError:collision=True
    check("Spatial/historical collision fail-closed",collision)
    print("HISTORICAL_RULE_ENGINE_VERIFIED_ENVELOPE_HANDOFF_PASS")
if __name__=="__main__":main()
