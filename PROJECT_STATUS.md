# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-09-17
기준 branch: `cleanup/repository-organization-20260916`
기준 behavioral PASS HEAD: `07b1c8c28871a6d07ffc94df112178baa7beb361`
보존 checkpoint branch: `checkpoint/c12-fastapi-20260821`
보존 STEP114 HEAD: `ad06db07cf22138e5324eb263ae666814520eb53`
Architecture Baseline: v1.2

## 1. 현재 단계

STEP114 이후 historical/district-unit production, parcel identity/parcel-only production, verified address identity, public exact-address analysis, candidate discovery/public HTTP, selected-candidate same-PNU polygon verification, 그리고 selected-candidate → existing analysis wiring/full live E2E까지 사용자 로컬 검증했다. STEP114 이후 기능 경계에는 새 architecture STEP 번호를 부여하지 않는다.

최신 관련 PASS:
- `ADDRESS_PARCEL_IDENTITY_RESOLVER_CONTRACT_PASS`
- `ADDRESS_SITE_ANALYSIS_ORCHESTRATOR_WIRING_CONTRACT_PASS`
- `PUBLIC_API_ADDRESS_SITE_ANALYSIS_CONTRACT_PASS`
- `ADDRESS_PARCEL_CANDIDATE_SEARCH_CONTRACT_PASS`
- `PUBLIC_API_ADDRESS_PARCEL_CANDIDATE_SEARCH_CONTRACT_PASS`
- `SELECTED_PARCEL_CANDIDATE_VERIFIER_CONTRACT_PASS`
- `SELECTED_PARCEL_CANDIDATE_SITE_ANALYSIS_WIRING_CONTRACT_PASS`

## 2. Candidate discovery/public HTTP — VALIDATED

`POST /v1/parcel-candidates/address` actual user-local HTTP PASS. `서울특별시 강남구 개포동 12`, size 10 → `PARCEL_CANDIDATE_SEARCH_V1`, READY, count 10.

Candidate discovery remains non-authoritative:

```text
candidate PNU ≠ canonical parcel truth
candidate point ≠ parcel inclusion proof
user selection ≠ canonical parcel truth
```

## 3. Selected candidate same-PNU verification — VALIDATED

Actual live candidate:
- `개포동 12-2 / 개포자이`
- candidate_pnu `1168010300100120002`
- x `127.07662495509604`
- y `37.49629354642009`

Live `LP_PA_CBND_BUBUN` polygon re-query found the same PNU, and `parcel_identity_from_pnu` regeneration produced VERIFIED / `SELECTED_PARCEL_CANDIDATE_VERIFIED`.

Verified identity: sigungu `11680`, bjdong `10300`, plat_gb `0`, bun `0012`, ji `0002`, CRS EPSG:4326.

## 4. Selected candidate → existing full analysis — VALIDATED

Behavioral PASS HEAD `07b1c8c28871a6d07ffc94df112178baa7beb361`.

Focused contract:
`SELECTED_PARCEL_CANDIDATE_SITE_ANALYSIS_WIRING_CONTRACT_PASS`

Actual user-local live E2E:

```text
selected candidate
→ live same-PNU polygon verification
→ VERIFIED canonical components
→ existing analyze_site_by_parcel()
→ Building HUB + land/site analysis
→ SITE_ANALYSIS_API_V1 / READY
```

Observed result:
- site_id `11680-10300-0012-0002`
- pnu `1168010300100120002`
- address `서울특별시 강남구 개포동 12-2번지`
- road_address `서울특별시 강남구 개포로109길 69 (개포동)`
- identity_status `COMPLETE`
- zone `제3종일반주거지역`
- building_count `9`
- Building HUB status `00`

No second SITE analysis lane was created.

## 5. Public selected-candidate HTTP — IMPLEMENTED, LOCAL VALIDATION PENDING

Current GitHub implementation exposes:

```text
POST /v1/site-analysis/selected-candidate
```

Request boundary:
- candidate_pnu: exactly 19 digits
- x: -180..180
- y: -90..90
- project_profile
- procedure_profile
- include_debug

The HTTP layer does not parse PNU or create VERIFIED state. It delegates to `analyze_site_by_selected_candidate()`, which performs the existing live polygon re-verification before parcel analysis.

Focused contract:
`site_data/public_api_selected_parcel_candidate_site_analysis_contract_test.py`

Required next validation:
`PUBLIC_API_SELECTED_PARCEL_CANDIDATE_SITE_ANALYSIS_CONTRACT_PASS`

After contract PASS, run actual local HTTP E2E for `개포동 12-2`.

## 6. Safety boundary

No identity/address/zone/coordinate/geometry/evidence may be reused across a different PNU. Historical production remains PNU-bound/fail-closed. Public historical input remains unauthorized. UQQ700 remains UNKNOWN/BLOCKED.

## 7. Repository / local rules

Repository: `jehun0620-bot/site-ai`
Branch: `cleanup/repository-organization-20260916`
Local root: `D:\site-ai`

Protected local-only modified file:
`law_data/output/urban_area_conversion_history_final_resolution.json`

Expected:
```text
 M law_data/output/urban_area_conversion_history_final_resolution.json
```

Never modify, restore, checkout, reset, delete, stage, commit, or clean this file. Never modify/commit `.env` or `law_data/output/*` without explicit scope. Never use broad staging. User-local execution PASS is final behavioral validation.
