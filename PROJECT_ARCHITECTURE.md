# AI 대지분석 자동화 시스템 — PROJECT ARCHITECTURE

최종 reconciliation: 2026-09-16
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
- LLM 합의 ≠ source verification
- 조건 미충족 상태에서 수치 확정 금지

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
주소/지번
→ 법정동 identity
→ PNU
→ official land/building data
→ SITE identity
```

다른 PNU의 snapshot, geometry, evidence 재사용을 금지한다. API 오류와 규제 FALSE도 분리한다.

## 5. Runtime spatial SITE fact

Runtime spatial condition은 parcel geometry, target PNU, CRS, regulation geometry intersection을 검증한다. Spatial query 실패를 FALSE로 바꾸지 않으며 EPSG:4326 degree²를 법적 면적으로 사용하지 않는다.

Historical provenance는 이 spatial runtime channel과 별도로 유지한다.

## 6. Regulation resolution

표준 상태:
```text
TRUE / FALSE / UNKNOWN
```

주요 resolution family:
```text
SPATIAL_DATA_CONFIRMED
NOTICE_CONFIRMED
LEGAL_RULE_CALCULATED
HYBRID_SPATIAL_NOTICE
HISTORICAL_SITE_EVENT
EXTERNAL_AUTHORITY_REQUIRED
```

Profile metadata는 resolver execution, SITE truth, production registration, runtime registration 또는 Rule Engine input과 동일하지 않다.

## 7. Provenance-bound numbered chain

현재 validated architecture STEP chain:

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

STEP114는 candidate SITE decision eligibility이며 SITE truth가 아니다. STEP114 이후 구현된 경계에는 아직 새 STEP 번호를 부여하지 않는다.

## 8. Historical SITE applicability

```text
STEP114 verified candidate
+
canonical SITE identity / PNU
+
family-specific verified parcel applicability evidence
→ fail-closed SITE applicability admission
```

Historical parcel evidence는 event identity, official source verification, parcel binding verification, event binding verification을 요구한다.

Admission 규칙:
- canonical/target/evidence PNU 불일치 → 거부
- family evidence kind 불일치 → 거부
- unverified applicability → UNKNOWN/rejection
- admission 자체로 SITE truth mutation/promotion 금지
- admission 자체로 production/runtime registration 금지

## 9. Historical production safety gates

Historical path는 새 병렬 production path를 만들지 않고 기존 service/builder/Rule Engine 경로를 사용한다.

현재 validated 흐름:

```text
PNU-bound SITE applicability ADMITTED
+
typed trusted historical handoff AUTHORIZED
↓
actual Site object PNU rebinding
↓
candidate↔repair state consistency authorization
↓
candidate↔condition identity binding authorization
↓
admitted historical Rule Input adapter READY
↓
existing service
↓
existing builder
↓
historical registry / collision policy / live consumption authorization
↓
existing Rule Engine
```

### Actual SITE PNU rebinding
Applicability에서 검증한 canonical PNU와 이번 요청으로 실제 생성된 Site의 PNU가 정확히 같아야 한다. 다른 필지에서 만들어진 admission 재사용을 막는다.

### Candidate↔repair consistency
현재 STEP114 historical eligibility는 verified `FALSE` candidate만 eligible하다. Trusted repairs의 상태가 이 candidate와 모순되면 production forwarding을 차단한다. 이 경계는 상태 일치 검증이며 condition identity를 새로 정의하지 않는다.

### Candidate↔condition binding
Trusted repairs의 `condition` 이름을 검증하여 하나의 명확한 historical condition identity만 존재하도록 한다. 같은 condition이 여러 Rule 위치에서 반복되어 여러 repair가 존재하는 것은 허용하지만, 서로 다른 condition 이름이 섞이면 fail-closed다.

Condition identity는 새로 발명하지 않는다. 기존 upstream historical mutation/preview/execution chain과 trusted repair가 가진 condition identity를 보존한다.

### Adapter
위 gate들이 통과한 뒤에만 기존 historical Rule Engine input shape를 만든다. Candidate decision을 새 repair로 합성하지 않는다. 실제 repair의 source는 기존 trusted handoff다.

## 10. SITE truth와 production consumption의 분리

현재 historical path가 Rule Engine에서 trusted repair를 소비할 수 있다는 사실은 별도의 일반 SITE truth promotion 권한을 의미하지 않는다.

```text
verified candidate
≠ SITE truth

SITE applicability admitted
≠ SITE truth promotion

production forwarding authorized
≠ generic SITE truth mutation authority
```

따라서 향후 SITE truth/promotion authorization을 설계하더라도 기존 SITE registry/runtime architecture를 우회하는 두 번째 truth store/path를 만들지 않는다.

## 11. Public API / runtime exposure

현재 public FastAPI request에는 다음 historical 내부 입력을 노출하지 않는다:
- `historical_rule_input`
- `historical_handoff_authorization`
- `historical_site_applicability_admission`

Historical provenance는 spatial runtime condition channel에 등록되지 않는다. 현재 reconciliation은 public historical injection, historical spatial runtime registration, generic SITE truth promotion 권한을 부여하지 않는다.

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

## 13. Hybrid spatial/notice

HYBRID TRUE의 최소 원칙:

```text
OFFICIAL_DESIGNATION_IDENTITY_VERIFIED
+
CURRENT_VALIDITY_VERIFIED
+
SITE_SPATIAL_INCLUSION_VERIFIED
→ TRUE candidate
```

단순 검색 실패는 FALSE가 아니다.

### UQQ700 개발밀도관리구역
- family: `HYBRID_SPATIAL_NOTICE`
- standard code: `UQQ700`
- legal-source resolution: UNKNOWN
- negative evidence / legal absence inference disabled
- SITE TRUE/FALSE promotion blocked
- production/runtime registration blocked
- historical reconciliation은 UQQ700을 `HISTORICAL_SITE_EVENT`로 바꾸거나 활성화하지 않는다.

## 14. Legal knowledge / deterministic Rule Engine

법률→시행령→시행규칙→조례→고시→별표→지침의 delegation/version chain을 보존한다. 개정 전 원문과 effective/promulgation date를 유지하고 as-of analysis로 발전한다.

Condition family:
```text
SITE / PROJECT / PROCEDURE / AUTHORITY / TEMPORAL / SPATIAL
```

계산 가능한 결과는 Rule Engine이 결정한다. 조건이 확정되지 않으면 숫자를 임의 확정하지 않는다.

## 15. Provenance / verification

모든 중요한 결과는 역추적 가능해야 한다.

```text
Final result
→ Rule / resolution
→ official/legal source
→ version/event
→ canonical SITE/PNU binding where applicable
```

AI는 설명과 쟁점 발견을 담당하되 규제 TRUE/FALSE, PNU, 법적 source 또는 수치 상한을 임의 생성하지 않는다.

## 16. Test / error policy

Test categories:
```text
UNIT
BEHAVIORAL REGRESSION
INTEGRATION
END-TO-END
POLICY ASSERTION
```

오류/불확실성 상태를 분리한다:
```text
NOT_APPLICABLE
UNKNOWN
SOURCE_UNAVAILABLE
SOURCE_ERROR
UNVERIFIED
```

Fail-safe:
```text
잘못된 TRUE보다 UNKNOWN이 낫다.
잘못된 FALSE보다 UNKNOWN이 낫다.
```

## 17. Security / repository policy

- API keys in `.env`; secrets Git 저장 금지
- runtime raw/cache와 Git source 분리
- `law_data/output/*` 보호
- explicit WRITE approval before repository mutation
- user-local behavioral PASS is final validation

## 18. Numbering policy

Architecture STEP98…STEP114와 legal-source investigation S206…S216/future S217은 별개다. 서로 번호를 연결하거나 S217을 STEP115로 부르지 않는다.

새 architecture STEP은 repository design/documentation에서 명시적으로 확립할 때만 부여한다.

## 19. Current validated architecture position

User-local behavioral validation through HEAD `29967e6fbde26bb6d3839bc2202ad363fb41bdf5` establishes:

```text
verified historical FALSE candidate
→ verified parcel/PNU applicability
→ actual-SITE PNU rebinding
→ candidate/repair state consistency
→ candidate/condition identity binding
→ admitted existing historical Rule Input
→ existing builder / Rule Engine consumption
```

STEP74 E2E confirms the reconciled historical path while preserving:
- normal no-historical analysis
- no public API historical exposure
- no historical spatial runtime registration
- no real-condition activation implied by the test
- caller input immutability

## 20. Next design question

The next work is a READ-ONLY audit, not an assumed new STEP. Determine what evidence/authority would be required before any generic SITE truth/promotion authorization can be designed, while preserving the existing SITE registry/runtime architecture and avoiding a second truth path.
