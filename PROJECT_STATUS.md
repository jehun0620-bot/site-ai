# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-09-17
기준 branch: `cleanup/repository-organization-20260916`
기준 behavioral PASS HEAD: `b9d204cc6c6d128a46ed33ee38071a3c4f545065`
보존 checkpoint branch: `checkpoint/c12-fastapi-20260821`
보존 STEP114 HEAD: `ad06db07cf22138e5324eb263ae666814520eb53`
Architecture Baseline: v1.2

## 1. 현재 단계

STEP114 이후 historical SITE applicability/production/promotion, district-unit common production lane, parcel-register identity, parcel-only production, public ordinary/mountain HTTP E2E, address-based verified parcel identity, 그리고 verified address → existing parcel-analysis internal wiring까지 구현·사용자 로컬 검증했다.

STEP114 이후 기능 경계에는 새 architecture STEP 번호를 부여하지 않는다.

핵심 최신 user-local PASS:
- `HISTORICAL_SITE_EVENT_SITE_TRUTH_PROMOTION_RULE_INPUT_BRIDGE_CONTRACT_PASS`
- `HISTORICAL_SITE_TRUTH_PROMOTION_END_TO_END_REGRESSION_PASS`
- `SITE_ANALYSIS_ORCHESTRATOR_PROMOTION_RULE_INPUT_WIRING_CONTRACT_PASS`
- `HISTORICAL_RULE_ENGINE_VERIFIED_ENVELOPE_HANDOFF_PASS`
- `HISTORICAL_PRODUCTION_VERIFIED_ENVELOPE_EXPOSURE_PASS`
- `PARCEL_REGISTER_IDENTITY_PNU_CONTRACT_PASS`
- `PARCEL_ONLY_SITE_ORCHESTRATOR_CONTRACT_PASS`
- `SITE_IDENTITY_CROSS_PNU_FALLBACK_GUARD_CONTRACT_PASS`
- `PARCEL_ONLY_LAND_ENRICHMENT_CONTRACT_PASS`
- `PUBLIC_API_PARCEL_REGISTER_IDENTITY_CONTRACT_PASS`
- `PARCEL_ONLY_ADDRESS_ENRICHMENT_CONTRACT_PASS`
- `DISTRICT_UNIT_PLAN_SITE_TRUTH_PROMOTION_END_TO_END_REGRESSION_PASS`
- `ADDRESS_PARCEL_IDENTITY_RESOLVER_CONTRACT_PASS`
- `ADDRESS_SITE_ANALYSIS_ORCHESTRATOR_WIRING_CONTRACT_PASS`

### Address → existing full analysis E2E

Behavioral PASS HEAD `b9d204cc6c6d128a46ed33ee38071a3c4f545065` validates the internal address-analysis wiring. `analyze_site_by_address()` accepts an address, requires a VERIFIED address parcel identity, then forwards only canonical parcel components into the existing `analyze_site_by_parcel()` pipeline. No second analysis path or Rule Engine was created.

User-local real-data E2E confirmed:

```text
서울특별시 강남구 개포동 12번지
→ verified PNU 1168010300100120000
→ plat_gb_cd=0
→ existing parcel analysis
→ site_id 11680-10300-0012-0000
→ zone 제3종일반주거지역
→ building_count 34
→ identity_status COMPLETE
```

```text
서울특별시 동작구 동작동 산 29-3
→ verified PNU 1159010600200290003
→ plat_gb_cd=1
→ existing parcel analysis
→ parcel-only Building HUB 0 path
→ site_id 11590-10600-0029-0003
→ zone 자연녹지지역
→ building_count 0
→ identity_status COMPLETE
```

This establishes real-data ordinary + mountain address-to-full-analysis internal E2E. Public HTTP address exposure is not yet implemented/validated.

### Address parcel identity validation

Validated identity boundary remains:

```text
USER PARCEL ADDRESS
→ safe parcel-address normalization
→ VWorld parcel address search
→ exact address.parcel match
→ address-search item.id PNU
→ item coordinate
→ live LP_PA_CBND_BUBUN polygon query
→ polygon PNU
→ address PNU == polygon PNU
→ PNU component decomposition
→ create_pnu() exact regeneration
→ VERIFIED canonical parcel identity
```

Fail-closed behavior remains mandatory for empty search, no exact parcel match, address/polygon PNU mismatch, multiple distinct verified PNUs, invalid PNU, missing key, or unresolved parcel polygon.

### Parcel register identity / parcel-only production

Code-system mapping remains explicit:

```text
Public API / Building HUB plat_gb_cd=0 (ordinary) → PNU land-register digit 1
Public API / Building HUB plat_gb_cd=1 (mountain) → PNU land-register digit 2
```

Building HUB status `00` with zero items can produce a parcel-only Site from canonical parcel identity. Same-PNU VWorld Land Characteristics may enrich land category, zoning, official land area, and parcel address. Cross-PNU persisted identity fallback remains blocked.

Previously user-local validated public parcel-component HTTP E2E:
- ordinary `11680/10300/0/0012/0000` → PNU `1168010300100120000`, Building HUB 34 items, official land area `121040.4 square_meter`, identity COMPLETE
- mountain `11590/10600/1/0029/0003` → PNU `1159010600200290003`, parcel-only enrichment, official land area `16704.0 square_meter`, identity COMPLETE

## 2. Current safety boundary

```text
address search result ≠ canonical parcel truth
user parcel selection ≠ canonical parcel truth
verified address identity → existing parcel pipeline only
resolver result ≠ parcel applicability
SITE-decision eligibility ≠ SITE truth
SITE applicability admission ≠ production/runtime registration authority
promotion authorization ≠ second SITE truth store
verified envelope ≠ new Rule Engine
```

No identity/address/zone/coordinate/geometry/evidence may be reused across a different PNU. Address-derived identity must be rebound to live same-PNU parcel geometry before VERIFIED status.

Historical production remains PNU-bound and fail-closed. Public historical input remains unauthorized. UQQ700 remains UNKNOWN/BLOCKED.

## 3. Production reconciliation

Historical and district-unit family-specific verification paths converge only at the common verified SITE registry / existing Rule Engine lane. Simultaneous historical + district-unit production input remains fail-closed because no cross-family merge policy is authorized.

Address input is not a new production lane. It is an identity front door that converges into the existing parcel analysis function.

## 4. Documentation / product design

Architecture Baseline remains v1.2.

- `PROJECT_ARCHITECTURE.md`: validated architecture/invariants
- `PROJECT_STATUS.md`: current implementation and behavioral validation checkpoint
- `PROJECT_PRODUCT_UX.md`: product-facing ideas and UX backlog

Candidate-list + map-assisted parcel selection remains future product UX. User selection will still require backend PNU/geometry verification.

## 5. Repository / local rules

Repository: `jehun0620-bot/site-ai`
Current branch: `cleanup/repository-organization-20260916`
Preserved checkpoint: `checkpoint/c12-fastapi-20260821`
Local root: `D:\site-ai`

Never modify/commit `.env`, `law_data/output/*`, or unrelated files without explicit approved scope. Never use broad staging commands.

Protected local-only modified file:
`law_data/output/urban_area_conversion_history_final_resolution.json`

Expected state:
```text
 M law_data/output/urban_area_conversion_history_final_resolution.json
```

Never modify, restore, checkout, reset, delete, stage, commit, or clean this protected file. User-local execution PASS remains final behavioral validation.

## 6. Standard development process

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

## 7. Next action

Current READ-ONLY public HTTP audit confirms `api_app.py` is a thin FastAPI layer whose existing `/v1/site-analysis` route calls `analyze_site_by_parcel()` directly.

Next minimal public boundary should add an address request model and an address route that calls the already validated `analyze_site_by_address()` function. It must not duplicate address resolution or parcel analysis logic in the HTTP layer.

Target flow:

```text
POST address request
→ thin FastAPI validation
→ analyze_site_by_address()
→ VERIFIED address identity
→ existing analyze_site_by_parcel()
→ existing analysis response
```

Public historical inputs remain excluded. Candidate-list/map UX remains separate and should not be mixed into this first address-analysis HTTP endpoint.

## 8. Handoff policy

In a new chat, reconstruct actual branch HEAD and current files from GitHub READ-ONLY first. Current GitHub code plus user-local execution results override stale summaries/documents.
