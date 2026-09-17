# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-09-17
기준 branch: `cleanup/repository-organization-20260916`
기준 behavioral PASS HEAD: `164c669089b67272bb6cf01abbdf7a67593e5b43`
보존 checkpoint branch: `checkpoint/c12-fastapi-20260821`
보존 STEP114 HEAD: `ad06db07cf22138e5324eb263ae666814520eb53`
Architecture Baseline: v1.2

## 1. 현재 단계

STEP114 이후 historical/district-unit production, parcel identity/parcel-only production, verified address identity, public exact-address analysis, candidate discovery/public HTTP, selected-candidate same-PNU polygon re-verification까지 사용자 로컬 검증했다. STEP114 이후 기능 경계에는 새 architecture STEP 번호를 부여하지 않는다.

최신 관련 PASS:
- `ADDRESS_PARCEL_IDENTITY_RESOLVER_CONTRACT_PASS`
- `ADDRESS_SITE_ANALYSIS_ORCHESTRATOR_WIRING_CONTRACT_PASS`
- `PUBLIC_API_ADDRESS_SITE_ANALYSIS_CONTRACT_PASS`
- `ADDRESS_PARCEL_CANDIDATE_SEARCH_CONTRACT_PASS`
- `PUBLIC_API_ADDRESS_PARCEL_CANDIDATE_SEARCH_CONTRACT_PASS`
- `SELECTED_PARCEL_CANDIDATE_VERIFIER_CONTRACT_PASS`

## 2. Candidate discovery/public HTTP — VALIDATED

`POST /v1/parcel-candidates/address` actual user-local HTTP PASS at code lineage through `1f21cd0c8837fbae31e81b757482a311d9d7b6e5`.

`서울특별시 강남구 개포동 12`, size 10 → `PARCEL_CANDIDATE_SEARCH_V1`, READY, count 10. Returned real candidate PNU/address/point metadata.

Candidate discovery remains non-authoritative:

```text
candidate PNU ≠ canonical parcel truth
candidate point ≠ parcel inclusion proof
user selection ≠ canonical parcel truth
```

## 3. Selected candidate same-PNU verification — VALIDATED

Behavioral PASS HEAD `164c669089b67272bb6cf01abbdf7a67593e5b43`.

Focused contract:
`SELECTED_PARCEL_CANDIDATE_VERIFIER_CONTRACT_PASS`

Actual VWorld live verification:

```text
candidate: 개포동 12-2 / 개포자이
candidate_pnu: 1168010300100120002
x: 127.07662495509604
y: 37.49629354642009
→ live LP_PA_CBND_BUBUN query
→ selected PNU found in polygon feature PNUs
→ parcel_identity_from_pnu regeneration
→ VERIFIED / SELECTED_PARCEL_CANDIDATE_VERIFIED
```

Verified identity:
- sigungu_cd `11680`
- bjdong_cd `10300`
- plat_gb_cd `0`
- bun `0012`
- ji `0002`
- CRS `EPSG:4326`

This is canonical parcel identity verification only. It is not SITE truth or regulation applicability.

## 4. Selected candidate → existing analysis wiring — IMPLEMENTED, LOCAL VALIDATION PENDING

Current GitHub implementation adds `analyze_site_by_selected_candidate()` to the existing Orchestrator. It:

```text
candidate_pnu + x + y
→ verify_selected_parcel_candidate()
→ require VERIFIED
→ use only verified sigungu/bjdong/plat_gb/bun/ji
→ existing analyze_site_by_parcel()
```

Rejected verification raises `SiteBuildError` before parcel analysis. No second analysis lane is created.

Focused contract file:
`site_data/selected_parcel_candidate_site_analysis_wiring_contract_test.py`

Required next validation:
`SELECTED_PARCEL_CANDIDATE_SITE_ANALYSIS_WIRING_CONTRACT_PASS`

After that, run real selected-candidate → full existing analysis E2E. Public selected-candidate HTTP endpoint remains a later separate boundary.

## 5. Safety boundary

No identity/address/zone/coordinate/geometry/evidence may be reused across a different PNU. Historical production remains PNU-bound/fail-closed. Public historical input remains unauthorized. UQQ700 remains UNKNOWN/BLOCKED.

## 6. Repository / local rules

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
