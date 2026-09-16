# AI 대지분석 자동화 시스템 — PROJECT ARCHITECTURE

문서 목적
======================================================================

이 문서는 `PROJECT_STATUS.md`와 역할이 다르다.

- `PROJECT_STATUS.md`: 현재 개발/검증 상태와 다음 작업을 기록한다.
- `PROJECT_ARCHITECTURE.md`: 장기 layer, 책임, 데이터 흐름, 판정 원칙과 완료 기준을 정의한다.

최초 작성 기준일: 2026-08-26
최종 reconciliation: 2026-09-16
Architecture Baseline: v1.2


1. 프로젝트 최종 목표
======================================================================

사용자가 주소 또는 필지를 입력하면 시스템이 해당 SITE에 대해 공식 데이터와 법적 근거를 추적하여 다음을 자동 생성한다.

1. 정확한 필지 identity
2. 토지/건축물 현황
3. 적용되는 용도지역·지구·구역 및 기타 규제
4. 각 규제의 TRUE / FALSE / UNKNOWN
5. 각 판정의 공식 출처와 provenance
6. 적용 법률·시행령·시행규칙·조례·고시·별표
7. 건폐율·용적률·높이·주차·이격·조경 등 계산 가능한 규제값
8. 조건부 규제 및 추가 입력이 필요한 PROJECT 조건
9. 규제 간 충돌, 중첩, 우선순위
10. AI가 설명한 최종 대지분석 보고서
11. 모든 결과의 citation / reverse verification

핵심 질문:

> 이 필지에는 정확히 어떤 규제가 적용되고, 그 사실은 어느 공식 데이터·공간정보·지정고시·법령에서 확정되며, 따라서 무엇을 얼마나 지을 수 있는가?


2. 최상위 설계 철학
======================================================================

```text
OFFICIAL FACT
→ SITE FACT
→ REGULATION RESOLUTION
→ LEGAL RULE
→ DETERMINISTIC ENGINE
→ AI ANALYSIS
→ VERIFICATION
```

핵심 원칙:
- 검색 결과 ≠ 법적 사실
- 문서 발견 ≠ 규제 TRUE
- endpoint 발견 ≠ 문서 검증
- 고시 발견 ≠ 현재 유효
- 지역명 일치 ≠ 권한 있는 발행기관
- point 포함 ≠ parcel 포함
- source 미발견 ≠ FALSE
- 조건 미충족 상태에서 수치 확정 금지
- LLM 합의 ≠ source verification
- resolver result ≠ parcel applicability
- SITE-decision eligibility ≠ SITE truth
- admission ≠ production/runtime registration authority


3. 전체 시스템 아키텍처
======================================================================

```text
LAYER 0  USER / PROJECT INPUT
    ↓
LAYER 1  PARCEL IDENTITY & OFFICIAL LAND DATA
    ↓
LAYER 2  SITE FACT MODEL
    ↓
LAYER 3  REGULATION RESOLUTION
    ↓
LAYER 4  LEGAL KNOWLEDGE
    ↓
LAYER 5  RULE NORMALIZATION
    ↓
LAYER 6  DETERMINISTIC EVALUATION
    ↓
LAYER 7  RETRIEVAL & LEGAL CONTEXT
    ↓
LAYER 8  AI ANALYSIS
    ↓
LAYER 9  VERIFICATION & PROVENANCE
    ↓
LAYER 10 PRODUCT / API / REPORT
```


4. SITE / PROJECT INPUT BOUNDARY
======================================================================

```text
SITE CONDITION != PROJECT CONDITION
```

SITE identity는 주소/PNU/지번 등 현재 필지 사실을 나타낸다. PROJECT input은 용도, 규모, 층수, 세대수, 인센티브 선택 등 사용자의 계획조건이다. SITE에 존재하지 않는 PROJECT 조건을 자동 TRUE 처리하지 않는다.


5. PARCEL IDENTITY & OFFICIAL LAND DATA
======================================================================

모든 후속 판정이 동일한 실제 필지를 바라보도록 canonical parcel identity를 확정한다.

```text
주소
→ 법정동 identity
→ PNU
→ official land/building data
→ SITE identity
```

필수 불변조건:
- 다른 PNU의 snapshot/geometry/evidence 재사용 금지
- upstream API 오류와 규제 FALSE 분리
- raw API data와 normalized SITE data 분리
- API key source code 저장 금지

현재 기반은 Building HUB, VWorld, Site/Building model, FastAPI service orchestration이다.


6. SITE FACT / RUNTIME SPATIAL MODEL
======================================================================

공식 source를 downstream Rule Engine이 사용할 수 있는 일관된 SITE FACT로 변환한다.

Runtime Spatial Condition 원칙:
- POINT 단독 TRUE 확정 금지
- Parcel Polygon / MultiPolygon 확보
- target PNU 직접 검증
- CRS 확인
- parcel geometry와 regulation geometry intersection 검증
- spatial query 실패와 FALSE 분리
- EPSG:4326 degree²를 법적 면적으로 사용 금지

Historical provenance는 이 spatial runtime channel과 별도로 유지한다.


7. REGULATION RESOLUTION
======================================================================

표준 결과:

```text
TRUE
FALSE
UNKNOWN
```

UNKNOWN은 정식 상태다.

현재 resolution family/type에는 다음이 포함된다.

```text
SPATIAL_DATA_CONFIRMED
NOTICE_CONFIRMED
LEGAL_RULE_CALCULATED
HYBRID_SPATIAL_NOTICE
HISTORICAL_SITE_EVENT
EXTERNAL_AUTHORITY_REQUIRED
```

예:
- UQQ700 개발밀도관리구역 → `HYBRID_SPATIAL_NOTICE`
- historical SITE condition → `HISTORICAL_SITE_EVENT`

Profile metadata는 resolver execution, SITE state, production registration, runtime registration, Rule Engine input과 동일하지 않다.


8. PROVENANCE-BOUND RESOLUTION PIPELINE
======================================================================

현재 locally validated numbered chain:

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

STEP114는 candidate SITE decision의 eligibility 경계이며 SITE truth가 아니다.

STEP114 이후 현재 구현·검증된 기능 경계에는 아직 새 STEP 번호를 부여하지 않는다.

```text
STEP114 verified candidate
+
canonical SITE identity / PNU
+
family-specific parcel applicability evidence
↓
fail-closed SITE applicability admission
↓
admitted historical Rule Input adapter
↓
existing production consumption architecture
```


9. SITE APPLICABILITY ADMISSION
======================================================================

SITE applicability admission은 resolver verification과 분리된 fail-closed boundary다.

```text
verified candidate SITE decision
+
canonical SITE identity / PNU
+
verified parcel applicability
→ SITE applicability admission
```

필수 불변조건:
- candidate decision은 현재 canonical SITE/PNU와 명시적으로 결합한다.
- target/evidence PNU가 canonical PNU와 다르면 거부한다.
- family-specific evidence kind가 resolver family와 맞아야 한다.
- parcel applicability가 검증되지 않으면 UNKNOWN 또는 rejection을 유지한다.
- admission 자체로 SITE truth mutation/promotion을 허용하지 않는다.
- admission 자체로 production/runtime registration을 허용하지 않는다.
- 두 번째 SITE truth path를 만들지 않는다.

`HISTORICAL_SITE_EVENT`에는 historical parcel event binding evidence contract가 구현되어 있으며 event identity, official source verification, parcel binding verification, event binding verification을 별도 gate로 요구한다.


10. HISTORICAL PRODUCTION CONSUMPTION BOUNDARY
======================================================================

Historical production path는 기존 service/builder/Rule Engine 경로를 유지한다. 새 병렬 production path를 만들지 않는다.

현재 흐름:

```text
PNU-bound SITE applicability ADMITTED
+
typed trusted historical handoff authorized
↓
admitted historical Rule Input adapter READY
↓
orchestrator
↓
service
↓
builder
↓
historical registry/collision/live authorization
↓
Rule Engine
```

Fail-closed 규칙:
- handoff만 존재 → 차단
- applicability만 존재 → 차단
- UNKNOWN/unverified applicability → 차단
- unauthorized/forged handoff → 차단
- raw `historical_rule_input` orchestrator 직접 주입 → 제거/차단

일반 분석은 두 historical typed input이 모두 없으면 기존 경로를 유지한다.

이 production wiring은 candidate decision 자체를 repair로 합성하지 않는다. 기존 trusted handoff의 authorized repairs가 실제 Rule Engine input의 source이고, PNU applicability는 그 input을 내보내기 위한 선행 admission gate다.


11. PUBLIC API / RUNTIME EXPOSURE BOUNDARY
======================================================================

현재 public FastAPI request는 historical raw/typed inputs를 노출하지 않는다.

Public API에 없는 내부 필드:
- `historical_rule_input`
- `historical_handoff_authorization`
- `historical_site_applicability_admission`

Historical provenance는 spatial runtime condition channel에 등록되지 않는다.

따라서 현재 reconciliation은:
- public API historical injection을 허용하지 않는다.
- historical spatial runtime registration을 허용하지 않는다.
- SITE truth promotion 권한을 새로 부여하지 않는다.


12. COMPETENT AUTHORITY & SOURCE SCOPE
======================================================================

공식처럼 보이는 host만으로 competent authority가 되지 않는다.

```text
OFFICIAL HOST
→ REGION BINDING
→ SOURCE ROLE
→ LEGAL AUTHORITY SCOPE
→ TARGET REGULATION COMPATIBILITY
```

`AuthoritySourceScope`는 registry 이전 qualification contract다. descriptive metadata 존재만으로 verification flag를 올리지 않는다.

Verified authority/source registry는 verified mapping과 provenance가 실제로 준비된 경우에만 도입한다.


13. HISTORICAL NOTICE / DOCUMENT / VALIDITY
======================================================================

Historical discovery 안전 원칙:
- endpoint 발견 ≠ target document 발견
- query ≠ candidate evidence
- search title ≠ document verification
- official history source의 negative만으로 FALSE 금지
- candidate universe completeness가 없는 exhaustive disproof 금지
- discovery 실패 → UNKNOWN

Historical event validity는 designation/change/release/cancellation/supersession timeline과 source provenance를 보존해야 한다.


14. SPATIAL SCOPE VERIFICATION
======================================================================

HYBRID spatial/notice TRUE는 최소 다음을 요구한다.

```text
OFFICIAL_DESIGNATION_IDENTITY_VERIFIED
+
DESIGNATION_VALIDITY_VERIFIED
+
SITE_SPATIAL_INCLUSION_VERIFIED
→ TRUE
```

단순 검색 실패는 FALSE가 아니다.


15. LEGAL KNOWLEDGE / VERSIONING
======================================================================

법률 → 시행령 → 시행규칙 → 조례 → 고시 → 별표 → 지침의 delegation/version chain을 구조화한다.

- 개정 전 원문 삭제 금지
- effective/promulgation date 보존
- superseded history 유지
- as-of-date 분석 가능 구조로 발전


16. RULE NORMALIZATION & DETERMINISTIC ENGINE
======================================================================

법령 원문을 predicate/condition/effect/numeric/source 구조로 변환한다.

Condition family:

```text
SITE
PROJECT
PROCEDURE
AUTHORITY
TEMPORAL
SPATIAL
```

계산 가능한 결과는 AI가 아니라 Rule Engine이 계산한다. 조건이 확정되지 않았을 때 숫자를 임의 결정하지 않는다.

Rule 상태:

```text
APPLICABLE
NOT_APPLICABLE
CONDITIONAL
UNKNOWN
```


17. RULE CONFLICT / PRIORITY
======================================================================

상위법/하위법, 일반/특별규정, 완화, 중복 인센티브, 누적 상한, 적용시점 차이를 별도 conflict/priority layer로 강화한다. 최종 숫자뿐 아니라 계산 trace를 보존한다.


18. HYBRID RETRIEVAL / AI / VERIFICATION
======================================================================

권장 retrieval:

```text
Rule Matching + BM25 + Vector + Parent-Child + Delegation + Reranker
```

AI는 쟁점 발견, 법적 맥락 설명, 조건부 결과 설명, 추가 확인사항과 대안 설명을 담당한다. AI가 규제 TRUE/FALSE, PNU, 조문/고시, 수치 상한을 임의 생성하지 않는다.

AI 출력 후 조문, 시행일, 고시번호, 수치, SITE FACT, 규제 상태를 reverse verification한다.


19. PROVENANCE MODEL
======================================================================

모든 중요한 결과는 source까지 역추적 가능해야 한다.

```text
Final result
→ Rule / resolution
→ legal or official source
→ version/event
→ canonical SITE/PNU binding where applicable
```


20. PRODUCT / API
======================================================================

최종 후보 기능:
- 단일/다중 필지 분석
- 지도 overlay
- 법령 질의
- 개발가능규모/인센티브 분석
- 규제 변경이력/as-of analysis
- PDF 보고서
- API/batch analysis

현재 FastAPI는 product layer 기반으로 유지한다.


21. DATA / TEST / ERROR POLICY
======================================================================

Git repository와 runtime raw/cache를 분리한다.

Test categories:
- UNIT
- BEHAVIORAL REGRESSION
- INTEGRATION
- END-TO-END
- POLICY ASSERTION

`all_pass=True`는 실제 법적 정확성과 동일하지 않다.

오류 상태를 분리한다.

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


22. SECURITY / OPERATION / SCALE
======================================================================

- API key `.env`
- secret Git 저장 금지
- timeout / bounded retry / response-size limit
- logging secret 제거
- source rate limit 고려
- 전국화 시 source/law/spatial cache, scheduler, document index, incremental refresh 사용

전국화는 SITE별 무한 crawling이 아니라 source registry/document index 기반 lookup으로 발전한다.


23. NATIONWIDE REGISTRY STRATEGY
======================================================================

필요 registry 후보:

```text
MUNICIPALITY_REGISTRY
OFFICIAL_SOURCE_REGISTRY
SOURCE_AUTHORITY_REGISTRY
SPATIAL_DATASET_REGISTRY
REGULATION_RESOLUTION_REGISTRY
LEGAL_SOURCE_REGISTRY
```

지자체별 차이는 adapter/config로 흡수한다. Registry 존재 자체를 verification evidence로 사용하지 않는다.


24. MASTER ROADMAP
======================================================================

```text
PHASE 0   Foundation                    COMPLETE
PHASE 1   Building/SITE                 COMPLETE
PHASE 2   Land/Spatial                  CORE COMPLETE
PHASE 3   SITE Analysis                 CORE COMPLETE
PHASE 4   Legal ingestion               IN PROGRESS
PHASE 5   Rule Engine                   IN PROGRESS / CORE STABLE
PHASE 6   Runtime spatial               CORE STABLE
PHASE 7   Regulation Resolution         ACTIVE / PROFILE + RESOLVER CONTRACTS ADVANCED
PHASE 8   Authority/Historical          CORE INFRASTRUCTURE RECONCILED / EVIDENCE-DRIVEN EXTENSIONS DEFERRED
PHASE 9   Nationwide Regulation Registry ACTIVE / PNU-BOUND HISTORICAL ADMISSION + EXISTING PRODUCTION WIRING VALIDATED
PHASE 10  Legal Knowledge Graph         FUTURE
PHASE 11  Numeric/Design Engine         FUTURE EXPANSION
PHASE 12  Hybrid Retrieval              FUTURE
PHASE 13  AI Analysis                   FUTURE
PHASE 14  Citation Verification         FUTURE
PHASE 15  Productization                FUTURE
PHASE 16  Multi-Parcel                  FUTURE
PHASE 17  Historical/As-of              FUTURE
PHASE 18  Scale/Operations              FUTURE
PHASE 19  Production Quality            FUTURE
```


25. CURRENT ARCHITECTURE CHECKPOINT
======================================================================

2026-09-16 user-local behavioral validation 기준:

```text
STEP98
→ STEP101
→ STEP103
→ STEP104
→ STEP106
→ STEP108
→ STEP110
→ STEP112
→ STEP114
→ historical parcel applicability evidence
→ PNU-bound SITE applicability admission
→ admitted historical Rule Input adapter
→ typed trusted handoff + applicability orchestrator gate
→ existing service / builder / Rule Engine path
```

STEP114 이후 기능 경계에는 새 STEP 번호를 아직 부여하지 않는다.

Current safety conclusion:
- STEP114 candidate ≠ SITE truth
- PNU admission requires exact canonical parcel binding
- unverified applicability remains UNKNOWN/rejected
- historical production path requires applicability + trusted handoff
- raw historical orchestrator injection removed
- public API historical exposure NOT AUTHORIZED
- historical spatial runtime registration NONE
- SITE truth mutation/promotion not authorized by these contracts
- second SITE truth/production path not created

Locally reconciled historical regressions:
- STEP67 production runtime exposure PASS
- STEP68 orchestrator exposure PASS
- STEP69 public API exposure PASS
- STEP73 production wiring PASS
- STEP74 end-to-end PASS


26. UQQ700 / REAL-CONDITION LOCKS
======================================================================

개발밀도관리구역:
- standard code `UQQ700`
- family `HYBRID_SPATIAL_NOTICE`
- current legal-source resolution UNKNOWN
- negative evidence / legal absence inference disabled
- minimum gate: official designation identity + current validity + SITE spatial inclusion
- SITE TRUE/FALSE promotion blocked
- production/runtime registration blocked

Current historical-family production reconciliation does not activate UQQ700 and does not change its family.

Unresolved historical real conditions likewise remain evidence-driven and fail-closed.

Legal-source investigation numbering (`S206`…`S216`/future S217) is independent from architecture STEP numbering.


27. ARCHITECTURE DECISION PRINCIPLES
======================================================================

새 기능 추가 전 확인:
1. SITE FACT인가 PROJECT INPUT인가?
2. official source가 있는가?
3. TRUE/FALSE를 deterministic하게 결정할 수 있는가?
4. 미확정이면 UNKNOWN을 유지하는가?
5. resolution family/type은 무엇인가?
6. competent authority는 누구인가?
7. spatial/historical verification이 필요한가?
8. canonical PNU binding이 필요한가?
9. AI가 아니라 Rule Engine에서 처리 가능한가?
10. provenance를 끝까지 추적 가능한가?
11. regression fixture를 만들 수 있는가?
12. 전국화 가능한 registry/adapter 구조인가?
13. 기존 SITE truth/production path에 합류하는가, 아니면 잘못된 병렬 path를 만드는가?


28. PROJECT SUCCESS CRITERIA
======================================================================

```text
INPUT SITE
→ 확정된 parcel identity
→ 공식 SITE facts
→ 규제별 TRUE / FALSE / UNKNOWN
→ 공식 designation / spatial / legal provenance
→ 결정론적 법규 계산
→ AI 설명
→ reverse verification
```

최종 사용자에게는 단순한 결과를 보여주되 내부 판단은 source와 parcel identity까지 역추적 가능해야 한다.


29. ARCHITECTURE CHANGE LOG
======================================================================

### v1.2 SITE applicability / production wiring reconciliation — 2026-09-16

반영 내용:
- STEP114 이후 historical parcel applicability evidence contract 반영
- canonical PNU-bound SITE applicability admission 반영
- cross-PNU / unbound evidence fail-closed 원칙을 실제 구현 상태와 정합화
- admitted historical Rule Input adapter 반영
- typed trusted handoff + applicability orchestrator gate 반영
- 기존 service/builder/Rule Engine production path 재사용 명시
- raw historical Rule Input orchestrator 직접 주입 제거 반영
- STEP67/68/69/73/74 locally validated regression reconciliation 반영
- public API historical exposure / spatial runtime registration 차단 유지
- 새 STEP 번호를 임의 부여하지 않음

Behavior 영향:
- historical production admission은 이전 handoff-only 경계보다 엄격해져 PNU-bound applicability admission을 추가 요구한다.
- 일반 non-historical 분석 경로는 유지된다.
- SITE truth mutation/promotion authority는 부여하지 않는다.
- UQQ700 UNKNOWN/BLOCKED 정책은 변경하지 않는다.

### v1.2 STEP114 reconciliation — 2026-09-16

- STEP98→STEP114 provenance/profile/resolver chain 반영
- resolver result와 parcel applicability 분리
- SITE-decision eligibility와 SITE truth 분리
- canonical SITE/PNU binding을 후속 admission 필수조건으로 명시
- 두 번째 독립 SITE truth path 생성 금지

### v1.2 — 2026-09-10

- `RegulationResolutionProfile` metadata boundary 반영
- `AuthoritySourceScope` qualification boundary 반영
- verified authority/source mapping 전 registry 승격 금지

### v1.1 — 2026-09-09

- `HISTORICAL_SITE_EVENT` family 반영
- historical event identity / SITE applicability / temporal relation / history completeness 책임 분리
- search no-hit를 FALSE로 승격하지 않는 exhaustive-disproof 원칙 명시

### v1.0 — 2026-08-26

초기 master architecture baseline.

다음 architecture review trigger:
- SITE truth/promotion authorization 설계 시
- verified authority/source registry 설계 시
- UQQ700 최종 resolution 완료 시
- nationwide registry의 실제 condition 확장 시
- Hybrid Retrieval / AI 단계 진입 시
