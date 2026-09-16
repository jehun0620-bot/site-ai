# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-09-16
기준 branch: `cleanup/repository-organization-20260916`
기준 개발 HEAD: `eb24b15939b40ca37516915d4734ac45f68c3f7f` (문서 갱신 직전 behavioral PASS HEAD)
보존 checkpoint branch: `checkpoint/c12-fastapi-20260821`
보존 STEP114 HEAD: `ad06db07cf22138e5324eb263ae666814520eb53`
Architecture Baseline: v1.2

## 1. 현재 단계

STEP114 behavioral validation 이후의 provenance-bound SITE applicability 및 historical production wiring reconciliation까지 완료했다.

STEP114 이후 구현/검증된 기능 경계에는 아직 새 architecture STEP 번호를 부여하지 않는다.

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
→ admitted historical rule-input adapter
→ typed trusted handoff + applicability orchestrator gate
→ existing service / builder / Rule Engine consumption path
```

핵심 behavioral validation:
- `STEP114_PROVENANCE_BOUND_SITE_DECISION_ELIGIBILITY_CONTRACT_PASS`
- `PROVENANCE_BOUND_SITE_APPLICABILITY_ADMISSION_CONTRACT_PASS`
- `HISTORICAL_SITE_EVENT_PARCEL_APPLICABILITY_EVIDENCE_CONTRACT_PASS`
- `HISTORICAL_SITE_EVENT_SITE_APPLICABILITY_ADMISSION_CONTRACT_PASS`
- `HISTORICAL_SITE_EVENT_ADMITTED_RULE_INPUT_ADAPTER_CONTRACT_PASS`
- `SITE_ANALYSIS_ORCHESTRATOR_SITE_APPLICABILITY_WIRING_CONTRACT_PASS`
- STEP68 historical orchestrator exposure reconciliation PASS
- STEP69 historical public API exposure reconciliation PASS
- STEP73 trusted handoff production wiring reconciliation PASS
- STEP74 trusted handoff end-to-end reconciliation PASS
- STEP67 production runtime exposure regression PASS

Latest user-local behavioral PASS HEAD before this documentation update:
`eb24b15939b40ca37516915d4734ac45f68c3f7f`

## 2. Current safety boundary

다음 불변조건이 현재 구현과 regression에서 유지된다.

```text
resolver result ≠ parcel applicability
SITE-decision eligibility ≠ SITE truth
SITE applicability admission ≠ production/runtime registration authority
```

Historical production 경로는 이제 fail-closed다.

```text
trusted historical handoff
+
PNU-bound SITE applicability ADMITTED
↓
admitted historical rule-input adapter READY
↓
orchestrator
↓
existing service
↓
existing builder
↓
existing historical registry / Rule Engine path
```

차단 상태:
- raw `historical_rule_input` orchestrator 직접 주입
- trusted handoff 단독 production 진입
- applicability admission 단독 production 진입
- cross-PNU / unbound parcel evidence
- UNKNOWN / unverified parcel applicability
- public API historical input
- historical spatial runtime registration
- admission 결과만으로 SITE truth mutation/promotion

일반 SITE 분석은 historical 입력이 없으면 기존 경로를 그대로 사용한다.

## 3. Historical safety / real condition locks

PHASE 8의 evidence-driven 안전 원칙은 유지된다.
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
- minimum gate remains official designation identity + current validity + SITE spatial inclusion verification
- current historical production reconciliation does not activate UQQ700 or move it into `HISTORICAL_SITE_EVENT`

Legal-source investigation numbering (`S206`…`S216`/future S217) is separate from architecture STEP numbering and must not be conflated.

## 4. Architecture state

Architecture Baseline remains v1.2.

The former STEP114→SITE/PNU applicability gap is no longer an implementation gap for the historical-family contract path. The implemented reconciliation is:

```text
STEP114 verified candidate
+
canonical SITE identity / PNU
+
family-specific parcel applicability evidence
↓
fail-closed SITE applicability admission
↓
admitted historical Rule Input adapter
↓
existing production consumption architecture
```

This does not create a second SITE truth path. The adapter emits the existing historical Rule Engine input shape only after applicability and trusted handoff gates pass.

No new architecture STEP number is assigned by this reconciliation. A future numbered STEP must be established explicitly by repository documentation/design rather than inferred from sequence.

Remaining evidence-driven work includes condition-specific official evidence resolution, verified authority/source mappings where needed, and eventual SITE truth/promotion authorization contracts. Those are not implied by the current admission/wiring PASS.

## 5. Production wiring reconciliation

`site_data/site_analysis_orchestrator.py` now requires both typed historical inputs when the historical path is requested:
- `historical_handoff_authorization`
- `historical_site_applicability_admission`

If neither is present, normal analysis continues.
If only one is present, or applicability/handoff validation fails, historical production admission fails closed.

The orchestrator uses `historical_site_event_admitted_rule_input_adapter` before forwarding the existing `historical_rule_input` shape to `site_analysis_service` / builder.

Unchanged production components:
- `site_data/site_analysis_service.py`
- `law_data/site_analysis_builder.py`
- downstream historical registry / Rule Engine integration
- public API request schema

STEP68/69/73/74 regression contracts were reconciled to this new boundary and passed locally. STEP67 lower-path runtime exposure regression also remained PASS.

## 6. Repository cleanup checkpoint

Cleanup branch:
`cleanup/repository-organization-20260916`

Cleanup started from exact STEP114 checkpoint:
`ad06db07cf22138e5324eb263ae666814520eb53`

Previously validated cleanup batches remain valid:
- obsolete root probes `hello.py`, `api_test.py` deleted
- obsolete Building HUB probes `main.py`, `building_api_test.py`, `building_api_parse.py` deleted
- obsolete `regulations/test_regulation_data.py` deleted
- `land_api_test.py` retained
- `regulations/residential_zones.py` retained
- `law_data/*` investigation/provenance families retained

Do not mechanically move/delete `law_data/*` or `site_data/*` for cosmetic cleanup without dependency/path audit and separate approval.

## 7. Documentation state

This update reconciles `PROJECT_STATUS.md` with the user-locally validated state through provenance-bound SITE applicability, admitted historical Rule Input adaptation, orchestrator production gating, and STEP67/68/69/73/74 regressions.

`PROJECT_ARCHITECTURE.md` is reconciled separately in the same approved documentation scope. Architecture Baseline remains v1.2; no new STEP number is invented.

## 8. Git / local rules

Repository: `jehun0620-bot/site-ai`
Current cleanup branch: `cleanup/repository-organization-20260916`
Preserved development checkpoint branch: `checkpoint/c12-fastapi-20260821`
Local root: `D:\site-ai`

GitHub/local write requires explicit scope/purpose/non-target approval.

Never modify/commit:
- `.env`
- `law_data/output/*`
- unrelated files

Never use bulk staging such as `git add .`, `git add -A`, or `git add --all`.

Protected local-only modified file:
`law_data/output/urban_area_conversion_history_final_resolution.json`

It must not be modified, restored, checked out, reset, deleted, staged, committed, or removed by clean operations.

Expected protected local state:

```text
 M law_data/output/urban_area_conversion_history_final_resolution.json
```

User local execution PASS remains the final behavioral validation standard.

## 9. Standard development process

```text
IMPLEMENT
→ REMOTE HEAD CONFIRM
→ LOCAL git status --short
→ protected file remains M
→ git pull --ff-only
→ protected file remains M
→ target file existence/signature check
→ py_compile
→ focused contract test
→ necessary regressions
→ final git status --short
→ user local PASS confirmation
→ closure
→ next READ-ONLY audit
```

Stop on pull conflict/refusal. Do not use stash/restore/reset/checkout/clean as a workaround for the protected file.

## 10. Next action

READ-ONLY design audit before assigning any new STEP or implementation scope.

Audit priorities:
1. identify the next real evidence/production gap after PNU-bound historical admission wiring
2. distinguish SITE truth/promotion authorization from admission and Rule Engine consumption
3. preserve public API and spatial-runtime historical boundaries
4. preserve UQQ700 UNKNOWN/BLOCKED policy
5. avoid a second SITE truth or production path
6. only after the audit, propose exact files and purpose for explicit WRITE approval

## 11. Handoff policy

In a new chat, reconstruct actual branch HEAD and current files from GitHub READ-ONLY first. Current GitHub code plus user-local execution results override stale summaries/documents.

Preserve:
- cleanup branch and preserved STEP114 checkpoint
- Architecture Baseline v1.2
- STEP114 provenance chain
- post-STEP114 PNU-bound applicability/admitted-rule-input/production-wiring behavioral PASS
- no invented next STEP number
- protected local output modification
- fail-closed safety invariants
- explicit Git write approval rule
