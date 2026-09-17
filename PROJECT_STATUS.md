# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-09-17
기준 branch: `cleanup/repository-organization-20260916`
기준 behavioral PASS HEAD: `1f21cd0c8837fbae31e81b757482a311d9d7b6e5`
보존 checkpoint branch: `checkpoint/c12-fastapi-20260821`
보존 STEP114 HEAD: `ad06db07cf22138e5324eb263ae666814520eb53`
Architecture Baseline: v1.2

## 1. 현재 단계

STEP114 이후 historical/district-unit production, parcel identity/parcel-only production, verified address identity, public exact-address analysis, address parcel candidate discovery, 그리고 public candidate-search HTTP boundary까지 구현·사용자 로컬 검증했다. STEP114 이후 기능 경계에는 새 architecture STEP 번호를 부여하지 않는다.

최신 관련 PASS:
- `ADDRESS_PARCEL_IDENTITY_RESOLVER_CONTRACT_PASS`
- `ADDRESS_SITE_ANALYSIS_ORCHESTRATOR_WIRING_CONTRACT_PASS`
- `PUBLIC_API_ADDRESS_SITE_ANALYSIS_CONTRACT_PASS`
- `ADDRESS_PARCEL_CANDIDATE_SEARCH_CONTRACT_PASS`
- `PUBLIC_API_ADDRESS_PARCEL_CANDIDATE_SEARCH_CONTRACT_PASS`

## 2. Public exact-address analysis — VALIDATED

`POST /v1/site-analysis/address` actual HTTP ordinary/mountain E2E PASS.

```text
address
→ VERIFIED canonical parcel identity
→ existing analyze_site_by_parcel()
→ SITE_ANALYSIS_API_V1 / READY
```

Ordinary: `서울특별시 강남구 개포동 12번지` → PNU `1168010300100120000`, identity COMPLETE, building_count 34.
Mountain: `서울특별시 동작구 동작동 산 29-3` → PNU `1159010600200290003`, identity COMPLETE, parcel-only building_count 0.

## 3. Parcel candidate discovery + public HTTP — VALIDATED

Behavioral PASS HEAD `1f21cd0c8837fbae31e81b757482a311d9d7b6e5`.

Internal candidate search contract and real VWorld query passed. Public contract `PUBLIC_API_ADDRESS_PARCEL_CANDIDATE_SEARCH_CONTRACT_PASS` passed locally.

Actual user-local HTTP:

```text
POST /v1/parcel-candidates/address
query = 서울특별시 강남구 개포동 12
size = 10
→ schema_version PARCEL_CANDIDATE_SEARCH_V1
→ status READY
→ count 10
```

Returned real candidates included PNU/address/point metadata for `개포동 12`, `12-1`, `12-10`, etc. Candidate coordinates are EPSG:4326. Road address/building name are preserved when supplied by VWorld.

PowerShell Korean mojibake is a terminal display issue; structural fields, PNU, coordinates and counts were correct.

Candidate search is discovery only:

```text
candidate PNU ≠ canonical parcel truth
candidate point ≠ parcel inclusion proof
user selection ≠ canonical parcel truth
```

## 4. Next architecture boundary: selected candidate re-verification

READ-ONLY inspection confirms reusable primitives already exist in `law_data/parcel_geometry_provider.py` and `site_data/address_parcel_identity_resolver.py`:
- `query_dataset_by_point(api_key, PARCEL_DATASET, x, y)`
- polygon-only filtering
- `find_feature_pnu(feature)`
- `parcel_identity_from_pnu(pnu)` with create_pnu regeneration

Therefore selected-candidate verification should not duplicate VWorld transport or PNU parsing.

Preferred boundary:

```text
selected candidate_pnu + x + y
→ validate 19-digit PNU / EPSG:4326 point
→ live LP_PA_CBND_BUBUN query at selected point
→ polygon feature PNU extraction
→ require selected candidate_pnu in live polygon PNUs
→ parcel_identity_from_pnu(candidate_pnu)
→ VERIFIED selected parcel identity
```

This verifier should be a separate module from candidate discovery and exact-address resolver. It must not trust candidate address text, must not perform SITE/regulation analysis, and must fail closed on mismatch/query failure/invalid PNU.

After this verifier is behaviorally validated, a separate adapter can pass its verified canonical parcel components into existing `analyze_site_by_parcel()`.

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

## 7. Next action

Implement the selected-candidate same-PNU polygon verifier as an isolated boundary plus focused contract test. Do not modify candidate discovery, exact-address resolver, Orchestrator, Rule Engine, historical/district code, `.env`, or output files in that implementation.
