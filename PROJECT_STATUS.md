# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-09-21
기준 branch: `cleanup/repository-organization-20260916`
기준 behavioral PASS HEAD: `3f9ab844250dad962c4b9129d2f6a696f09811ad`
보존 checkpoint branch: `checkpoint/c12-fastapi-20260821`
보존 STEP114 HEAD: `ad06db07cf22138e5324eb263ae666814520eb53`
Architecture Baseline: v1.2

## 1. 현재 단계

STEP114 이후 historical/district-unit production, parcel identity/parcel-only production, verified address identity, public exact-address analysis, candidate discovery/public HTTP, selected-candidate same-PNU polygon verification, selected-candidate full analysis, public selected-candidate HTTP까지 사용자 로컬 검증했다. STEP114 이후 기능 경계에는 새 architecture STEP 번호를 부여하지 않는다.

최신 관련 PASS:
- `ADDRESS_PARCEL_IDENTITY_RESOLVER_CONTRACT_PASS`
- `ADDRESS_SITE_ANALYSIS_ORCHESTRATOR_WIRING_CONTRACT_PASS`
- `PUBLIC_API_ADDRESS_SITE_ANALYSIS_CONTRACT_PASS`
- `ADDRESS_PARCEL_CANDIDATE_SEARCH_CONTRACT_PASS`
- `PUBLIC_API_ADDRESS_PARCEL_CANDIDATE_SEARCH_CONTRACT_PASS`
- `SELECTED_PARCEL_CANDIDATE_VERIFIER_CONTRACT_PASS`
- `SELECTED_PARCEL_CANDIDATE_SITE_ANALYSIS_WIRING_CONTRACT_PASS`
- `PUBLIC_API_SELECTED_PARCEL_CANDIDATE_SITE_ANALYSIS_CONTRACT_PASS`

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

## 5. Public selected-candidate HTTP — VALIDATED

Behavioral PASS HEAD `5538b95ab74eb674883420ea9267fd1d38ebf2ec`.

Endpoint:

```text
POST /v1/site-analysis/selected-candidate
```

Focused contract:
`PUBLIC_API_SELECTED_PARCEL_CANDIDATE_SITE_ANALYSIS_CONTRACT_PASS`

Actual user-local HTTP E2E for `개포동 12-2 / 개포자이` returned:
- schema_version `SITE_ANALYSIS_API_V1`
- status `READY`
- site_id `11680-10300-0012-0002`
- pnu `1168010300100120002`
- identity_status `COMPLETE`
- official land area `15487.3 square_meter`
- building_count `9`
- Building HUB status `00`
- building coverage ratio `50.0%`
- floor area ratio `250.0%`

The spatial response proves the safety boundary remained active:

```text
requested_pnu  = 1168010300100120002
snapshot_pnu   = 1168010300100120000
snapshot match = false
live feature_pnu = 1168010300100120002
live resolution  = PNU_POLYGON_VERIFIED
verified          = true
```

The stale different-PNU snapshot was not treated as parcel truth; live same-PNU geometry was re-queried and verified before analysis.

Public backend flow is now validated end-to-end:

```text
address search
→ candidate list HTTP
→ user candidate selection
→ live same-PNU polygon re-verification
→ VERIFIED canonical parcel identity
→ existing full analysis
→ public HTTP READY
```

## 6. Current product boundary — Single Parcel v1 closure

Candidate list/map, lightweight parcel confirmation, VERIFIED polygon display, selected-candidate full analysis, additional-input/reanalysis UX, PC result presentation, and actual Backend-connected Playwright regression have progressed beyond the 2026-09-17 candidate-UI boundary. Frontend implementation/validation details are tracked in `PROJECT_FRONTEND_STATUS.md`.

The current product strategy is to finish **Single Parcel v1** at a deliberate boundary before starting Integrated Development.

Single Parcel v1 closure priorities:

```text
1. Public Rule Presentation Model
2. PC rule-detail UX consuming only the public product contract
3. Machine-readable Product Error Model + PC error mapping
4. Final Single Parcel regression baseline
```

Road-name-address input support and broader provider retry/cache/rate-limit/observability hardening are not currently required to block the Single Parcel v1 closure; they remain follow-up scope unless later evidence changes that decision. Mobile-specific refinement remains paused until a mobile test environment is available.

Backend Public Rule Presentation Model is now IMPLEMENTED and user-local validated.

Validation:

```text
SITE_ANALYSIS_RULE_DETAILS_CONTRACT_PASS
SITE_ANALYSIS_RULE_DETAILS_REAL_DATA_REGRESSION_PASS
rule_details.count: 314
APPLICABLE: 62
NOT_APPLICABLE: 214
CONDITIONAL: 36
UNKNOWN: 2
```

The two real UNKNOWN rules were preserved as public product details with law name, rule title, Backend applicability reason, and unresolved condition `도시지역편입해제구역`. The public response keeps `debug.rule_engine` separate, and no second Rule Engine path was created.

The PC Frontend consuming this public contract is also user-local behavioral/build/E2E validated.

The **Machine-readable Product Error Model** is now implemented and user-local contract validated. Public FastAPI failures use the product-safe `SITE_API_ERROR_V1` detail envelope with stable `code`, `category`, `message`, and `retryable` fields while preserving HTTP status. Focused and existing selected-candidate public API contracts passed locally:

```text
PUBLIC_API_PRODUCT_ERROR_CONTRACT_PASS
PUBLIC_API_SELECTED_PARCEL_CANDIDATE_SITE_ANALYSIS_CONTRACT_PASS
PUBLIC_API_SELECTED_PARCEL_CANDIDATE_CONFIRMATION_CONTRACT_PASS
```

The PC Frontend now parses that structured error contract across candidate search, parcel confirmation, and SITE analysis while retaining legacy string-detail fallback. User-local production build passed and the existing actual Backend-connected Playwright regression passed at HEAD `3f9ab844250dad962c4b9129d2f6a696f09811ad` with `1 passed (15.0s)`.

During that regression a searched candidate was legitimately rejected by live same-PNU verification with `SELECTED_PNU_POLYGON_MISMATCH`. The E2E was corrected so discovery candidates are not assumed to be VERIFIED; rejected discovery candidates are allowed and the test still requires at least one VERIFIED candidate per default address before exercising analysis/reanalysis.

Remaining Single Parcel v1 closure work:

```text
1. Focused deterministic Frontend validation of SITE_API_ERROR_V1 product-error UX
2. Final Single Parcel regression baseline
3. Single Parcel v1 baseline freeze / handoff
```

Frontend structured-error parsing dedicated deterministic error-path validation is now user-local PASS.

Single Parcel v1 final baseline at code HEAD `8d44834e98b4035b1da44fc8994ce1b9e1db17a2`:

```text
Production build: PASS (Vite 8.3.0, 21 modules, 95ms)
Focused SITE_API_ERROR_V1 Frontend E2E: PASS (3 passed, 2.4s)
Actual Backend-connected reanalysis E2E: PASS (1 passed, 18.9s)
```

Therefore Single Parcel v1 is baseline-frozen with user-local final regression PASS.

## 7. Safety boundary

No identity/address/zone/coordinate/geometry/evidence may be reused across a different PNU. Historical production remains PNU-bound/fail-closed. Public historical input remains unauthorized. UQQ700 remains UNKNOWN/BLOCKED.

## 8. Repository / local rules

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


## 9. Architecture / code-quality checkpoint — 2026-09-21

SITE FACT land provenance is user-local behavioral PASS through the actual Backend-connected Playwright regression. The subsequent VWorld land-hydration deduplication is also user-local behavioral PASS at code HEAD `b12443228c4dee823e594eb8d6039c6110cc5d88`:

```text
PARCEL_ONLY_LAND_ENRICHMENT_CONTRACT_PASS
VWORLD_LATEST_LAND_YEAR_SELECTION: all_pass True
SITE FACT real-data regression: all_pass True
SITE analysis public response: all_pass True
actual Backend SITE-facts E2E: 1 passed
```

That refactor centralized latest-record conversion + land provenance preservation in `hydrate_land_from_records()` while preserving the existing VWorld latest-year policy and public behavior.

The Building HUB provider extraction is now **USER-LOCAL BEHAVIORAL PASS** at HEAD `d46a3afbbead00341fa2a8f2a7581cbf26760009`. Validation passed for the focused provider contract, parcel-only land regression, real-data SITE FACT regression, public response regression, and actual Backend-connected SITE-facts Playwright E2E.

No change is intended to public API schemas, canonical PNU semantics, Rule Engine, historical/district-unit admission, Frontend contracts, or the protected local output file.


### Verified SITE input admission refactor — 2026-09-21

The pre-refactor fail-closed safety contract was user-local PASS at `499fe03d58f322d9b0bc82c8caf36d703e795825`, together with the historical promotion end-to-end regression. The verified historical/district admission responsibility has now been extracted from `site_analysis_orchestrator.py` into `site_data/verified_site_input_admission.py` without changing the intended admission rules or error semantics. This extraction is **USER-LOCAL BEHAVIORAL PASS** at HEAD `6a55eab6eb51c8c1a76e4bb1d6d197fbc3c9caf6`: the focused admission contract, historical promotion end-to-end regression, real-data SITE FACT regression, and public response regression all passed.


### SITE facts response projection refactor — 2026-09-21

Public `site_facts` projection has been extracted from `site_analysis_response.py` into `site_data/site_facts_response.py`. A focused projection contract test was added. This extraction is **USER-LOCAL BEHAVIORAL PASS** at HEAD `ecc2cd1952855939f375131cdd774e6d0d9127b0`: focused SITE facts projection, existing public response regression, real-data SITE FACT regression, and actual Backend-connected SITE-facts E2E all passed with the existing `SITE_ANALYSIS_API_V1` shape and values preserved.
