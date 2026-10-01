# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-09-29
기준 branch: `cleanup/repository-organization-20260916`
기준 behavioral PASS HEAD: `268a87a7bd64237a311da6ee0b4c059a8936f6f4`
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

Road-name-address candidate discovery is now implemented and user-local validated: candidate search tries parcel-address search first, falls back to road-address search only on a normal no-result, deduplicates provider rows by PNU, and preserves the existing live same-PNU polygon verification boundary before analysis. Provider transport/HTTP/provider-status failures are no longer collapsed into a normal no-result; they surface through the structured `SITE_API_ERROR_V1` product-error boundary. Broader provider retry/cache/rate-limit/observability hardening remains follow-up scope. Responsive CSS is implemented, while mobile-specific behavioral validation remains deferred.

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

### Current Single Parcel regression checkpoint — 2026-09-22

After the road-address discovery and candidate-provider error-semantics changes, the current Single Parcel baseline was revalidated from the user-local checkout at HEAD `268a87a7bd64237a311da6ee0b4c059a8936f6f4`.

```text
Backend SITE service: PASS
SITE facts response contract: PASS
Public rule-details contract: PASS
Rule-details real-data regression: PASS
Final SITE snapshot: PASS / READY / 314 = 62 / 214 / 36 / 2
Frontend production build: PASS (Vite 8.3.0, 28 modules)
Focused SITE_API_ERROR_V1 Frontend E2E: PASS (3 passed, 2.5s)
Actual Backend-connected reanalysis E2E: PASS (1 passed, 19.4s; test body 18.8s)
```

The Backend-connected regression covers the current parcel/road-address discovery path, candidate confirmation and VERIFIED parcel boundary, selected-candidate analysis/reanalysis, rule-detail presentation, state isolation across parcel changes, and the buildingless case. This checkpoint supersedes the older Single Parcel regression timing/module-count record above without changing the architecture or truth boundaries.

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


### Zone relevance classifier production boundary — 2026-09-21

용도지역 관련 production 판정이 더 이상 `law_special_rule_clause_split_test.py`의 테스트 구현을 import하지 않도록 `law_data/zone_relevance_classifier.py`로 분리했다. `rule_evaluation_pipeline.py`와 기존 clause-split regression은 동일 production classifier를 공유한다.

사용자 로컬 검증 결과:

```text
law_special_rule_clause_split_test: ALL PASS
rule_evaluation_pipeline_module_test: all_pass True
rule_evaluation_pipeline_stateless_test: all_pass True
SITE_ANALYSIS_CURRENT_BASELINE_PASS
SITE_ANALYSIS_RULE_DETAILS_CONTRACT_PASS
SITE_ANALYSIS_RULE_DETAILS_REAL_DATA_REGRESSION_PASS
final SITE rules: 314 = 62 / 214 / 36 / 2
public UNKNOWN: clause 47, 48 / 도시지역편입해제구역
site_analysis_final_snapshot_test: all_pass True
```

따라서 classifier production-boundary 정규화는 behavioral PASS다. 기존 `law_data/output/site_analysis_final_snapshot.json`은 현재 production 전체를 재직렬화할 때 이번 작업 범위를 넘어서는 누적 차이가 함께 발생하므로 이 refactor의 commit 대상에서 제외한다. snapshot baseline 전체 reconciliation은 별도 작업으로 분리한다. 보호 파일 `urban_area_conversion_history_final_resolution.json`은 계속 제외한다.


### Public API Product Error normalization — 2026-09-21

Public FastAPI error boundary를 재점검한 결과 `POST /v1/site-analysis/address`의 generic exception 한 경로만 기존 문자열 `detail`을 반환하고 있었다. 해당 경로를 기존 `SITE_API_ERROR_V1` product error envelope의 `UNEXPECTED_ERROR / INTERNAL`로 통일했고, 오래된 address contract assertion도 현재 공개 계약에 맞게 정렬했다.

사용자 로컬 검증 결과:

```text
PUBLIC_API_PRODUCT_ERROR_CONTRACT_PASS
PUBLIC_API_ADDRESS_SITE_ANALYSIS_CONTRACT_PASS
PUBLIC_API_SELECTED_PARCEL_CANDIDATE_SITE_ANALYSIS_CONTRACT_PASS
PUBLIC_API_SELECTED_PARCEL_CANDIDATE_CONFIRMATION_CONTRACT_PASS
```

따라서 현재 검증 대상 public SITE/candidate HTTP 오류 경로는 machine-readable product error 계약으로 정규화되었다. production 분석 로직, PNU/geometry truth, Rule Engine, Historical/District, SITE FACT, Frontend 계약은 변경하지 않았다.


## 10. Backend final refactoring / reconciliation checkpoint — 2026-09-22

Single Parcel v1 이후 전체 repository를 production dependency 기준으로 재점검했다. 파일 크기나 `*_test.py` 이름만으로 삭제하지 않고, definition → production import/caller → runtime entrypoint → contract/regression을 추적한 뒤 KEEP / REFACTOR / LEGACY 후보를 판단한다. 삭제 작업은 GitHub 저장만으로 완료 처리하지 않고 사용자 로컬 회귀 PASS까지 확인한다.

### Spatial provider boundary

VWorld spatial HTTP/credential/response-classification 책임을 `law_data/vworld_spatial_provider.py`로 분리하고, `spatial_condition_evaluator.py`는 parcel compatibility, geometry intersection, condition-specific TRUE/FALSE/UNKNOWN 의미론을 유지한다. 분리 과정에서 evaluator 소유 dataset registry 상수 4개가 누락된 회귀를 발견해 즉시 복구했고, 이후 focused provider contract, production adapter regression, runtime spatial generalization regression이 사용자 로컬 PASS했다.

### Safety contracts and legacy cleanup

현재 production 경계를 직접 잠그는 focused contract를 추가했다.

```text
ZONE_RELEVANCE_TRANSITION_CONTRACT_PASS
PARCEL_GEOMETRY_PROVIDER_CONTRACT_PASS
SITE_IDENTITY_RESOLVER_CONTRACT_PASS
```

계약 확인 후 실제 production 실행에 기여하지 않던 placeholder/obsolete probe만 제한적으로 제거했다. `live_parcel_geometry_provider_test.py`와 `site_analysis_identity_probe_test.py` 삭제 후 관련 production regressions가 사용자 로컬 PASS했다. 과거 `regulation_model.py` 삭제 시 실제 `site_data_model.py`의 direct import를 놓친 사례가 있었고 즉시 원복했다. 따라서 `regulation_model.py`는 현재 KEEP이며, historical/official-data forensic 파일은 이름만으로 일괄 삭제하지 않는다.

### Rule Evaluation Pipeline decision

`law_data/rule_evaluation_pipeline.py`는 크지만 현재 deterministic evaluation의 safety-critical ordering을 한 곳에서 조정한다. numeric guards, zone relevance transition, runtime/site registry overlay, verified upper-branch restoration 등의 결합을 재검토한 결과 현재는 **KEEP**으로 결정했다. 단순 LOC 감소를 위한 분리는 하지 않는다. Zone relevance transition은 별도 contract로 현재 의미론을 고정했다.

### Final snapshot reconciliation

`law_data/output/site_analysis_final_snapshot.json`을 현재 production 결과와 구조적으로 비교했다. 신규/확장된 `rule_details`, `land_area`, `site`, `rule_engine`이 대규모 diff의 원인이었고, `rule_details.count == 314`, 실제 items 314, 최종 분포 `62 / 214 / 36 / 2`, analysis READY를 확인했다. Snapshot test는 `site_input.land_area`를 주입하지 않으므로 해당 builder-level snapshot의 official land area가 `None`인 것도 현재 코드 의미론과 일치한다.

새 snapshot baseline은 commit `1eddb0c98db32d815829fdb242485c42cb42e7c8`로 저장되었고 snapshot 1개 파일만 포함됨을 확인했다. 보호 파일 `law_data/output/urban_area_conversion_history_final_resolution.json`은 계속 local unstaged 상태로 보존한다.

Backend 최종 통합 regression은 2026-09-22 사용자 로컬에서 **BEHAVIORAL PASS**했다. Provider/geometry/identity/zone-transition safety contracts, production/runtime spatial regressions, Building HUB numeric preservation, SITE service/public response, real API→SITE analysis, real-data SITE FACT, public product-error contract, multi-SITE state-leakage regression이 모두 PASS했다.

대표 확인값:
```text
BASE: 314 = 62 / 214 / 36 / 2
LIVE: 314 = 62 / 216 / 34 / 2
개포동 12: READY / official area 121040.4 / buildings 34 / BCR 50 / FAR 250
개포동 13: READY / verified different PNU / MultiPolygon / BCR 60 / FAR 150
```

다른 PNU에서 stale BASE snapshot geometry를 canonical truth로 재사용하지 않고 live same-PNU polygon을 재검증했으며, zone/numeric/rule state도 대상 SITE에 맞게 독립적으로 해석됐다. 따라서 현재 Backend final refactoring closeout은 **USER-LOCAL BEHAVIORAL PASS**다. 추가 대규모 Backend 구조 분해는 중단하고, 실제 결함 또는 새 기능 요구가 있을 때만 좁은 범위로 재개한다. 다음 주요 개발 단계는 Frontend responsibility refactor다.


## 11. Land provider provenance / Provider resilience D closeout — 2026-09-24

Building-HUB 건축물이 존재하는 SITE 경로에서도 기존 VWorld 토지 조회 결과의 provider provenance를 보존하도록 정렬했다. Building-HUB-present와 parcel-only 경로 모두 토지 조회를 `AVAILABLE / NO_DATA / PROVIDER_FAILED`로 구분하고, provider failure의 `retryable` 값을 public SITE FACT의 `land_status / land_retryable`까지 전달한다.

사용자 로컬 검증에서 `BUILDING_SITE_LAND_ENRICHMENT_CONTRACT_PASS`, `VWORLD_LAND_PROVIDER_CONTRACT_PASS`, `PARCEL_ONLY_LAND_ENRICHMENT_CONTRACT_PASS`, `SITE_FACTS_RESPONSE_CONTRACT_PASS`가 PASS했다. 실제 대표 필지 `1168010300100120000`도 `READY`, `land_status=AVAILABLE`, `land_retryable=False`, official area `121040.4`, buildings `34`, BCR `50`, FAR `250`, rules `314 = 62 / 214 / 36 / 2`를 확인했다. Backend-connected reanalysis E2E와 mobile responsive E2E도 각각 `1 passed`로 사용자 로컬 PASS했다. 이 검증 시점의 HEAD는 `d7cd0ab6896dd70c7da1012560f1a623917de5d5`다.

Provider resilience D의 마지막 presentation 정렬로 Frontend는 이미 전달받고 있던 `SITE_API_ERROR_V1.retryable`을 provider 오류 메시지에 반영한다. `retryable=true`만 사용자에게 다시 시도 가능함을 알리고, `false/null`에는 해당 문구를 붙이지 않는다. 이는 자동 retry, 자동 SITE 재분석, 임의 progress/timeout을 추가하지 않는다. 이 Frontend 변경의 behavioral completion은 focused product-error E2E와 production build의 사용자 로컬 PASS 후 확정한다.

## 12. SITE FACT spatial-condition expansion (E-1) — 2026-09-24
- Public SITE FACT now reuses the spatial-condition results already resolved for the current SITE and consumed by the Rule Engine.
- User-facing spatial facts cover four registered conditions: 지구단위계획, 개발진흥지구, 취락지구, 방재지구.
- Public projection preserves only the stable condition state: `TRUE`, `FALSE`, or `UNKNOWN`. Internal evidence/provider diagnostics are not exposed through this SITE FACT projection.
- Frontend presentation maps `TRUE → 해당`, `FALSE → 비해당`, and `UNKNOWN → 확인 필요`; UNKNOWN is never presented as non-applicable.
- No second VWorld/spatial-provider query path was added for SITE FACT. The same runtime condition result is shared with the Rule Engine.
- User-local verification passed:
  - `site_data.site_facts_response_contract_test` → `SITE_FACTS_RESPONSE_CONTRACT_PASS`
  - `site_data.test_site_analysis_response` → `all_pass: True`
  - `site_data.site_analysis_site_facts_real_data_regression_test` → `all_pass: True`
  - frontend `npm run build` → PASS
  - backend-connected `e2e/site-analysis-reanalysis.spec.ts` → `1 passed`
- E-1 status: **USER-LOCAL BEHAVIORAL PASS / CLOSED**.

## 13. SITE FACT building identity expansion (E-2) — 2026-09-24

- Public SITE FACT already carried Building HUB `management_id`; E-2 validates and presents that existing fact without adding a second provider or SITE truth path.
- Representative parcel `1168010300100120000` returned 34 building items. User-local real-data regression confirmed all 34 management IDs are present and unique.
- The same live response returned `Building.land_area = 0.0` for all 34 items. E-2 therefore does not present building-ledger land area in the product UI; it does not reinterpret `0.0` as a verified physical/site land area.
- `Building.land_area` and its existing converter mapping remain preserved for future source-data investigation; this closeout does not declare the field or mapping defective.
- Frontend `SiteFactsSection` now displays the verified building management ID while keeping building-ledger land area hidden.
- User-local validation:
  - `site_data.site_analysis_site_facts_real_data_regression_test` → `all_pass: True`
  - Frontend production build → PASS (Vite 8.3.0, 28 modules)
  - actual Backend-connected `site-analysis-reanalysis.spec.ts` → `1 passed (24.1s)`
- E-2 status: **USER-LOCAL BEHAVIORAL PASS / CLOSED**.

## E-3 SITE FACT building expansion — 2026-09-24

E-3 is **USER-LOCAL BEHAVIORAL PASS / CLOSED** at code HEAD `6c78fcc870c22459da4cf323ef2d07e5ca9f3e2d`.

The expansion was limited to Building HUB fields whose representative raw-provider evidence and production mapping were verified:

```text
strctCdNm → Building.structure → public SITE FACT structure
pmsDay    → Building.permit_date → public SITE FACT permit_date
```

Representative PNU `1168010300100120000` returned 34 Building HUB title records. Structure was populated for all 34 records; permit date was populated for 30 records and blank for 4, so blank permit dates remain valid rather than being invented or rejected. Roof, seismic, height, parking, elevator fields, Building.land_area changes, Land.district, and Land.land_use_regulation were not included in E-3.

Validation completed user-locally:

```text
SITE FACT real-data regression: PASS
Frontend production build: PASS (Vite 8.3.0, 28 modules)
Actual Backend-connected reanalysis E2E: PASS (1 passed, 24.6s)
SITE_FACTS_RESPONSE_CONTRACT_PASS
```

The public response contract now permanently asserts `structure` and `permit_date`. No second SITE truth path, provider path, spatial query, or Rule Engine path was introduced.

## E-4 SITE FACT building roof — 2026-09-24

E-4 adds the Building HUB title-field `roofCdNm` to the canonical/public SITE FACT building path as `Building.roof`. The provider-supplied roof-name string is preserved as-is apart from whitespace trimming; no numeric/code interpretation or inferred meaning is introduced.

Read-only provider probes established the field before implementation:

```text
개포동 12   : 34 / 34 roofCdNm nonblank
  (철근)콘크리트 32
  기타지붕 2

개포동 12-2 : 9 / 9 roofCdNm nonblank
  (철근)콘크리트 8
  슬레이트 1

Observed total: 43 / 43 nonblank
```

The permanent representative real-provider regression for PNU `1168010300100120000` verifies all 34 public building items have a nonblank `roof` without hard-coding a particular roof type. The public SITE FACT projection contract also fixes the new field.

User-local validation at code HEAD `c73985723852fdd8d8108da70028053abf1ba788`:

```text
SITE_FACTS_RESPONSE_CONTRACT_PASS
SITE FACT real-data regression: all_pass True
Building HUB: 34 / 34 / status 00
Frontend production build: PASS (Vite 8.3.0, 28 modules, 118ms)
Actual Backend-connected reanalysis E2E: PASS (1 passed, 24.4s; test body 23.4s)
Tracked working tree after validation: clean
```

No provider boundary, Rule Engine, spatial/law-data truth boundary, Land fields, or protected output file changed. Therefore **E-4 SITE FACT BUILDING ROOF = USER-LOCAL BEHAVIORAL PASS / CLOSED**.

## 14. E-5 legal-rule semantic checkpoint — 2026-09-28

E-5 legal-rule semantic refinement has progressed through verified mixed-numeric semantics and structural parent/child investigation.

### E-5-B-4C verified mixed numeric semantics

Representative mixed clauses INDEX 89 / 102 / 106 preserve raw numeric values while assigning verified roles:

- 40% = RESULT
  - target: building_coverage_ratio
  - semantic_type: ABSOLUTE_MAX
  - unit: percent
- 50% = APPLICABILITY_THRESHOLD
  - target: additional_site_area_ratio
  - operator: LTE
  - unit: percent_of_existing_site_area

The 50% applicability threshold is not promoted to a numeric effect. No Rule Engine calculation-path change was introduced.

Current user-local behavioral baseline:

- Rules: 314
- APPLICABLE: 58
- NOT_APPLICABLE: 192
- CONDITIONAL: 43
- UNKNOWN: 21
- Numeric candidates: 28
- Rules requiring input: 50
- Rules with unknown condition: 22
- PROJECT inputs: 14
- PROCEDURE inputs: 2
- Unresolved SITE conditions: 4
- all_pass: True

### Structural clause role

The legal-clause parser now records structural hierarchy independently from evaluation semantics:

- CONTAINER: 63
- LEAF: 251

Representative verified cases:

- 71 = CONTAINER
- 72 = LEAF
- 76 = LEAF
- 77 = LEAF
- 115 = CONTAINER
- 189 = CONTAINER
- 250 = CONTAINER

The 농공단지 legal-text alias is normalized to the existing canonical 산업단지 condition.

CONTAINER means only that the clause has structural child clauses. It does not mean exclusion from applicability, condition, numeric-effect, or Rule Engine evaluation.

Final snapshot regression:

- RULES = 314
- STRUCTURAL_ROLES = 251 LEAF / 63 CONTAINER
- ROLE_COUNT_OK = True
- STRUCTURAL_PROPAGATION_OK = True
- APP_BASELINE_OK = True
- all_pass = True

No runtime-wide CONTAINER-to-evaluation-exclusion rule was introduced. law_data/rule_evaluation_pipeline.py remains unchanged by the structural-role correction.

### Remaining E-5 work

E-5 is not globally closed.

Completed foundation work now also includes:

- NUMERIC predicate schema and LTE evaluation;
- typed numeric fact_context input;
- derived additional_site_area_ratio from existing_site_area and additional_site_area;
- TRUE / FALSE / UNSET / UNKNOWN numeric-predicate regression coverage.

Remaining work includes:

- verified production condition-expression population where source structure is sufficiently represented;
- production connection for the verified mixed numeric clauses, including INDEX 89 / 102 / 106, without promoting applicability thresholds to numeric effects;
- branch-local zone predicate semantics;
- spatial predicate semantics where required by legal expressions;
- branch-specific conditions that are over-extracted into aggregate parents or missing from their precise child branch;
- explicit parent base-rule / child exception relationships;
- fail-closed REVIEW_REQUIRED / UNKNOWN behavior where source semantics cannot yet be represented safely.

The current verified expression grammar supports ATOM / AND / OR / NUMERIC / BUILDING_USE. NUMERIC and BUILDING_USE foundation support does not mean that production expressions have been populated or VERIFIED across the 314-clause corpus.

### Building Use / Numeric Fact Rule Engine → API → Frontend checkpoint — 2026-09-30

User-local Behavioral PASS now covers the controlled path from verified Building Use classification into the existing Rule Engine and public product flow:

- `BUILDING_USE` expression evaluation using trusted `fact_context["building_use"]`;
- controlled Rule 125 공연장 branch integration with `applicable_use_floor_area > 1000 square_meter`;
- expression-derived `BUILDING_USE` / `NUMERIC_FACT` requirements;
- remaining-input aggregation for project / procedure / building_use / numeric_facts;
- Site Analysis internal requirement projection and public API requirement output;
- public canonical `building_use_name` and validated `numeric_facts` input through `site_analysis_fact_input`;
- Frontend canonical Building Use / Numeric Fact additional-input UI and selected-candidate reanalysis;
- Frontend production build PASS and actual Backend-connected reanalysis/mobile-responsive E2E PASS.

This closes the previously listed user-facing required-input aggregation item for the verified controlled scope. It does **not** close E-5 globally. Actual production 314-clause expression population/verification remains separate work. Rule 125 validation is limited to the controlled 공연장 branch; 집회장/관람장 are not proven by this checkpoint. Annex 1 Building Use coverage is not claimed complete, and unresolved facts continue to use the existing fail-closed UNSET / UNKNOWN / REVIEW_REQUIRED boundaries.

Automatic expression generation for all 314 clauses or all multi-condition clauses is not authorized.

### Current local repository protection state

The development checkout contains intentional local-only modified outputs transferred between the two active development environments.

Specially protected local file:

law_data/output/urban_area_conversion_history_final_resolution.json

This file remains outside ordinary restore/reset/stage/commit operations unless separately and explicitly authorized.

Desktop handoff is a recurring synchronization procedure between two active development environments, not a one-time PC replacement.

## Building Use official-source / structural-parser checkpoint — 2026-09-28

건축물 용도 자동화의 공식 원문 경로를 기존 국가법령정보 API infrastructure 위에서 검증했다. 별도의 Building Use 전용 API client를 만들지 않고 기존 `lawService.do` + appendix normalization을 재사용한다.

사용자 로컬 Behavioral PASS:

```text
건축법 시행령 current MST 자동 탐색: PASS (288849)
별표 1 "용도별 건축물의 종류(제3조의5 관련)" 취득: PASS
별표 1 content length: 10924
본문 / 비고 분리: PASS
건축물 용도 source MAJOR 30개 구조 추출(기본번호 1..29 + 가지번호 23의2): PASS
2/라/1 일반기숙사: PASS
2/라/2 임대형기숙사: PASS
14/나/2 오피스텔: PASS
wrapped "말한" + "다."의 가짜 다목 방지: PASS
official API physical raw_lines provenance 보존: PASS
Structural Parser RESULT: PASS (188 structural units / 30 source MAJOR nodes / 23의2 독립 가지번호 보존)
```

관련 code checkpoint:
- source probe: `381a577d6d74324159ec4416ce890217aaebba7f`
- structural parser 최초 PASS: `5a45dd3ab8fdaa618ce401f0dd93311cdfcd941a`
- raw-lines provenance 보존 PASS: `13009e0297d09c359c692d8727005b181ca84b78`

현재 완료 범위는 **official source retrieval + source hierarchy extraction**이다. API physical line wrap은 단어 사이와 단어 내부 모두에서 발생하므로 reconstructed `text`를 공식 원문의 완전한 띄어쓰기 복원본으로 취급하지 않는다. 각 structural node의 `raw_lines`를 source provenance로 보존한다.

아직 완료되지 않은 범위:
- Canonical Building Use semantic taxonomy
- Building Use Identity / Qualification Predicate 분리
- 별표 1 전체 세부조건의 Numeric / Exception / Cross-reference 의미분류
- current 314-rule PROJECT condition mapping
- Rule Engine production integration

따라서 **source retrieval/parsing PASS는 semantic legal approval 또는 ENGINE_READY를 의미하지 않는다.**
## Building Use qualification automation scope checkpoint — 2026-09-29

Building Use Qualification은 현재 사용자 로컬 검증 기준으로 SourcePath 공통 Qualification 29건과 Canonical-specific Qualification 1건까지 Behavioral PASS다. Canonical-specific 첫 검증 사례는 `3/아 + 통신용 시설`이며, `3/아` SourcePath 자체는 의도적으로 미등록 상태를 유지한다. 이 경계는 동일 SourcePath의 변전소·도시가스배관시설·정수장·양수장에 통신용 시설의 1,000㎡ 조건이 잘못 전파되는 것을 방지한다.

현재 개발 단계는 `4/카 ↔ 10/다 ↔ 10/라`처럼 공통 Qualification과 canonical-use별 Qualification이 함께 필요한 사례를 검토하는 단계다.

이 단계부터 Annex 1의 모든 문구를 완전 자동판정하는 것 자체를 목표로 삼지 않는다. 실제 Canonical Building Use 선택 또는 후속 법규검토 결과를 바꾸는 명확한 numeric / classification exclusion / 검증 가능한 state 조건을 우선 자동화한다. 현재 확보 가능한 Fact만으로 안전하게 판정할 수 없는 복잡한 조건은 억지로 TRUE/FALSE로 만들지 않고 REVIEW_REQUIRED 또는 UNSET 경계를 유지한다.

다음 전환 체크포인트는 Qualification coverage를 다시 측정한 뒤 Canonical final classification에 필요한 핵심 조건이 충분한지 판단하는 것이다. 충분하면 Annex 1 세부조건 확장을 계속하는 대신 Canonical final classification → PROJECT Mapping → API → Frontend 순서로 전진한다.

개발 속도 원칙: 동일 구조이고 READ-ONLY 검증으로 의미가 확인된 항목은 안전한 범위에서 batch 처리한다. 단, 법적 의미·데이터 계약·평가 구조가 다른 항목을 속도를 이유로 한 묶음에 넣어 오류 가능성을 높이지 않는다.

## Building Use qualification re-audit checkpoint — 2026-09-29

앞서 구현된 Building Use source/parser/semantic/canonical/qualification/resolver 계층을 현재의 자동화 범위 원칙으로 재검토했다. 현재 확인된 구조를 대규모로 되돌리거나 제거할 근거는 없다. 특히 numeric boundary, major-use classification exclusion, four-state fail-closed resolver, SourcePath-common + Canonical-specific qualification은 실제 법정 용도분류 결과를 바꾸는 기반으로 유지한다.

일반기숙사·임대형기숙사처럼 복수 STATE와 numeric fact를 결합한 기존 검증 사례도 유지한다. 다만 이를 Annex 1 전체에 동일한 깊이로 확대하여 세부 STATE를 무제한 추가하는 것을 후속 목표로 삼지 않는다.

현재 진행 우선순위는 Qualification rule 개수 자체를 늘리는 것이 아니다. `4/카 ↔ 10/다 ↔ 10/라`처럼 Canonical final classification을 실제로 바꾸는 대표 공백을 우선 검토·보완한 뒤 Qualification Coverage Audit으로 이동한다.

향후 진행축:
```text
representative classification gaps
→ Qualification Coverage Audit
→ Canonical Final Classification
→ PROJECT Mapping
→ existing Rule Engine
→ API
→ Frontend
```

Coverage Audit에서는 자동판정 가능한 항목과 REVIEW_REQUIRED / UNSET으로 남는 항목을 명시적으로 구분한다. 핵심 분류에 필요한 coverage가 충분하면 Annex 1 qualification 숫자를 계속 늘리는 대신 PROJECT Mapping으로 전환한다.


## Building Use cross-classification / progressive requirement checkpoint — 2026-09-30

User-local Behavioral PASS now covers the verified Annex 1 cross-classification path for 체육관 / 운동장:

```text
체육관 또는 운동장
→ has_spectator_seating
→ spectator_seating_area >= 1000 square_meter
→ 관람장
→ SourcePath 5/다
→ 문화 및 집회시설
```

The cross-classification candidate layer, narrow Final Classifier promotion, and Building Use classification requirement bridge are separately implemented. The requirement bridge does not duplicate the 1,000㎡ legal threshold; it reads the already-verified cross-classification expression and requests only the currently decisive missing fact. With no spectator facts it requests `has_spectator_seating`; after TRUE it requests `spectator_seating_area`; after FALSE it does not request the area.

This checkpoint does not expand the general Final Classifier whitelist. 집회장 remains outside this cross-classification registry. Public API / Frontend support for `has_spectator_seating` and user-declared numeric UNKNOWN is not yet implemented, and the Rule 125 관람장 production branch is not proven by this checkpoint.

The existing four-state boundary is retained for project-stage facts: UNSET means no answer/fact has been supplied; UNKNOWN means a fact has been supplied but cannot currently support a definitive result. The Rule Engine already evaluates a numeric fact shaped as `{"state": "UNKNOWN"}` as UNKNOWN, and the Building Use requirement bridge does not re-request that fact as an unanswered requirement. A focused contract test locks this existing behavior; public product input for declaring a numeric value "아직 미정" remains future work.


## Building Use public qualification input / SITE requirement integration — 2026-09-30

Backend public input now has a narrow contract for the verified 체육관 / 운동장 → 관람장 classification path. `has_spectator_seating` is accepted only as a dedicated optional boolean and converted internally to STATE TRUE/FALSE. Numeric facts retain the existing `value + unit` contract and additionally allow an explicit `undecided: true` form with no value; the Backend converts that form to internal numeric UNKNOWN. A request that marks a numeric fact undecided while also supplying a value is rejected by the API model and ignored fail-closed by the lower public-fact boundary.

SITE Analysis input requirements now include Building Use classification prerequisites. The verified progressive sequence is intended to be: first request `has_spectator_seating`; only after TRUE request `spectator_seating_area`; after FALSE request no area; a concrete area resolves the verified cross-classification boundary; explicit undecided remains UNKNOWN and is not re-requested as missing.

This checkpoint changes Backend/public contract only. Frontend controls for these fields are not yet implemented. Rule 125 관람장 production applicability is still not proven or persisted by this work. User-local Behavioral PASS is required before this checkpoint is treated as validated integration.

## Building Use public catalog → Frontend progressive-input checkpoint — 2026-10-01

The verified public Building Use discovery boundary is now connected to the Single Parcel Frontend.

Backend public discovery:
- `GET /v1/building-uses`
- schema: `BUILDING_USE_CATALOG_V1`
- verified public option count: 15
- the catalog is the union of the existing Final Classifier whitelist and verified cross-classification input names; it is not the full Annex 1 catalog.

Frontend behavior:
- the planned-building-use selector consumes the Backend catalog instead of maintaining an independent legal-use list;
- the selected canonical name is sent through the existing `building_use_name` reanalysis input;
- classification follow-up questions are rendered only from Backend `requirements`;
- for the verified 체육관 path, Backend first requests `has_spectator_seating`; after TRUE it requests `spectator_seating_area`;
- public numeric `undecided: true` is preserved as internal UNKNOWN and is treated as answered rather than re-requested as missing.

User-local validation:
```text
Frontend production build:
tsc -b && vite build
Vite 8.3.0 / 28 modules transformed
PASS

Actual Backend-connected reanalysis E2E:
e2e/site-analysis-reanalysis.spec.ts
2 passed (31.4s)
- existing multi-parcel/reanalysis/state-isolation regression PASS
- 체육관 → 관람석 → spectator area → 아직 미정 progressive flow PASS

Actual Backend-connected mobile responsive regression:
e2e/site-analysis-mobile-responsive.spec.ts
1 passed (5.4s)
```

Status: **IMPLEMENTED + USER-LOCAL BEHAVIORAL PASS** for this verified public/progressive scope.

This checkpoint does not prove full Annex 1 public coverage, direct 집회장 support, full Rule 125 production applicability, or Rule 125 관람장 production integration. Those remain separate work.
