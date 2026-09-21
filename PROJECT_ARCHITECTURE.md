# AI 대지분석 자동화 시스템 — PROJECT ARCHITECTURE

최종 reconciliation: 2026-09-21
Architecture Baseline: v1.2

## 1. 프로젝트 목표

주소 또는 필지를 입력하면 canonical SITE/PNU와 공식 데이터·법적 근거를 추적하여 규제 TRUE/FALSE/UNKNOWN, 적용 법령과 고시, 계산 가능한 규제값, 조건부 결과, provenance와 검증 가능한 최종 대지분석을 생성한다.

## 2. 최상위 원칙

```text
OFFICIAL FACT
→ SITE FACT
→ REGULATION RESOLUTION
→ LEGAL RULE
→ DETERMINISTIC ENGINE
→ AI ANALYSIS
→ VERIFICATION
```

불변조건:
- 검색 결과 ≠ 법적 사실
- 주소 검색 결과 ≠ canonical parcel truth
- candidate parcel ≠ canonical parcel truth
- 사용자 UI 선택 ≠ canonical parcel truth
- 문서 발견 ≠ 규제 TRUE
- 고시 발견 ≠ 현재 유효
- point 포함 ≠ parcel 포함
- source 미발견 ≠ FALSE
- resolver result ≠ parcel applicability
- SITE-decision eligibility ≠ SITE truth
- SITE applicability admission ≠ production/runtime registration authority
- promotion authorization ≠ second SITE truth store
- verified envelope ≠ new Rule Engine
- 다른 PNU의 identity/address/zone/coordinate/geometry/evidence 재사용 금지

## 3. 전체 레이어

```text
USER / PROJECT INPUT
→ PARCEL IDENTITY & OFFICIAL LAND DATA
→ SITE FACT MODEL
→ REGULATION RESOLUTION
→ LEGAL KNOWLEDGE
→ RULE NORMALIZATION
→ DETERMINISTIC EVALUATION
→ RETRIEVAL & LEGAL CONTEXT
→ AI ANALYSIS
→ VERIFICATION & PROVENANCE
→ PRODUCT / API / REPORT
```

SITE CONDITION과 PROJECT CONDITION을 분리한다. PROJECT 조건을 SITE 사실로 자동 승격하지 않는다.

## 4. Canonical SITE / PNU

모든 후속 판정은 동일한 실제 필지를 바라봐야 한다.

```text
Public API / Building HUB plat_gb_cd=0 (일반) → PNU land-register digit 1
Public API / Building HUB plat_gb_cd=1 (산)   → PNU land-register digit 2
```

Building HUB status `00` + 건축물 0건도 canonical parcel identity가 유효하면 parcel-only Site를 구성할 수 있다.

### 4A. Address → verified canonical parcel identity

```text
USER PARCEL ADDRESS
→ safe parcel-address normalization
→ VWorld parcel address search
→ exact address.parcel match
→ search item.id PNU
→ item coordinate
→ live LP_PA_CBND_BUBUN polygon query
→ polygon PNU
→ address PNU == polygon PNU
→ PNU component decomposition
→ create_pnu() regeneration == original PNU
→ VERIFIED canonical parcel identity
```

검색이 `12`, `12-1`, `12-10` 등을 함께 반환하더라도 exact parcel-address match 전에는 어느 후보도 canonical identity가 아니다. Empty/no-exact/mismatch/ambiguous/invalid/unresolved states fail closed.

### 4B. Verified address → existing parcel analysis

```text
VERIFIED ADDRESS PARCEL IDENTITY
→ canonical parcel components
→ existing analyze_site_by_parcel()
→ existing SITE / regulation / Rule Engine pipeline
```

`analyze_site_by_address()`는 identity front door / adapter이며 별도 분석 engine이 아니다.

## 5. Public HTTP address boundary — VALIDATED

Public address endpoint is now validated:

```text
POST /v1/site-analysis/address
→ Pydantic address request validation
→ analyze_site_by_address()
→ verified identity only
→ existing analyze_site_by_parcel()
→ SITE_ANALYSIS_API_V1 response
```

User-local real HTTP E2E at code HEAD `f54cd84b6c91cd2f8c0e47612223133daac97a4d` confirmed:
- ordinary `서울특별시 강남구 개포동 12번지` → PNU `1168010300100120000`, Building HUB 34, identity COMPLETE, READY
- mountain `서울특별시 동작구 동작동 산 29-3` → PNU `1159010600200290003`, Building HUB 0 parcel-only path, identity COMPLETE, READY

The HTTP layer does not parse PNU, query VWorld, or duplicate parcel analysis. Existing `/v1/site-analysis` parcel-component endpoint remains separate and unchanged in purpose.

Public historical inputs remain NOT AUTHORIZED.

## 6. Candidate discovery boundary — DESIGN DIRECTION

Candidate search is a product discovery function, not identity verification and not analysis admission.

Current VWorld parcel search response already provides candidate metadata that can support a list/map UX:

```text
candidate
├─ item.id              → candidate PNU identifier
├─ address.parcel       → parcel address
├─ address.road         → road address when supplied
├─ address.bldnm        → building name when supplied
└─ point.x / point.y    → map centering point
```

The existing exact resolver currently uses the same search provider internally but intentionally filters to exact `address.parcel` matches and then performs live polygon PNU verification. Its fail-closed semantics must not be weakened to expose prefix candidates.

Preferred architecture separation:

```text
DISCOVERY BOUNDARY
user query
→ normalize only for search compatibility
→ VWorld parcel candidate search
→ sanitize candidate metadata
→ return candidate list
→ NO VERIFIED status
→ NO analysis admission

SELECTION / VERIFICATION BOUNDARY
selected candidate PNU + selected parcel context
→ backend live parcel re-verification
→ selected PNU == live polygon PNU
→ canonical component regeneration
→ VERIFIED identity
→ existing analysis pipeline
```

Candidate PNU is an identifier supplied by the search provider, not canonical truth until re-verification.

The candidate response should be intentionally smaller than raw VWorld data. Recommended initial fields:
- `candidate_pnu`
- `parcel_address`
- `road_address`
- `building_name`
- `x`
- `y`
- `crs=EPSG:4326`

Do not expose provider API keys, raw transport response, SITE truth, regulation result, or VERIFIED status in discovery.

## 7. Map boundary direction

Candidate point coordinates are sufficient for initial map centering/markers but not sufficient to prove parcel inclusion. Parcel polygon visualization should use live parcel geometry associated with the selected/reverified PNU.

Future list/map flow:

```text
query
→ candidates
→ list + map points
→ user selects candidate
→ backend re-verification
→ verified PNU polygon
→ highlight parcel
→ user confirms analysis
```

Map click selection can later become another discovery input but must converge into the same verification boundary.

## 8. Runtime spatial / regulation architecture

Runtime spatial condition continues to require parcel geometry/PNU/CRS verification. Spatial query failure is not FALSE. Historical provenance remains outside the spatial runtime condition channel.

Validated numbered architecture chain remains:

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
```

No new STEP number is created for address/API/product boundaries.

## 9. Historical / district-unit / hybrid locks

Historical and district-unit paths keep family-specific verification and converge only at the authorized common production lane. No second SITE truth store or Rule Engine is created. Simultaneous historical + district-unit production remains fail-closed without explicit merge policy.

UQQ700 remains `HYBRID_SPATIAL_NOTICE`, standard code `UQQ700`, legal-source resolution UNKNOWN, SITE TRUE/FALSE promotion blocked, production/runtime registration blocked.

## 10. Legal / provenance / deterministic evaluation

Legal delegation/version chains and provenance remain preserved. AI may explain but does not invent regulation TRUE/FALSE, PNU, legal source or numeric limit. Calculable results belong to deterministic evaluation; unresolved conditions remain unresolved.

## 11. Product UX separation

- `PROJECT_ARCHITECTURE.md`: validated boundaries and safety invariants
- `PROJECT_STATUS.md`: implementation / behavioral checkpoint
- `PROJECT_PRODUCT_UX.md`: product ideas, candidate workflows, map interactions and backlog

## 12. Security / repository policy

- API keys in `.env`; secrets Git 저장 금지
- runtime raw/cache와 Git source 분리
- `law_data/output/*` 보호
- explicit WRITE approval before repository mutation
- user-local behavioral PASS is final validation

## 13. Public result presentation boundary

The deterministic Rule Engine remains the sole legal applicability evaluator. Product-facing rule detail must be derived from the already-evaluated final rules through a presentation adapter:

```text
INTERNAL RULE ENGINE
→ deterministic evaluated rules
→ PRODUCT PRESENTATION ADAPTER
→ public SITE analysis result
→ Frontend presentation
```

The adapter may expose stable, existing rule facts needed for explanation, including clause index, law name, rule title, paragraph/item/subitem, category, applicability, applicability reason, rule text, relevant unresolved/required/blocking conditions, and numeric effect where supported.

It must not expose raw engine/debug implementation as the product contract. `baseline`, branch-overlay internals, registry raw payloads, repairs, dynamic injection internals, numeric guards, or `debug.rule_engine` remain internal unless a later architecture decision explicitly promotes a field. A product presentation model must not create a second legal conclusion or reinterpret `UNKNOWN`.

## 14. Product analysis-target direction

The current validated analysis target is one canonical PNU / parcel. Future Integrated Development must not weaken that atomic parcel authority.

Proposed target hierarchy:

```text
PARCEL
official atomic PNU unit
    ↓ 1..N verified members
ASSEMBLED_SITE
one proposed development site composed by the user
    ↓ surrounding context
SITE CONTEXT
roads / neighboring parcels / planning context / facilities
```

Multiple selected parcels are not intended as a core "independent parcels in parallel" product mode. They are intended to compose one proposed integrated development site.

Important future invariants:

```text
verified member parcel truth != assembled-site truth
assembled-site truth != cadastral merge eligibility
cadastral merge ineligibility != automatically integrated-development ineligibility
parcel applicability != target applicability
```

Integrated Development must separately evaluate cadastral merge conditions, building-site composition where legally relevant, planning/common-development constraints, geometry/adjacency, mixed regulation, target-level applicability, and surrounding context. User selection alone never proves legal merge or integrated-development eligibility.

This direction is PROPOSED architecture for the next major product phase; it is not yet an implemented Backend target model and does not alter the current v1.2 Single Parcel pipeline.

## 15. Current transition

Single Parcel v1 should be closed before the Integrated Development target model is implemented. The immediate architecture work is the public rule presentation boundary, followed by a machine-readable product error boundary and final Single Parcel regression. No new numbered architecture STEP is introduced for these product boundaries.


## 15. Backend provider boundary checkpoint — 2026-09-21

Architecture/code-quality checkpoint after Single Parcel v1 identified external provider I/O as a separate responsibility from SITE orchestration. Building HUB transport is therefore being isolated behind `site_data/building_hub_provider.py`.

The intended boundary is:

```text
Building HUB HTTP / DATA_API_KEY / response normalization
→ building_hub_provider.fetch_building_items()
→ normalized building provider result
→ site_analysis_orchestrator
→ canonical Site construction
→ verified legal-input admission
→ existing analysis / public response
```

This extraction does not create a second SITE path and does not change canonical PNU, Building HUB semantics, Rule Engine, historical/district-unit admission, public API schema, or Frontend contracts. Provider failures remain product-mapped at the HTTP boundary through `BuildingAPIError`.

The next backend architecture checkpoint should evaluate verified-input admission/rebinding separately from provider I/O; it must not weaken the existing fail-closed PNU/envelope contracts.


### 15A. Validation status

The Building HUB provider extraction was user-local behavioral PASS at HEAD `d46a3afbbead00341fa2a8f2a7581cbf26760009`. Provider extraction therefore remains an architecture-only responsibility split with preserved runtime behavior.


## 16. Verified SITE input admission boundary — 2026-09-21

Historical and district-unit verified inputs now have a dedicated fail-closed admission boundary in `site_data/verified_site_input_admission.py`. The orchestrator remains responsible for sequencing, while the admission boundary owns mutual-exclusion checks, canonical-PNU rebinding, historical consistency/binding/adapter gates, and sealing of the verified historical envelope.

The architectural invariant is unchanged: external verified input is not trusted merely because it is typed or previously verified; it must be rebound to the actual canonical Site PNU immediately before analysis. Historical and district-unit verified inputs remain mutually exclusive in this lane. The extraction is not considered behaviorally complete until the pre-existing focused admission contract and historical end-to-end regression pass unchanged after the move.


### 16A. Validation status

The verified SITE input admission extraction is user-local behavioral PASS at HEAD `6a55eab6eb51c8c1a76e4bb1d6d197fbc3c9caf6`. The pre-refactor fail-closed safety contract and historical promotion end-to-end path both remained green after responsibility extraction, confirming that canonical-PNU rebinding and verified-envelope admission semantics were preserved.


## 17. Public SITE facts projection boundary — 2026-09-21

The public projection of already-canonical land/building facts is isolated in `site_data/site_facts_response.py`. This boundary is presentation-only: it may map canonical `Site.land` / `Site.buildings` and their provenance into the existing public `site_facts` shape, but it must not call providers, verify PNU, resolve regulation, or make legal applicability decisions. `site_analysis_response.py` remains the owner of the overall `SITE_ANALYSIS_API_V1` response contract.

This extraction is intentionally additive/structural and must preserve the existing public schema and real-data values. Behavioral completion requires focused projection, public response, real-data SITE FACT, and actual Backend-connected UI regression to remain green.


### 17A. Validation status

The public SITE facts projection extraction is user-local behavioral PASS at HEAD `ecc2cd1952855939f375131cdd774e6d0d9127b0`. Focused projection, public response, real-data SITE FACT, and actual Backend-connected UI regressions all remained green after extraction, confirming that this is a presentation-only responsibility split with preserved public schema and values.


## 18. Zone relevance classifier production boundary — 2026-09-21

용도지역 relevance 판정은 `law_data/zone_relevance_classifier.py`가 production 소유권을 가진다. Rule Evaluation Pipeline과 clause-split regression은 이 동일 classifier를 소비하며, production runtime이 `*_test.py` 구현에 의존하지 않는다.

```text
normalized legal clause
→ production zone relevance classifier
→ zone relevance result
→ deterministic Rule Evaluation Pipeline
→ final SITE composition
→ public rule presentation
```

이 분리는 판정 알고리즘 변경이 아니라 dependency-direction 정규화다. 사용자 로컬 회귀에서 standalone pipeline의 현재 의미론 `62 / 213 / 36 / 3`과 spatial SITE composition 이후 최종 public 의미론 `62 / 214 / 36 / 2`가 각각 검증되었다. 최종 public UNKNOWN은 기존과 같이 도시지역편입해제구역 조건의 clause 47, 48 두 건이다.

전체 실행 snapshot은 classifier 외 runtime spatial 상태와 누적 production 결과도 포함하므로 classifier refactor와 동일한 변경 단위로 취급하지 않는다. snapshot baseline reconciliation은 별도 검증 경계로 유지한다.
