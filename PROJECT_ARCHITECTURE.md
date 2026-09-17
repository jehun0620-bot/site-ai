# AI 대지분석 자동화 시스템 — PROJECT ARCHITECTURE

최종 reconciliation: 2026-09-17
Architecture Baseline: v1.2

## 1. 프로젝트 목표

주소 또는 필지를 입력하면 canonical SITE/PNU와 공식 데이터·법적 근거를 추적하여 규제 TRUE/FALSE/UNKNOWN, 적용 법령과 고시, 계산 가능한 규제값, 조건부 결과, provenance와 검증 가능한 최종 대지분석을 생성한다.

핵심 질문:
> 이 필지에는 정확히 어떤 규제가 적용되고, 그 사실은 어느 공식 데이터·공간정보·지정고시·법령에서 확정되며, 따라서 무엇을 얼마나 지을 수 있는가?

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
- LLM 합의 ≠ source verification
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

모든 후속 판정은 동일한 실제 필지를 바라봐야 한다. 다른 PNU의 snapshot, geometry, evidence, admission, promotion input을 재사용하지 않는다.

Public API / Building HUB와 PNU의 필지구분은 서로 다른 코드 체계이므로 명시적으로 변환한다.

```text
Public API / Building HUB plat_gb_cd=0 (일반) → PNU land-register digit 1
Public API / Building HUB plat_gb_cd=1 (산)   → PNU land-register digit 2
```

Building HUB status `00` + 건축물 0건도 canonical parcel identity가 유효하면 parcel-only Site를 구성할 수 있다. 건축물 존재 여부를 필지 존재 여부와 동일시하지 않는다.

Parcel-only enrichment는 현재 canonical PNU와 정확히 같은 공식 토지특성 record에만 의존한다. 동일-PNU VWorld Land Characteristics에서 지목, 용도지역, 공식 토지면적, 지번주소를 보강할 수 있지만 다른 PNU의 persisted snapshot/identity fallback은 사용할 수 없다.

### 4A. Address → verified canonical parcel identity

주소 입력은 PNU를 추측하는 shortcut이 아니다. 현재 validated address resolver는 다음 경계를 사용한다.

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

일반 지번의 말미 `번지` 표기는 검색 호환을 위해 안전하게 정규화할 수 있다. 예: `서울특별시 강남구 개포동 12번지` → 검색값 `서울특별시 강남구 개포동 12`.

검색어 `12`가 `12`, `12-1`, `12-10` 등을 함께 반환하더라도 exact `address.parcel` match 전에는 어느 후보도 canonical identity가 아니다. Exact match 이후에도 address-search PNU와 live parcel polygon PNU가 같아야 한다.

다음은 fail-closed다:
- search empty
- exact parcel-address match 없음
- address PNU / polygon PNU mismatch
- multiple distinct verified PNUs
- invalid/non-reconstructable PNU
- missing VWorld key
- live parcel PNU unresolved

User-local real-data validation at behavioral PASS HEAD `52f7b65e268fe4384553f84293d56ff5d129eb3e` confirmed:
- ordinary `서울특별시 강남구 개포동 12번지` → `1168010300100120000`, `plat_gb_cd=0`, VERIFIED
- mountain `서울특별시 동작구 동작동 산 29-3` → `1159010600200290003`, `plat_gb_cd=1`, VERIFIED

This resolver is currently an internal verified identity boundary. Public address-to-analysis wiring and user-selectable candidate UX are separate later boundaries.

## 5. Runtime spatial SITE fact

Runtime spatial condition은 parcel geometry, target PNU, CRS, regulation geometry intersection을 검증한다. Spatial query 실패를 FALSE로 바꾸지 않는다. Historical provenance는 spatial runtime condition channel과 별도로 유지한다.

Parcel-only 경로에서는 동일-PNU 공식 지번주소가 확보되면 address search를 통해 좌표를 구하고, VWorld parcel dataset의 live polygon feature PNU가 requested canonical PNU와 정확히 일치할 때만 `PNU_POLYGON_VERIFIED` geometry로 채택한다.

EPSG:4326 live geometry는 공간 판정용으로 유지하며 면적을 임의 계산하지 않는다. 공식 토지면적은 VWorld Land Characteristics의 `lndpclAr`을 별도 `square_meter` 값으로 보존한다.

## 6. Regulation resolution / numbered chain

표준 상태는 `TRUE / FALSE / UNKNOWN`이다. 주요 family는 `SPATIAL_DATA_CONFIRMED`, `NOTICE_CONFIRMED`, `LEGAL_RULE_CALCULATED`, `HYBRID_SPATIAL_NOTICE`, `HISTORICAL_SITE_EVENT`, `EXTERNAL_AUTHORITY_REQUIRED`다.

현재 validated numbered architecture chain:

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

STEP114는 candidate SITE decision eligibility이며 SITE truth가 아니다. 이후 구현 경계에는 새 STEP 번호를 부여하지 않는다.

## 7. Historical SITE applicability / promotion / production

Historical path는 PNU-bound applicability와 promotion authorization을 거쳐 existing production consumption lane으로만 들어간다. Promotion은 별도 SITE truth store나 Rule Engine이 아니다.

```text
STEP114 verified candidate
→ verified parcel applicability
→ actual SITE PNU rebinding
→ candidate/repair/condition binding
→ promotion authorization/execution/bridge where authorized
→ Orchestrator actual-SITE PNU recheck
→ HistoricalVerifiedRuleInputEnvelope
→ Service / Builder PNU recheck
→ historical collision / live authorization
→ common verified SITE registry
→ existing Rule Engine
```

Raw historical production injection, malformed envelopes, PNU mismatch, UNKNOWN applicability, unauthorized promotion, and public historical injection remain fail-closed.

## 8. District-unit / common verified production lane

District-unit production transport remains validated through the existing Rule Engine architecture.

```text
verified district-unit envelope
→ Orchestrator actual-SITE PNU recheck
→ Service typed-envelope / PNU recheck
→ Builder typed-envelope / PNU recheck
→ district spatial collision / live authorization
→ common verified SITE registry
→ existing Rule Engine
```

Historical and district-unit inputs are not implicitly merged. Without an explicit cross-family merge policy, simultaneous production input fails closed. This creates no new architecture STEP and does not authorize UQQ700.

## 9. Public API / runtime exposure

Public FastAPI historical internal input remains NOT AUTHORIZED. Historical provenance remains outside the spatial runtime condition channel.

Current validated public parcel request accepts `sigungu_cd / bjdong_cd / plat_gb_cd / bun / ji`; ordinary and mountain HTTP E2E are user-local validated.

Address identity resolution is now validated internally, but public address-to-analysis wiring is not yet validated. The next production-facing boundary is:

```text
VERIFIED ADDRESS PARCEL IDENTITY
→ canonical parcel components
→ existing analyze_site_by_parcel pipeline
```

Do not create a second analysis pipeline for address input. Address resolution must converge into the existing canonical parcel path.

Future candidate-list/map-assisted selection belongs to product UX design (`PROJECT_PRODUCT_UX.md`). Even after a user selects a candidate, backend same-PNU verification remains required before analysis.

## 10. Authority / historical evidence

Official-looking host만으로 competent authority가 되지 않는다.

```text
OFFICIAL HOST
→ REGION BINDING
→ SOURCE ROLE
→ LEGAL AUTHORITY SCOPE
→ TARGET REGULATION COMPATIBILITY
```

Historical discovery에서도 endpoint 발견, query 결과, search title, source 미발견만으로 target document verification 또는 FALSE를 만들지 않는다. Designation/change/release/cancellation/supersession timeline과 provenance를 보존한다.

## 11. Hybrid spatial/notice / UQQ700

HYBRID TRUE의 최소 원칙:

```text
OFFICIAL_DESIGNATION_IDENTITY_VERIFIED
+
CURRENT_VALIDITY_VERIFIED
+
SITE_SPATIAL_INCLUSION_VERIFIED
→ TRUE candidate
```

### UQQ700 개발밀도관리구역
- family: `HYBRID_SPATIAL_NOTICE`
- standard code: `UQQ700`
- legal-source resolution: UNKNOWN
- negative evidence / legal absence inference disabled
- SITE TRUE/FALSE promotion blocked
- production/runtime registration blocked

## 12. Legal knowledge / deterministic Rule Engine

법률→시행령→시행규칙→조례→고시→별표→지침의 delegation/version chain을 보존한다. Condition family는 SITE / PROJECT / PROCEDURE / AUTHORITY / TEMPORAL / SPATIAL로 분리한다. 계산 가능한 결과는 Rule Engine이 결정하고 조건이 확정되지 않으면 숫자를 임의 확정하지 않는다.

## 13. Provenance / verification

모든 중요한 결과는 다음처럼 역추적 가능해야 한다.

```text
Final result
→ Rule / resolution
→ official/legal source
→ version/event
→ canonical SITE/PNU binding where applicable
```

AI는 설명과 쟁점 발견을 담당하되 규제 TRUE/FALSE, PNU, 법적 source 또는 수치 상한을 임의 생성하지 않는다.

## 14. Test / fail-safe policy

Test categories: UNIT / BEHAVIORAL REGRESSION / INTEGRATION / END-TO-END / POLICY ASSERTION.

```text
잘못된 TRUE보다 UNKNOWN이 낫다.
잘못된 FALSE보다 UNKNOWN이 낫다.
```

Behavioral PASS HEAD `52f7b65e268fe4384553f84293d56ff5d129eb3e` includes the previously validated parcel/public/historical/district-unit contracts plus `ADDRESS_PARCEL_IDENTITY_RESOLVER_CONTRACT_PASS` and real-data ordinary/mountain address identity verification.

## 15. Product UX separation

Architecture truth and product ideas are deliberately separated.

- `PROJECT_ARCHITECTURE.md`: validated system boundaries, invariants, authority and data-flow rules
- `PROJECT_STATUS.md`: current implementation/validation checkpoint and next work
- `PROJECT_PRODUCT_UX.md`: product-facing ideas, candidate workflows, map interactions and implementation backlog

A UX idea does not become implemented architecture merely because it is documented. Conversely, UI convenience must never bypass canonical PNU verification.

## 16. Security / repository policy

- API keys in `.env`; secrets Git 저장 금지
- runtime raw/cache와 Git source 분리
- `law_data/output/*` 보호
- explicit WRITE approval before repository mutation
- user-local behavioral PASS is final validation

## 17. Numbering policy

Architecture STEP98…STEP114와 legal-source investigation S-numbering은 별개다. 새 architecture STEP은 repository design/documentation에서 명시적으로 확립할 때만 부여한다.

## 18. Current validated architecture position

```text
USER PARCEL COMPONENTS
→ canonical PNU
→ existing parcel analysis pipeline

USER PARCEL ADDRESS
→ normalized/exact parcel search
→ address PNU + coordinate
→ live parcel polygon PNU verification
→ reconstructed canonical parcel identity
→ VERIFIED
→ [production/public wiring not yet validated]

canonical parcel identity
→ ordinary Building HUB path OR parcel-only zero-building path
→ same-PNU official land enrichment
→ canonical SITE identity
→ same-PNU spatial recovery / exact-PNU polygon verification where available
→ regulation resolution / deterministic evaluation
```

Historical and district-unit verified transports remain on the single common production consumption architecture. No second SITE truth store or Rule Engine is created.

## 19. Next design question

The next architecture question is no longer how to resolve a parcel address; that internal boundary is validated. It is how to transport a VERIFIED address-derived identity into the existing production/public parcel analysis path without creating a second path.

Required READ-ONLY audit targets include current `api_app.py`, `site_data/site_analysis_orchestrator.py`, and relevant service boundary. Preserve:
- verified identity only; never raw search result
- canonical PNU exact regeneration
- ordinary/mountain distinction
- same-PNU evidence boundary
- existing analyze-by-parcel path
- one SITE truth / Rule Engine consumption architecture
- public historical non-exposure
- UQQ700 UNKNOWN/BLOCKED
- no invented architecture STEP number
