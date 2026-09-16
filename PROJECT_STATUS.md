# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-09-16
기준 branch: `cleanup/repository-organization-20260916`
기준 behavioral PASS HEAD: `29967e6fbde26bb6d3839bc2202ad363fb41bdf5`
보존 checkpoint branch: `checkpoint/c12-fastapi-20260821`
보존 STEP114 HEAD: `ad06db07cf22138e5324eb263ae666814520eb53`
Architecture Baseline: v1.2

## 1. 현재 단계

STEP114 behavioral validation 이후 provenance-bound SITE applicability와 historical production wiring을 fail-closed로 연결했고, 이후 실제 SITE PNU 재결합, candidate↔repair 상태 일치, candidate↔condition identity 결합까지 구현·검증했다.

STEP114 이후 기능 경계에는 아직 새 architecture STEP 번호를 부여하지 않는다.

현재 locally validated 흐름:

```text
STEP98 Evidence→Seed admission
→ STEP101 verified classification→profile admission
→ STEP103 registry classification compatibility
→ STEP104 resolver-family eligibility
→ STEP106 dispatch plan
→ STEP108 input admission
→ STEP110 resolver execution
→ STEP112 resolver result verification
→ STEP114 SITE-decision eligibility
→ historical parcel applicability evidence
→ PNU-bound SITE applicability admission
→ actual SITE PNU rebinding
→ candidate↔repair consistency authorization
→ candidate↔condition binding authorization
→ admitted historical rule-input adapter
→ existing service / builder / Rule Engine consumption path
```

핵심 user-local behavioral validation:
- `STEP114_PROVENANCE_BOUND_SITE_DECISION_ELIGIBILITY_CONTRACT_PASS`
- `PROVENANCE_BOUND_SITE_APPLICABILITY_ADMISSION_CONTRACT_PASS`
- `HISTORICAL_SITE_EVENT_PARCEL_APPLICABILITY_EVIDENCE_CONTRACT_PASS`
- `HISTORICAL_SITE_EVENT_SITE_APPLICABILITY_ADMISSION_CONTRACT_PASS`
- `HISTORICAL_SITE_EVENT_ADMITTED_RULE_INPUT_ADAPTER_CONTRACT_PASS`
- `SITE_ANALYSIS_ORCHESTRATOR_SITE_APPLICABILITY_WIRING_CONTRACT_PASS`
- `SITE_ANALYSIS_ORCHESTRATOR_CANONICAL_PNU_REBINDING_CONTRACT_PASS`
- `HISTORICAL_SITE_EVENT_CANDIDATE_REPAIR_CONSISTENCY_AUTHORIZATION_CONTRACT_PASS`
- `SITE_ANALYSIS_ORCHESTRATOR_CANDIDATE_REPAIR_CONSISTENCY_WIRING_CONTRACT_PASS`
- `HISTORICAL_SITE_EVENT_CANDIDATE_CONDITION_BINDING_AUTHORIZATION_CONTRACT_PASS`
- `SITE_ANALYSIS_ORCHESTRATOR_CANDIDATE_CONDITION_BINDING_WIRING_CONTRACT_PASS`
- STEP74 historical trusted internal source handoff E2E reconciliation PASS at `29967e6...`

## 2. Current safety boundary

```text
resolver result ≠ parcel applicability
SITE-decision eligibility ≠ SITE truth
SITE applicability admission ≠ production/runtime registration authority
```

Historical production 경로:

```text
trusted historical handoff
+
PNU-bound SITE applicability ADMITTED
↓
actual Site object PNU == admitted canonical PNU
↓
candidate state == trusted repair state
↓
all trusted repairs identify one unambiguous condition
↓
admitted historical rule-input adapter READY
↓
existing service → builder → historical registry / Rule Engine path
```

Fail-closed 차단:
- raw `historical_rule_input` orchestrator 직접 주입
- handoff/applicability 한쪽만 존재
- cross-PNU 또는 실제 Site PNU 재결합 실패
- UNKNOWN/unverified parcel applicability
- candidate와 repair state 불일치
- 서로 다른 historical condition identity가 repair에 혼재
- unauthorized/forged handoff
- public API historical input
- historical spatial runtime registration
- admission/binding 결과만으로 SITE truth mutation/promotion

중요: candidate↔condition binding은 condition 이름을 새로 만들지 않는다. 기존 trusted repair의 condition identity가 하나로 명확한지만 검증한다.

## 3. Historical safety / real condition locks

Public API historical exposure remains NOT AUTHORIZED.
Historical data remains excluded from the spatial runtime condition channel.

### 도시지역편입해제구역
- resolution family: `HISTORICAL_SITE_EVENT`
- standard code: None / UNVERIFIED / DO NOT GUESS
- unresolved real-condition evidence remains fail-closed
- production/runtime registration remains BLOCKED unless later evidence and authorization explicitly support it

### 개발밀도관리구역 / UQQ700
- resolution family: `HYBRID_SPATIAL_NOTICE`
- standard code: `UQQ700`
- current legal-source resolution remains UNKNOWN
- negative evidence / legal absence inference disabled
- SITE TRUE/FALSE promotion remains blocked without required verified evidence
- production/runtime registration remains blocked
- minimum gate: official designation identity + current validity + SITE spatial inclusion verification
- historical production reconciliation does not activate UQQ700 or move it to `HISTORICAL_SITE_EVENT`

Legal-source investigation numbering (`S206`…`S216`/future S217) is separate from architecture STEP numbering.

## 4. Architecture state

Architecture Baseline remains v1.2. No new architecture STEP number is assigned.

The current historical-family reconciliation is:

```text
STEP114 verified FALSE candidate
+
canonical SITE/PNU + verified parcel evidence
→ SITE applicability admission
→ actual-SITE PNU rebinding
→ candidate/repair consistency
→ candidate/condition identity binding
→ admitted historical Rule Input adapter
→ existing production consumption architecture
```

This does not create a second SITE truth path. Existing trusted repairs remain the Rule Engine input source. The newer boundaries only determine whether those repairs are safe to forward for the current SITE and candidate.

## 5. Production wiring reconciliation

`site_data/site_analysis_orchestrator.py` requires both typed historical inputs when historical processing is requested:
- `historical_handoff_authorization`
- `historical_site_applicability_admission`

The orchestrator now checks, in order:
1. actual Site PNU rebinding
2. candidate↔repair state consistency
3. candidate↔condition identity binding
4. admitted historical rule-input adapter readiness

Only then is the existing `historical_rule_input` shape forwarded to `site_analysis_service` / builder.

Unchanged production components:
- `site_data/site_analysis_service.py`
- `law_data/site_analysis_builder.py`
- downstream historical registry / Rule Engine integration
- public API request schema

STEP74 E2E was reconciled to the current FALSE-only STEP114 eligibility contract and passed locally at HEAD `29967e6fbde26bb6d3839bc2202ad363fb41bdf5`.

## 6. Repository cleanup checkpoint

Cleanup branch: `cleanup/repository-organization-20260916`
Cleanup started from STEP114 checkpoint: `ad06db07cf22138e5324eb263ae666814520eb53`

Validated cleanup remains unchanged. Do not mechanically move/delete `law_data/*` or `site_data/*` for cosmetic cleanup without dependency/path audit and separate approval.

## 7. Documentation state

This update reconciles the status document through actual-SITE PNU rebinding, candidate/repair consistency, candidate/condition binding, and the current STEP74 E2E PASS. Architecture Baseline remains v1.2 and no new STEP number is invented.

## 8. Git / local rules

Repository: `jehun0620-bot/site-ai`
Current branch: `cleanup/repository-organization-20260916`
Preserved checkpoint: `checkpoint/c12-fastapi-20260821`
Local root: `D:\site-ai`

GitHub/local write requires explicit scope/purpose/non-target approval.
Never modify/commit `.env`, `law_data/output/*`, or unrelated files.
Never use `git add .`, `git add -A`, or `git add --all`.

Protected local-only modified file:
`law_data/output/urban_area_conversion_history_final_resolution.json`

Expected state:
```text
 M law_data/output/urban_area_conversion_history_final_resolution.json
```

Never modify, restore, checkout, reset, delete, stage, commit, or clean this protected file.
User local execution PASS remains final behavioral validation.

## 9. Standard development process

```text
READ-ONLY audit
→ exact WRITE scope approval when needed
→ IMPLEMENT
→ remote HEAD confirm
→ local protected-file check
→ git pull --ff-only
→ py_compile / focused contracts / necessary regressions
→ final protected-file check
→ user-local PASS
→ next READ-ONLY audit
```

## 10. Next action

READ-ONLY design audit of the next real gap after PNU/state/condition binding. Priorities:
1. distinguish SITE truth/promotion authorization from admission and Rule Engine consumption
2. determine whether any additional identity/provenance binding is required before promotion can even be designed
3. preserve public API and spatial-runtime historical boundaries
4. preserve UQQ700 UNKNOWN/BLOCKED policy
5. avoid a second SITE truth path
6. do not assign a new STEP number without explicit repository design

## 11. Handoff policy

In a new chat, reconstruct actual branch HEAD and current files from GitHub READ-ONLY first. Current GitHub code plus user-local execution results override stale summaries/documents.

Preserve cleanup branch, STEP114 checkpoint, Architecture Baseline v1.2, post-STEP114 safety gates, no invented STEP number, protected local output modification, fail-closed invariants, and explicit WRITE approval.
