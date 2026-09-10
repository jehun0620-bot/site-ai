# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-09-10
기준 branch: `checkpoint/c12-fastapi-20260821`
기준 개발 HEAD: `038858c388421bfdf2d854b6002514cecf25540d`

> 현재 개발 상태와 안전 불변조건을 기록한다. 장기 로드맵은 `PROJECT_ARCHITECTURE.md` 기준.

## 1. 현재 단계

```text
STEP 23
Focus: REGULATION_SOURCE_POLICY_REQUIREMENT_BOUNDARY + HISTORICAL_PROVENANCE_INTEGRATION
State: TERMINALLY CLOSED
Terminal classification: STEP23_REGULATION_SOURCE_POLICY_REQUIREMENT_BOUNDARY_TERMINALLY_RECONCILED
Validated classifications:
- STEP23_REGULATION_SOURCE_POLICY_REQUIREMENT_BOUNDARY_PASS
- STEP23_REGULATION_SOURCE_POLICY_REQUIREMENT_PROVENANCE_INTEGRATION_PASS
- STEP23_REGULATION_SOURCE_POLICY_REQUIREMENT_BOUNDARY_TERMINALLY_RECONCILED
```

STEP 18/19/20/22/23는 사용자 로컬 검증까지 완료되어 TERMINALLY CLOSED 상태다.

```text
STEP18_PRODUCTION_SITE_CONDITION_BOUNDARY_TERMINALLY_RECONCILED
STEP19_REGULATION_RESOLUTION_PROFILE_BOUNDARY_TERMINALLY_RECONCILED
STEP20_AUTHORITY_SOURCE_SCOPE_BOUNDARY_TERMINALLY_RECONCILED
STEP22_REGULATION_AUTHORITY_REQUIREMENT_BOUNDARY_TERMINALLY_RECONCILED
STEP23_REGULATION_SOURCE_POLICY_REQUIREMENT_BOUNDARY_TERMINALLY_RECONCILED
```

STEP 21 architecture baseline reconciliation도 완료되었다.

```text
Architecture Baseline: v1.2
Classification: STEP21_ARCHITECTURE_BASELINE_PROFILE_AUTHORITY_SCOPE_RECONCILED
```

STEP 17 terminal targets remain legally unresolved and fail-closed:

```text
개발밀도관리구역 / UQQ700
- Resolution type: HYBRID_SPATIAL_NOTICE
- Current resolution: UNKNOWN
- Runtime registration: BLOCKED

도시지역편입해제구역
- Resolution type: HISTORICAL_SITE_EVENT
- Standard code: UNVERIFIED / DO NOT GUESS
- Current resolution: UNKNOWN / MEDIUM
- Production wiring: BLOCKED
- Runtime registration: BLOCKED
```

## 2. STEP 18 production SITE condition boundary — TERMINALLY CLOSED

STEP 18 generalized the production-facing SITE condition contract without changing Rule Engine dispositive semantics.

Implemented chain:

```text
SPATIAL runtime condition
→ production spatial adapter
→ ProductionSiteCondition
                         \
                          → common shadow collector
                          → site_analysis_builder
                          → site_analysis_service passthrough
                          → site_analysis_orchestrator passthrough
                          → INTERNAL production_condition_contracts
                         /
pre-normalized SITE_HISTORY production contract
```

The builder does not execute or interpret raw historical resolvers. Historical producer/resolver execution remains outside the builder/service/orchestrator boundary.

Local terminal validation PASS:

```text
STEP18_PRODUCTION_SITE_CONDITION_BOUNDARY_TERMINALLY_RECONCILED
```

## 3. STEP 19 regulation resolution profile boundary — TERMINALLY CLOSED

STEP 19 introduced a pure read-only metadata boundary for regulation-resolution identity and policy requirements.

Implemented chain:

```text
condition identity
→ RegulationResolutionProfile
→ immutable exact-name profile registry
→ condition-specific readiness adapter metadata lookup
→ existing common readiness gate
```

This chain is metadata/readiness only.

```text
profile lookup
≠ resolver execution
≠ SITE state resolution
≠ production registration
≠ runtime registration
≠ Rule Engine input
≠ public API exposure
```

### 3.1 RegulationResolutionProfile contract

Common profile metadata:

```text
name
condition_type: SITE | SITE_HISTORY
resolution_type: SNAPSHOT | SPATIAL | HYBRID_SPATIAL_NOTICE | HISTORICAL_SITE_EVENT
standard_code: str | None
standard_code_verified
authority_requirements
source_policy_requirements
authority_identity_verified
source_policy_verified
negative_evidence_allowed
legal_absence_inference_allowed
site_promotion_allowed
production_registration_allowed
runtime_registration_allowed
diagnostics
```

Safety defaults remain fail-closed:

```text
standard_code missing → None
standard_code_verified=False unless explicit code exists
negative_evidence_allowed=False
legal_absence_inference_allowed=False
site_promotion_allowed=False
production_registration_allowed=False
runtime_registration_allowed=False
```

A profile never manufactures SITE state and never guesses a standard code.

### 3.2 Immutable profile registry

Built-in registry is immutable and exact-name only.

```text
known exact condition name → profile
empty / alias / partial / standard-code lookup → None
unknown condition → None
mutation API → NONE
resolver/evaluate/promote/runtime API → NONE
```

Current built-in profiles:

```text
개발밀도관리구역
- condition_type: SITE
- resolution_type: HYBRID_SPATIAL_NOTICE
- standard_code: UQQ700
- standard_code_verified: True
- authority_identity_verified: False
- source_policy_verified: False
- negative_evidence_allowed: False
- legal_absence_inference_allowed: False
- site_promotion_allowed: False
- production_registration_allowed: False
- runtime_registration_allowed: False

도시지역편입해제구역
- condition_type: SITE_HISTORY
- resolution_type: HISTORICAL_SITE_EVENT
- standard_code: None
- standard_code_verified: False
- production_registration_allowed: False
- runtime_registration_allowed: False
```

Known UQQ700 profile identity does not mean official designation/current validity/SITE applicability is verified.

### 3.3 Historical readiness integration

`urban_area_conversion_production_readiness_adapter.py` reads condition identity and standard-code verification from the immutable profile registry.

Current gates remain:

```text
condition_identity_verified             = True
standard_code_verified                  = False
positive_evidence_contract_ready        = True
history_completeness_contract_ready     = True
provenance_policy_verified              = False
runtime_registration_policy_verified    = False

verified gates = 3 / 6
production_wiring_ready = False
readiness_state = BLOCKED
```

Profile presence is identity metadata only and does not verify evidence/provenance/runtime policy.

## 4. STEP 19 validated classifications

User local PASS:

```text
STEP19_REGULATION_RESOLUTION_PROFILE_BOUNDARY_PASS
STEP19_REGULATION_RESOLUTION_PROFILE_REGISTRY_PASS
STEP19_REGULATION_RESOLUTION_PROFILE_READINESS_INTEGRATION_PASS
STEP19_REGULATION_RESOLUTION_PROFILE_BOUNDARY_TERMINALLY_RECONCILED
```

Terminal audit confirms:

```text
Profile contract SITE-state manufacture: NONE
Immutable exact-name registry boundary: PASS
Unknown/alias/code inference: NONE
Historical standard code: ABSENT / UNVERIFIED
Historical production readiness: BLOCKED
UQQ700 identity/profile safety locks: PRESERVED
Profile registry -> spatial runtime registry wiring: NONE
Builder/service/orchestrator/public API auto-wiring: NONE
Resolver/SITE/runtime mutation: NONE
```

## 5. STEP 20 authority/source scope boundary — TERMINALLY CLOSED

STEP 20 introduced a pure, fail-closed source qualification boundary for competent-authority and source-scope metadata.

Implemented qualification chain:

```text
OFFICIAL HOST
→ REGION BINDING
→ SOURCE ROLE
→ LEGAL AUTHORITY SCOPE
→ TARGET REGULATION COMPATIBILITY
→ authority_chain_verified
```

The boundary separates descriptive metadata from independently verified authority facts.

```text
official-looking host
≠ competent authority

region metadata
≠ verified region binding

PRIMARY / SECONDARY role value
≠ verified source role

authority scope text
≠ verified legal authority

target regulation metadata
≠ verified compatibility

source discovered / candidate hit / title match / archive hit
≠ authority verification
```

### 5.1 AuthoritySourceScope contract

`law_data/authority_source_scope.py` provides immutable/read-only authority-source qualification metadata.

Core fields:

```text
source_uri
source_host
official_host_verified
region_binding
region_binding_verified
source_role
source_role_verified
legal_authority_scope
legal_authority_scope_verified
target_regulation
target_regulation_compatible
target_regulation_compatibility_verified
authority_chain_verified
diagnostics
```

Positive authority-chain verification requires every positive gate to be explicitly verified and target compatibility to be positively verified TRUE.

Missing/no-hit evidence does not become incompatibility and does not justify negative legal inference.

### 5.2 Historical provenance integration

`urban_area_conversion_provenance_policy_adapter.py` binds descriptive source metadata through `AuthoritySourceScope` before creating historical provenance evidence.

Current behavior remains fail-closed:

```text
Diagnostic URL/candidate/title/archive -> authority verification: NONE
Official-looking host -> competent authority promotion: NONE
Source-role metadata -> verified role promotion: NONE
Authority chain verified: FALSE
Historical provenance state: BLOCKED
```

Verification-looking fields in diagnostic payloads are not imported as authority verification.

### 5.3 Authority registry status

No authority/source registry was introduced in STEP 20.

`PROJECT_ARCHITECTURE.md` treats authority/source registries as future candidates rather than current requirements. A registry should only be introduced after a separately justified architecture/data decision with verified authority mappings.

## 6. STEP 20 validated classifications

User local PASS:

```text
STEP20_AUTHORITY_SOURCE_SCOPE_BOUNDARY_PASS
STEP20_AUTHORITY_SOURCE_SCOPE_PROVENANCE_INTEGRATION_PASS
STEP20_AUTHORITY_SOURCE_SCOPE_BOUNDARY_TERMINALLY_RECONCILED
```

## 7. STEP 21 architecture baseline reconciliation — COMPLETE

`PROJECT_ARCHITECTURE.md` was reconciled to Architecture Baseline v1.2 after STEP 19/20 closure.

Key architecture locks:

```text
RegulationResolutionProfile
≠ resolver execution
≠ SITE state
≠ production registration
≠ runtime registration

AuthoritySourceScope
≠ authority registry
≠ SITE state
≠ resolver execution
≠ runtime registration

registry presence
≠ authority verification evidence
```

PHASE 7/8 architecture checkpoints were updated to reflect profile and authority/source scope boundaries while keeping verified authority/source registry integration as a future separately justified step.

Classification:

```text
STEP21_ARCHITECTURE_BASELINE_PROFILE_AUTHORITY_SCOPE_RECONCILED
```

## 8. STEP 22 regulation authority requirement boundary — TERMINALLY CLOSED

STEP 22 adds the missing fail-closed binding between `RegulationResolutionProfile` and `AuthoritySourceScope`.

Implemented chain:

```text
RegulationResolutionProfile
        +
AuthoritySourceScope
        ↓
RegulationAuthorityRequirementAssessment
        ↓
authority_requirement_satisfied
```

`authority_requirement_satisfied=True` is allowed only when all of the following are true:

```text
profile exists
AND profile declares authority requirements
AND exact profile name == scope target regulation
AND AuthoritySourceScope authority_chain_verified == True
```

Safety locks:

```text
profile name match
≠ authority verified

official-looking host / PRIMARY / authority text
≠ authority verified

partial authority chain
≠ authority requirement satisfied

verified incompatibility
≠ positive authority

verified authority for another regulation
≠ current regulation authority

source_policy_requirements
≠ source-policy evidence satisfied
```

The boundary does not resolve SITE state, evaluate spatial/history source-policy evidence, infer legal absence, or grant production/runtime registration.

User local PASS:

```text
STEP22_REGULATION_AUTHORITY_REQUIREMENT_BOUNDARY_PASS
STEP22_REGULATION_AUTHORITY_REQUIREMENT_PROVENANCE_INTEGRATION_PASS
STEP22_REGULATION_AUTHORITY_REQUIREMENT_BOUNDARY_TERMINALLY_RECONCILED
```

Terminal audit confirms:

```text
Missing profile/scope fail-closed: PASS
Profile/scope descriptive identity -> authority verification: NONE
Official-looking host / PRIMARY / authority text promotion: NONE
Cross-regulation verified authority reuse: BLOCKED
Positive authority requirement: EXPLICIT VERIFIED MATCHING CHAIN ONLY
Source-policy requirement auto-satisfaction: NONE
Historical standard code: ABSENT / UNVERIFIED
Historical provenance state: BLOCKED
Negative/legal absence/SITE promotion: NONE
Production/runtime mutation: NONE
UQQ700 cross-condition wiring: NONE
Builder/service/orchestrator/public API/spatial runtime auto-wiring: NONE
Authority registry requirement: NONE
```

## 9. STEP 22 historical provenance integration — VALIDATED AND CLOSED WITH BOUNDARY

`urban_area_conversion_provenance_policy_adapter.py` binds the exact-name regulation profile and condition-specific `AuthoritySourceScope` through `RegulationAuthorityRequirementAssessment` before constructing the historical provenance authority gate.

Current flow:

```text
RegulationResolutionProfile
        +
AuthoritySourceScope
        ↓
RegulationAuthorityRequirementAssessment
        ↓
authority_requirement_satisfied
        ↓
HistoricalSiteEventProvenanceEvidence.source_authority_identity_verified
        ↓
Historical provenance policy
```

Current result remains fail-closed:

```text
profile_present=True
condition_identity_aligned=True
authority_chain_verified=False
authority_requirement_satisfied=False
historical standard code=None / UNVERIFIED
historical provenance=BLOCKED
SITE promotion=NONE
production/runtime mutation=NONE
```

Verification-looking diagnostic fields still do not enter `AuthoritySourceScope` verification gates.

STEP 22 has not introduced an authority registry, runtime wiring, production promotion, or public API exposure.

## 10. STEP 23 regulation source-policy requirement boundary — TERMINALLY CLOSED

STEP 23 adds the common fail-closed binding between `RegulationResolutionProfile.source_policy_requirements` and independently verified positive requirement facts.

Implemented chain:

```text
RegulationResolutionProfile.source_policy_requirements
        +
explicit independently verified requirement facts
        ↓
RegulationSourcePolicyRequirementAssessment
        ↓
source_policy_requirement_satisfied
```

Positive satisfaction is allowed only when the profile exists, declares a non-empty requirement set, and every exact declared requirement has an explicit boolean `True` fact.

Safety locks:

```text
requirement declared
≠ requirement verified

profile source_policy_verified=True
≠ individual requirement fact verified

contract implemented / contract ready
≠ evidence satisfied

partial facts
≠ source-policy requirement satisfied

truthy non-bool values
≠ verified requirement facts

unrelated verified facts
≠ declared requirement satisfaction

empty requirement declaration
≠ vacuous TRUE

source-policy requirement satisfied
≠ legal resolution
≠ SITE state
≠ production/runtime registration
```

Historical profile requirements remain:

```text
HISTORY COMPLETENESS VERIFIED
PROVENANCE VERIFIED
```

The historical provenance adapter binds these requirements read-only. It does not verify history completeness itself, and provenance verification is sourced only from the common historical provenance policy result.

Current historical result remains:

```text
history completeness verified by provenance adapter=False
historical provenance=BLOCKED
verified source-policy requirements=[]
missing source-policy requirements=[HISTORY COMPLETENESS VERIFIED, PROVENANCE VERIFIED]
source_policy_requirement_satisfied=False
historical standard code=None / UNVERIFIED
SITE promotion=NONE
production/runtime mutation=NONE
```

User local PASS:

```text
STEP23_REGULATION_SOURCE_POLICY_REQUIREMENT_BOUNDARY_PASS
STEP23_REGULATION_SOURCE_POLICY_REQUIREMENT_PROVENANCE_INTEGRATION_PASS
STEP23_REGULATION_SOURCE_POLICY_REQUIREMENT_BOUNDARY_TERMINALLY_RECONCILED
```

Terminal audit confirms:

```text
Missing profile / empty requirement declaration fail-closed: PASS
Requirement declaration -> verification: NONE
Profile source_policy_verified flag -> requirement satisfaction: NONE
Partial / truthy / unrelated facts -> requirement satisfaction: NONE
Positive source-policy requirement: ALL DECLARED EXPLICIT TRUE FACTS ONLY
Historical standard code: ABSENT / UNVERIFIED
Historical provenance state: BLOCKED
History completeness verified by provenance adapter: FALSE
Historical source-policy requirement satisfied: FALSE
Negative/legal absence/SITE promotion: NONE
Production/runtime mutation: NONE
UQQ700 cross-condition wiring: NONE
Builder/service/orchestrator/public API/spatial runtime auto-wiring: NONE
Source-policy registry/mutation requirement: NONE
```

## 11. Rule Engine / production / runtime isolation

Existing Rule Engine semantics remain unchanged:

```text
FALSE   → blocked_by → NOT_APPLICABLE
UNKNOWN → unknown_by → UNKNOWN
UNSET   → CONDITIONAL
else    → APPLICABLE

NOT_APPLICABLE → INACTIVE
CONDITIONAL    → POTENTIAL_CONDITIONAL
UNKNOWN        → POTENTIAL_UNKNOWN
else           → ACTIVE_CANDIDATE
```

STEP 18/19/20/22/23 do not replace `site_condition_context` with production/profile/authority/source-policy contracts.

```text
production_condition_contracts
≠ Rule Engine site_condition_context

regulation_resolution_profile_registry
≠ spatial runtime registry

authority_source_scope
≠ spatial runtime registry
≠ SITE condition state
≠ resolver result

regulation_authority_requirement
≠ legal resolution
≠ SITE condition state
≠ production/runtime permission

regulation_source_policy_requirement
≠ verified legal evidence
≠ legal resolution
≠ SITE condition state
≠ production/runtime permission
```

No STEP 19/20/22/23 auto-wiring exists in builder/service/orchestrator/public API.

## 12. UQQ700 safety invariants — unchanged

Target: `개발밀도관리구역 / UQQ700`

```text
Resolution type: HYBRID_SPATIAL_NOTICE
Current resolution: UNKNOWN
negative_evidence_allowed=False
legal_absence_inference_allowed=False
site_false_inference_allowed=False
site_promotion_allowed=False
production_registration_allowed=False
runtime_registration_allowed=False
```

Minimum positive registration gate remains:

```text
OFFICIAL DESIGNATION IDENTITY VERIFIED
AND CURRENT VALIDITY VERIFIED
AND SITE SPATIAL INCLUSION VERIFIED
```

Current verified evidence remains insufficient:

```text
official_designation_identity_verified=False
current_validity_verified=False
site_spatial_inclusion_verified=False
minimum_registration_gate_satisfied=False
```

Known profile/code identity and STEP 20/22/23 metadata/requirement contracts do not satisfy any of these three positive evidence gates.

## 13. 도시지역편입해제구역 safety invariants — unchanged

```text
Resolution type: HISTORICAL_SITE_EVENT
Standard code: UNVERIFIED / DO NOT GUESS
Profile standard_code: None
Profile standard_code_verified: False
Current resolution: UNKNOWN / MEDIUM
verified qualifying historical event = False
history scope completeness verified = False
provenance policy verified = False
authority chain verified = False
authority requirement satisfied = False
source-policy requirement satisfied = False
production wiring = BLOCKED
runtime registration = BLOCKED
```

Preserve:

```text
TRUE_CANDIDATE ≠ production TRUE
contract readiness ≠ evidence verified
current geometry ≠ historical SITE applicability
search no-hit ≠ legal absence
source discovery ≠ competent authority verification
profile/scope identity alignment ≠ competent authority verification
requirement declaration ≠ requirement verification
```

## 14. STEP 17 terminal closure remains binding

```text
CLASSIFICATION: STEP17_TERMINAL_CLOSURE_AUDIT_PASS
STEP 17 state: TERMINALLY CLOSED
```

Do not repeat without new official positive evidence:

```text
UQQ700 closed/concluded source-family probing
UQQ700 spatial source/code guessing
도시지역편입해제구역 source-family re-probing
standard-code guessing
search/no-hit based FALSE inference
legal absence inference
SITE promotion
runtime registration
```

## 15. Core semantic locks

```text
condition name known
≠ standard code verified

profile exists
≠ resolver exists
≠ SITE applicability verified
≠ runtime support
≠ authority verified

profile metadata verified
≠ legal evidence verified

official-looking host
≠ competent authority

source discovered
≠ source role verified

authority compatible metadata
≠ legal evidence verified

region/source-role/authority-scope metadata present
≠ corresponding verification gate passed

profile/scope identity aligned
≠ authority requirement satisfied

authority requirement satisfied
≠ source-policy evidence satisfied
≠ legal resolution
≠ SITE state
≠ runtime registration

source-policy requirement declared
≠ source-policy requirement verified

source-policy requirement satisfied
≠ legal evidence verified
≠ legal resolution
≠ SITE state
≠ runtime registration

announcement/query success
≠ official historical source set verified

originals resolved
≠ history complete

candidate/document/current state
≠ verified qualifying historical event

TRUE_CANDIDATE
≠ production TRUE

contract implementation ready
≠ actual legal evidence satisfied

diagnostic provenance preserved
≠ production provenance policy verified

production readiness READY
≠ production wiring applied

runtime registration policy verified
≠ runtime registration applied

current geometry
≠ historical SITE applicability

production shadow collected
≠ production eligibility

internal production shadow
≠ public API legal fact
```

## 16. Architecture state

```text
PHASE 0 Foundation              COMPLETE
PHASE 1 Building/SITE           COMPLETE
PHASE 2 Land/Spatial            CORE COMPLETE
PHASE 3 SITE Analysis           CORE COMPLETE
PHASE 4 Legal ingestion         IN PROGRESS
PHASE 5 Rule Engine             CORE STABLE / IN PROGRESS
PHASE 6 Runtime spatial         CORE STABLE
PHASE 7 Regulation Resolution   ACTIVE / PROFILE + AUTHORITY + SOURCE-POLICY REQUIREMENT BOUNDARIES CLOSED
PHASE 8 Authority/Historical    ACTIVE / AUTHORITY SOURCE SCOPE + HISTORICAL PROVENANCE BINDINGS CLOSED
PHASE 9+ Nationwide/AI/Product  FUTURE
```

Development order remains:

```text
OFFICIAL FACT
→ SITE FACT
→ REGULATION RESOLUTION
→ LEGAL RULE
→ DETERMINISTIC ENGINE
→ AI ANALYSIS
→ VERIFICATION
```

## 17. Next allowed work after STEP 23 closure

```text
1. Keep STEP 18, STEP 19, STEP 20, STEP 22, and STEP 23 boundaries TERMINALLY CLOSED unless a new architecture decision or new positive evidence justifies reopening a relevant boundary.
2. Keep UQQ700 and 도시지역편입해제구역 UNKNOWN / blocked from production/runtime registration.
3. Select the next development step only after a read-only gap audit against current HEAD and Architecture Baseline v1.2.
4. Do not create authority/source/source-policy registries merely because common requirement boundaries exist; require independently verified mappings/provenance and a separate architecture/data decision.
5. Do not connect profile/authority/authority-requirement/source-policy-requirement metadata to the spatial runtime registry.
6. Do not auto-wire profile/authority/source-policy lookup into builder/service/orchestrator/public API.
7. Do not expose production_condition_contracts, resolution profiles, authority/source scope, authority-requirement assessments, or source-policy-requirement assessments as public legal facts in SITE_ANALYSIS_API_V1 without a separate schema decision.
8. Do not auto-run blocked historical producers from builder/service/orchestrator.
9. Contract readiness must never substitute for actual provenance/history/source-policy evidence verification.
10. New official positive evidence may reopen a relevant terminal condition only through its existing positive verification gates.
```

## 18. Git / local rules

Repository: `jehun0620-bot/site-ai`
Branch: `checkpoint/c12-fastapi-20260821`
Local root: `D:\site-ai`

```text
GitHub write 직전 exact file scope / purpose / non-targets 설명 후 사용자 승인 필수
.env 수정/commit 금지
law_data/output/* 수정/commit 금지
git add . 금지
git add -A 금지
git add --all 금지
intended files만 명시적으로 stage/commit
Large mutable output/PDF/HWP/HWPX commit 금지
```

Known local dirty tracked output must remain untouched unless the user explicitly directs otherwise:

```text
law_data/output/urban_area_conversion_history_final_resolution.json
```

## 19. Handoff policy

Use the latest `PROJECT_STATUS.md` when moving to a new chat. Do not create unnecessary handoff documents.

Minimum handoff content:

```text
repo / branch / local root
latest commit
current STEP / validated classification
STEP 18 terminal state
STEP 19 terminal state
STEP 20 terminal state
STEP 21 architecture baseline reconciliation
STEP 22 terminal state
STEP 23 terminal state
UQQ700 safety invariants
historical SITE_EVENT safety invariants
authority/source scope safety invariants
regulation authority requirement safety invariants
regulation source-policy requirement safety invariants
closed/concluded source families / DO-NOT-REPEAT
current unresolved external evidence gaps
next exact allowed action
Git write approval rule
```
