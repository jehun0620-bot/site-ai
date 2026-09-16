# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-09-16
기준 branch: `cleanup/repository-organization-20260916`
기준 개발 HEAD: `50678cf55a8345e96ebb42a7084a61c3ae1aa90d` (문서 갱신 직전 cleanup HEAD)
보존 checkpoint branch: `checkpoint/c12-fastapi-20260821`
보존 STEP114 HEAD: `ad06db07cf22138e5324eb263ae666814520eb53`
Architecture Baseline: v1.2

## 1. 현재 단계

STEP114 behavioral validation까지 완료/종료.

Latest terminal implementation:
`STEP114_PROVENANCE_BOUND_SITE_DECISION_ELIGIBILITY`

STEP114 validation:
- local fast-forward / target HEAD verification PASS
- py_compile PASS
- focused contract PASS
- marker: `STEP114_PROVENANCE_BOUND_SITE_DECISION_ELIGIBILITY_CONTRACT_PASS`
- final git status contained only the protected expected local output modification
- protected output file remained modified and untouched

STEP98 이후 locally validated provenance chain:

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
→ STOP
```

STEP114 conclusion:
- verified resolver result may produce a candidate SITE-decision eligibility result
- HISTORICAL FALSE may be conclusive as a candidate decision only after the provenance-bound gates pass
- TRUE_CANDIDATE / UNKNOWN and HYBRID UNKNOWN remain ineligible
- `site_truth_decision_allowed=False`
- `site_promotion_allowed=False`
- `production_readiness_allowed=False`
- `production_registration_allowed=False`
- `runtime_registration_allowed=False`
- STEP114 does not itself bind the candidate decision to the canonical parcel/PNU
- STEP114 does not authorize SITE mutation, production registration, runtime registration, public API exposure, or Rule Engine promotion

## 2. Historical safety / real condition locks

PHASE 8 remains terminally reconciled at the current evidence boundary.
Public API historical exposure remains NOT AUTHORIZED.
Historical data remains excluded from the spatial runtime condition channel.
Only exact valid typed trusted historical handoff authorization is accepted at the production orchestrator boundary.

### 도시지역편입해제구역

- resolution family: `HISTORICAL_SITE_EVENT`
- standard code: None / UNVERIFIED / DO NOT GUESS
- unresolved real-condition evidence remains fail-closed
- production/runtime registration remains BLOCKED unless later admission contracts explicitly authorize it

### 개발밀도관리구역 / UQQ700

- resolution family: `HYBRID_SPATIAL_NOTICE`
- current legal-source resolution remains UNKNOWN
- negative evidence / legal absence inference disabled
- SITE TRUE/FALSE promotion remains blocked without the required verified evidence
- production/runtime registration remains blocked
- minimum gate remains official designation identity + current validity + SITE spatial inclusion verification

Legal-source investigation numbering (`S206`…`S216`/future S217) is separate from architecture STEP numbering and must not be conflated.

## 3. Architecture state / current gap

Architecture Baseline remains v1.2.

Current architecture has two important, separately safe paths:

1. Existing historical production-consumption path through typed trusted handoff, builder/service/orchestrator and Rule Engine integration.
2. New provenance-bound profile/resolver chain through STEP114.

The new chain intentionally stops at STEP114. The missing architecture boundary is not another independent SITE truth path. The next design target is a single fail-closed SITE applicability/admission boundary that reconciles:

```text
STEP114 verified candidate
+
canonical SITE identity / PNU
+
parcel applicability evidence
↓
SITE-decision / applicability admission boundary
↓
existing production consumption architecture
```

Key requirements for the next boundary:
- bind a candidate decision to the current canonical SITE/PNU before SITE truth promotion
- reject cross-parcel or unbound evidence
- preserve UNKNOWN when parcel applicability is not verified
- avoid creating a second parallel SITE truth/production path
- preserve existing public API historical injection boundary
- do not treat profile metadata, resolver result, or eligibility alone as SITE truth

The exact next STEP number, file name, function/class name, and signature are NOT assigned until the next READ-ONLY design audit confirms the existing implementation seams.

## 4. Repository cleanup checkpoint

Cleanup branch:
`cleanup/repository-organization-20260916`

Cleanup started from exact STEP114 checkpoint:
`ad06db07cf22138e5324eb263ae666814520eb53`

Locally validated cleanup batches:

### Batch 1 — PASS
Deleted obsolete root probes:
- `hello.py`
- `api_test.py`

### Batch 2 — PASS
Deleted obsolete Building HUB manual probes:
- `main.py`
- `building_api_test.py`
- `building_api_parse.py`

API error contract and `SITE_ANALYSIS_API_V1` final contract regressions both returned `all_pass: True` locally.

### Batch 3 — PASS
Deleted obsolete manual regulation-data print probe:
- `regulations/test_regulation_data.py`

Kept intentionally:
- `land_api_test.py` — current land converter/API diagnostic value remains
- `regulations/residential_zones.py` — legacy/static candidate, but dependency/retirement not proven sufficiently for deletion
- `law_data/*` investigation/provenance families — not ordinary disposable tests

Repository-organization conclusion:
- do not perform large mechanical moves of `law_data/*` or `site_data/*` merely for cosmetic structure
- many current module paths and executable regression commands depend on their package locations
- numeric investigation, historical notice probes, and UQQ700 source forensics preserve legal/provenance reproducibility and must not be bulk-deleted
- future moves require exact dependency/import/path audit and separate approval

## 5. Documentation state

`PROJECT_STATUS.md` is synchronized through STEP114 and cleanup Batch 1–3 by this update.

`PROJECT_ARCHITECTURE.md` remains Architecture Baseline v1.2 and is a long-term design document. Its core layer model and fail-closed principles remain valid. Its `CURRENT ARCHITECTURE CHECKPOINT` section is older than the STEP114 implementation state and should be reconciled only through a separately approved architecture-document update after the current READ-ONLY architecture review identifies the exact changes required.

## 6. Git / local rules

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

## 7. Standard development process

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
→ STEP closure
→ next READ-ONLY audit
```

Stop on pull conflict/refusal. Do not use stash/restore/reset/checkout/clean as a workaround for the protected file.

## 8. Next action

READ-ONLY architecture reconciliation audit:

1. inspect STEP114 output contract and direct dependencies
2. inspect canonical SITE/PNU identity and spatial applicability boundaries
3. inspect existing historical production handoff / builder / service / orchestrator consumption seams
4. determine the minimum fail-closed contract that binds STEP114 candidate eligibility to the current parcel
5. prove the design does not create a second SITE truth path
6. only after the audit, propose the exact next STEP and exact write scope for explicit approval

No SITE mutation, production/runtime registration, public API exposure, Rule Engine promotion, or architecture-document behavior change is authorized by this status update.

## 9. Handoff policy

In a new chat, reconstruct the actual branch HEAD and current files from GitHub READ-ONLY first. GitHub current code/HEAD overrides stale summaries or documents.

Preserve:
- repository / local root
- cleanup branch and preserved checkpoint branch
- Architecture Baseline
- STEP114 terminal validation
- protected local output modification
- fail-closed safety invariants
- unresolved SITE/PNU applicability gap
- explicit Git write approval rule
