import copy
from law_data.historical_site_event_rule_engine_consumption_executor import execute_historical_site_event_rule_engine_consumption
from law_data.historical_site_event_rule_engine_consumption_execution_package_test import _package
CLASSIFICATION="STEP55_HISTORICAL_SITE_EVENT_RULE_ENGINE_CONSUMPTION_EXECUTOR_BOUNDARY_RECONCILED"
def main():
    rules=[{"clause_index":1,"conditions":[{"name":"역사조건","type":"SITE_HISTORY","state":"UNKNOWN","confidence":"LOW","source":"BASE"}]}]
    original=copy.deepcopy(rules); changed=execute_historical_site_event_rule_engine_consumption(_package(False),rules); assert changed.execution_succeeded and changed.apply_site_registry_called and rules==original and changed.actual_repair_count==1
    executed=changed.executed_rules[0]["conditions"][0]; assert executed["state"]=="TRUE" and executed["confidence"]=="HIGH" and executed["source"]=="RUNTIME_HISTORICAL_SITE_EVENT"
    noop_rules=[]; noop=execute_historical_site_event_rule_engine_consumption(_package(True),noop_rules); assert noop.execution_succeeded and not noop.apply_site_registry_called and noop_rules==[]
    drift=copy.deepcopy(rules); drift[0]["conditions"][0]["source"]="DRIFT"; blocked=execute_historical_site_event_rule_engine_consumption(_package(False),drift); assert not blocked.execution_succeeded and not blocked.apply_site_registry_called
    assert not execute_historical_site_event_rule_engine_consumption(None,rules).execution_succeeded
    print("="*72); print("STEP 55 HISTORICAL SITE EVENT RULE ENGINE CONSUMPTION EXECUTOR"); print("="*72); print("Changed-target deep-copy Rule Engine consumption: PASS"); print("Zero-op execution without apply_site_registry: PASS"); print("Current-rules TOCTOU drift fail-closed: PASS"); print("Authorized repair / affected rule alignment: PASS"); print("Original rules immutability: PASS"); print("apply_site_registry on deep-copy rules: PASS"); print("Production builder / runtime registration / API: NONE"); print(f"CLASSIFICATION: {CLASSIFICATION}")
if __name__=="__main__": main()
