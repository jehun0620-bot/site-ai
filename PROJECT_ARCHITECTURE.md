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
- 조건 미충족 상태에서 수치 확정 금지
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

Public API / Building HUB의 대장구분과 PNU의 필지구분은 서로 다른 코드 체계이므로 명시적으로 변환한다.

```text
Public API / Building HUB plat_gb_cd=0 (일반) → PNU land-register digit 1
Public API / Building HUB plat_gb_cd=1 (산)   → PNU land-register digit 2
```

Building HUB가 정상 status `00`이지만 건축물 0건을 반환해도 canonical parcel identity가 유효하면 parcel-only Site를 구성할 수 있다. 이 경로는 건축물 존재 여부를 필지 존재 여부와 동일시하지 않는다.

Parcel-only enrichment는 현재 canonical PNU와 정확히 같은 공식 토지특성 record에만 의존한다. 동일-PNU VWorld Land Characteristics에서 지목, 용도지역, 공식 토지면적, 지번주소를 보강할 수 있지만 다른 PNU의 persisted snapshot/identity fallback은 사용할 수 없다.

## 5. Runtime spatial SITE fact

Runtime spatial condition은 parcel geometry, target PNU, CRS, regulation geometry intersection을 검증한다. Spatial query 실패를 FALSE로 바꾸지 않는다. Historical provenance는 spatial runtime condition channel과 별도로 유지한다.

Parcel-only 경로에서는 동일-PNU 공식 지번주소가 확보되면 기존 address search를 통해 좌표를 구하고, VWorld parcel dataset의 live polygon feature PNU가 requested canonical PNU와 정확히 일치할 때만 `PNU_POLYGON_VERIFIED` geometry로 채택한다.

EPSG:4326 live geometry는 공간 판정용으로 유지하며 면적을 임의 계산하지 않는다. 공식 토지면적은 VWorld Land Characteristics의 `lndpclAr`을 별도 `square_meter` 값으로 보존하고 현재 land-area 결과에서 primary official value로 사용한다.

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

## 7. Historical SITE applicability / forwarding

```text
STEP114 verified candidate
+ canonical SITE/PNU
+ family-specific verified parcel applicability evidence
→ fail-closed SITE applicability admission
→ actual Site PNU rebinding
→ candidate↔repair state consistency
→ candidate↔condition identity binding
→ admitted historical Rule Input adapter
```

Admission이나 forwarding gate 자체는 SITE truth mutation/promotion 권한이 아니다. Candidate decision을 새 repair로 합성하지 않고 trusted handoff의 condition/state/source를 보존한다.

## 8. Historical SITE-truth promotion boundaries

Promotion은 기존 production truth/Rule Engine architecture를 우회하는 별도 store/path가 아니다.

```text
applicability + trusted candidate/repair/condition
→ pre-promotion same-fact binding authorization
→ current canonical PNU binding authorization
→ final non-executing promotion authorization
→ isolated promotion executor
→ promotion Rule Input bridge
```

각 경계의 역할:
- same-fact binding: applicability, candidate state, trusted condition, historical mutation execution이 같은 사실을 가리키는지 검증
- PNU binding: 현재 canonical PNU와 promotion 대상 PNU를 명시적으로 결합
- final authorization: authorized repairs가 bound condition/state/provenance와 일치하는지 검증하되 mutation을 실행하지 않음
- isolated executor: 승인된 promoted SITE condition snapshot을 만들지만 global registry/Rule Engine/runtime/API를 직접 변경하지 않음
- promotion bridge: executor 결과의 type/state/confidence/source/PNU 정합성을 검증하고 기존 historical Rule Input shape로 변환

## 9. Verified historical Rule Input envelope

Production Orchestrator는 legacy typed historical path 또는 promotion bridge path의 검증을 끝낸 뒤 실제 Site PNU를 다시 확인한다. 통과한 historical Rule Input만 `HistoricalVerifiedRuleInputEnvelope`로 봉인한다.

```text
Orchestrator verified historical input
+ actual canonical Site PNU
→ verified envelope
→ service envelope check
→ builder envelope + current site_input PNU recheck
→ historical registry adapter
→ spatial/historical collision policy
→ merged-registry live-consumption authorization
→ existing Rule Engine
```

Service와 Builder의 raw historical dict 직접 주입은 fail-closed다. Builder는 envelope canonical PNU와 현재 `site_input` PNU가 정확히 같아야 historical consumption을 진행한다.

Envelope는 새로운 truth decision이나 새로운 Rule Engine이 아니다. 이미 검증된 input과 canonical PNU를 함께 운반하는 production boundary다.

## 10. Single production consumption lane

Historical path는 새 병렬 Rule Engine을 만들지 않는다. 최종 소비는 기존 builder의 단일 경로다.

```text
spatial SITE registry
+
verified historical registry
→ collision policy
→ live-consumption authorization
→ existing evaluate_site_rules / Rule Engine
```

Repository-wide local grep at the previously validated production reconciliation point found no production raw-historical bypass caller. 남은 raw 직접 호출은 fail-closed 회귀 테스트 또는 isolated adapter/bridge 테스트다.

## 11. Public API / runtime exposure

현재 public FastAPI request에는 historical 내부 입력을 노출하지 않는다. Historical provenance는 spatial runtime condition channel에 등록하지 않는다. Promotion/envelope reconciliation도 public historical injection 권한이나 historical spatial runtime registration 권한을 부여하지 않는다.

현재 public parcel request는 `sigungu_cd / bjdong_cd / plat_gb_cd / bun / ji`를 직접 입력받아 canonical parcel identity를 구성한다. Ordinary와 mountain 두 public HTTP 경로가 실제 E2E 검증됐다.

다음 product-facing gap은 사용자가 위 필지 코드를 미리 알지 못해도 **주소 입력 → 검증된 canonical parcel identity/PNU → 기존 분석 pipeline**으로 진입할 수 있는 public input boundary다. 이 gap은 아직 구현되었다고 간주하지 않으며, 주소 해석 결과가 여러 필지이거나 불확실한 경우 임의 PNU를 선택해서는 안 된다.

## 12. Authority / historical evidence

Official-looking host만으로 competent authority가 되지 않는다.

```text
OFFICIAL HOST
→ REGION BINDING
→ SOURCE ROLE
→ LEGAL AUTHORITY SCOPE
→ TARGET REGULATION COMPATIBILITY
```

Historical discovery에서도 endpoint 발견, query 결과, search title, source 미발견만으로 target document verification 또는 FALSE를 만들지 않는다. Designation/change/release/cancellation/supersession timeline과 provenance를 보존한다.

## 13. Hybrid spatial/notice / UQQ700

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
- historical reconciliation은 UQQ700을 `HISTORICAL_SITE_EVENT`로 바꾸거나 활성화하지 않는다.

## 14. Legal knowledge / deterministic Rule Engine

법률→시행령→시행규칙→조례→고시→별표→지침의 delegation/version chain을 보존한다. Condition family는 SITE / PROJECT / PROCEDURE / AUTHORITY / TEMPORAL / SPATIAL로 분리한다. 계산 가능한 결과는 Rule Engine이 결정하고 조건이 확정되지 않으면 숫자를 임의 확정하지 않는다.

## 15. Provenance / verification

모든 중요한 결과는 다음처럼 역추적 가능해야 한다.

```text
Final result
→ Rule / resolution
→ official/legal source
→ version/event
→ canonical SITE/PNU binding where applicable
```

AI는 설명과 쟁점 발견을 담당하되 규제 TRUE/FALSE, PNU, 법적 source 또는 수치 상한을 임의 생성하지 않는다.

## 16. Test / fail-safe policy

Test categories: UNIT / BEHAVIORAL REGRESSION / INTEGRATION / END-TO-END / POLICY ASSERTION.

불확실성은 NOT_APPLICABLE / UNKNOWN / SOURCE_UNAVAILABLE / SOURCE_ERROR / UNVERIFIED로 구분한다.

```text
잘못된 TRUE보다 UNKNOWN이 낫다.
잘못된 FALSE보다 UNKNOWN이 낫다.
```

Behavioral PASS HEAD `e29d676b84f99cc220c52a18196af575631d60b3` includes the parcel-register identity contracts, parcel-only Site and Land/address enrichment contracts, cross-PNU identity guard, public API parcel identity contract, district-unit E2E regression, historical E2E regression, plus the previously validated promotion/verified-envelope production contracts.

Real-data validation additionally confirmed the mountain parcel-only path through official land data, address coordinate recovery, live parcel polygon exact-PNU verification, and Public FastAPI HTTP E2E. Ordinary Public FastAPI HTTP E2E was also validated without regressing the existing Building HUB path.

## 17. Security / repository policy

- API keys in `.env`; secrets Git 저장 금지
- runtime raw/cache와 Git source 분리
- `law_data/output/*` 보호
- explicit WRITE approval before repository mutation
- user-local behavioral PASS is final validation

## 18. Numbering policy

Architecture STEP98…STEP114와 legal-source investigation S206…S216/future S217은 별개다. 서로 번호를 연결하거나 S217을 STEP115로 부르지 않는다. 새 architecture STEP은 repository design/documentation에서 명시적으로 확립할 때만 부여한다.

## 19. Current validated architecture position

Behavioral PASS HEAD `e29d676b84f99cc220c52a18196af575631d60b3` establishes the current code/test validation point; documentation-only commits after that point do not replace it as the behavioral PASS HEAD.

Validated production architecture includes:

```text
canonical parcel identity
→ ordinary Building HUB path OR parcel-only zero-building path
→ same-PNU official land enrichment
→ canonical SITE identity
→ same-PNU spatial recovery / exact-PNU polygon verification where available
→ regulation resolution / deterministic evaluation

verified historical candidate
→ verified parcel/PNU applicability
→ actual-SITE PNU rebinding
→ candidate/repair state consistency
→ candidate/condition identity binding
→ promotion binding/authorization/execution/bridge where explicitly authorized
→ production Orchestrator PNU recheck
→ verified envelope
→ Service / Builder PNU recheck
→ existing collision/live-consumption authorization
→ existing Rule Engine
```

This preserves normal no-historical analysis, caller input immutability, no public historical API exposure, no historical spatial-runtime registration, no cross-PNU identity reuse, and no second Rule Engine/SITE truth path.

## 19A. District-unit / common verified production lane

District-unit production transport remains validated through the existing Rule Engine architecture.

```text
verified historical transport
→ historical collision / live authorization
→ common verified SITE registry
→ existing Rule Engine

verified district-unit transport
→ district spatial collision / live authorization
→ common verified SITE registry
→ existing Rule Engine
```

District-unit canonical PNU remains first-class through the verified transport boundaries and is not inferred from the final merged registry.

District spatial collision is evaluated in Builder because Builder owns the current spatial SITE registry.

Historical and district-unit production inputs are not implicitly merged. Without an explicit cross-family merge policy, simultaneous input fails closed.

This reconciliation creates no new architecture STEP number, does not change generic STEP112/STEP114 semantics, and does not authorize UQQ700.

## 20. Next design question

Parcel-register identity and parcel-only production support are now reconciled with the existing architecture without a new STEP number.

The next product-facing design question is:

```text
USER ADDRESS
→ authoritative/unambiguous parcel identity resolution
→ canonical PNU
→ existing analyze_site_by_parcel pipeline
```

Before implementation, perform a READ-ONLY audit of available address/parcel resolution providers and existing repository helpers. Preserve these boundaries:
- do not guess a PNU from ambiguous address results
- do not reuse identity evidence across PNU
- preserve ordinary/mountain register distinction
- keep the existing canonical PNU builder as the parcel identity authority after component resolution
- one SITE truth / Rule Engine consumption architecture
- verified-envelope fail-closed behavior
- public API historical non-exposure
- spatial/historical separation
- UQQ700 UNKNOWN/BLOCKED policy
- no invented architecture STEP number
