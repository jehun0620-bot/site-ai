# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-09-17
기준 branch: `cleanup/repository-organization-20260916`
기준 behavioral PASS HEAD: `644420035690d8e3281fad4c564789d01d6469b0`
보존 checkpoint branch: `checkpoint/c12-fastapi-20260821`
보존 STEP114 HEAD: `ad06db07cf22138e5324eb263ae666814520eb53`
Architecture Baseline: v1.2

## 1. 현재 단계

STEP114 이후 historical/district-unit production, parcel identity/parcel-only production, verified address identity, public exact-address analysis, 그리고 address parcel candidate discovery까지 구현·사용자 로컬 검증했다. STEP114 이후 기능 경계에는 새 architecture STEP 번호를 부여하지 않는다.

최신 관련 PASS:
- `ADDRESS_PARCEL_IDENTITY_RESOLVER_CONTRACT_PASS`
- `ADDRESS_SITE_ANALYSIS_ORCHESTRATOR_WIRING_CONTRACT_PASS`
- `PUBLIC_API_ADDRESS_SITE_ANALYSIS_CONTRACT_PASS`
- `ADDRESS_PARCEL_CANDIDATE_SEARCH_CONTRACT_PASS`

### Public exact-address HTTP — VALIDATED

Code HEAD `f54cd84b6c91cd2f8c0e47612223133daac97a4d`에서 `/v1/site-analysis/address` contract 및 실제 HTTP ordinary/mountain E2E가 user-local PASS했다.

```text
address HTTP
→ analyze_site_by_address()
→ VERIFIED canonical parcel identity
→ existing analyze_site_by_parcel()
→ SITE_ANALYSIS_API_V1 / READY
```

Ordinary: `서울특별시 강남구 개포동 12번지` → PNU `1168010300100120000`, identity COMPLETE, building_count 34.
Mountain: `서울특별시 동작구 동작동 산 29-3` → PNU `1159010600200290003`, identity COMPLETE, parcel-only building_count 0.

### Address parcel candidate discovery — VALIDATED

Behavioral PASS HEAD `644420035690d8e3281fad4c564789d01d6469b0`.

`site_data/address_parcel_candidate_search.py` is a discovery-only boundary. It returns sanitized VWorld parcel candidates and does not mark them VERIFIED or start SITE analysis.

User-local contract PASS:
`ADDRESS_PARCEL_CANDIDATE_SEARCH_CONTRACT_PASS`

User-local real VWorld query:
`서울특별시 강남구 개포동 12`
returned ten usable parcel candidates including:

```text
개포동 12    → candidate PNU 1168010300100120000 → 대청아파트302동
개포동 12-1  → candidate PNU 1168010300100120001
개포동 12-10 → candidate PNU 1168010300100120010
개포동 12-2  → candidate PNU 1168010300100120002 → 개포자이
개포동 12-4  → candidate PNU 1168010300100120004 → 석탑프라자
```

Each usable candidate supplied `candidate_pnu`, `parcel_address`, `x`, `y`, `crs=EPSG:4326`; road address/building name were preserved when provider supplied them.

This proves the product candidate-list foundation with real data. It does NOT prove candidate PNU as canonical truth.

## 2. Safety boundary

```text
address search result ≠ canonical parcel truth
candidate PNU ≠ canonical parcel truth
candidate coordinate ≠ parcel inclusion proof
user candidate selection ≠ canonical parcel truth
VERIFIED identity only → existing analysis pipeline
```

Candidate selection must later be rebound to live same-PNU parcel geometry before analysis admission. No identity/address/zone/coordinate/geometry/evidence may be reused across a different PNU.

Historical production remains PNU-bound/fail-closed. Public historical input remains unauthorized. UQQ700 remains UNKNOWN/BLOCKED.

## 3. Product-facing position

Candidate discovery backend is now real-data validated, but it is not yet exposed through public HTTP.

Current candidate payload foundation:
- `candidate_pnu`
- `parcel_address`
- `road_address`
- `building_name`
- `x`
- `y`
- `crs`

The next boundary is a thin public candidate-search endpoint that delegates to `search_address_parcel_candidates()` and returns discovery metadata only.

## 4. Repository / local rules

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

## 5. Standard process

```text
READ-ONLY audit
→ exact WRITE scope
→ implementation
→ focused contract
→ GitHub save
→ user-local validation
→ next READ-ONLY audit
```

## 6. Next action

Public candidate search should remain a thin discovery endpoint:

```text
HTTP candidate query
→ api_app validation
→ search_address_parcel_candidates()
→ sanitized candidate dictionaries
→ NO VERIFIED status
→ NO SITE/regulation analysis
```

After public candidate HTTP validation, design candidate selection → backend same-PNU polygon re-verification as a separate boundary.
