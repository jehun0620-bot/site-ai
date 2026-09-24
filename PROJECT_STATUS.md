# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-09-22
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
