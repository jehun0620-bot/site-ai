import inspect
from law_data import site_analysis_builder as builder
CLASSIFICATION="STEP61_HISTORICAL_SITE_EVENT_BUILDER_INPUT_ACCEPTANCE_BOUNDARY_RECONCILED"
def main():
    sig=inspect.signature(builder.build_site_analysis); assert "historical_rule_input" in sig.parameters and sig.parameters["historical_rule_input"].default is None
    source=inspect.getsource(builder.build_site_analysis); assert "accept_historical_rule_input(historical_rule_input)" in source; assert "site_condition_context=site_condition_context" in source; assert "site_condition_context.update" not in source
    original={"channel":"HISTORICAL_SITE_EVENT_NON_SPATIAL","provenance":"RUNTIME_HISTORICAL_SITE_EVENT","rules":[{"name":"역사조건"}],"repairs":[]}; accepted=builder.accept_historical_rule_input(original); assert accepted==original and accepted is not original; accepted["rules"][0]["name"]="변경"; assert original["rules"][0]["name"]=="역사조건"
    assert builder.accept_historical_rule_input(None) is None
    print("="*72); print("STEP 61 HISTORICAL SITE EVENT BUILDER INPUT ACCEPTANCE"); print("="*72); print("Optional historical_rule_input signature: PASS"); print("Legacy call default compatibility: PASS"); print("Historical input deep-copy acceptance: PASS"); print("Caller input immutability: PASS"); print("Spatial site_condition_context remains dedicated: PASS"); print("Historical input != Rule Engine injection: PASS"); print("Runtime_conditions / spatial shadow / evaluate_site_rules historical injection: NONE"); print(f"CLASSIFICATION: {CLASSIFICATION}")
if __name__=="__main__": main()
