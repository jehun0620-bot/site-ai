# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-09-05

> 현재 개발 상태와 안전 불변조건을 기록한다. 장기 로드맵은 `PROJECT_ARCHITECTURE.md` 기준.

## 1. 현재 단계

```text
STEP 17
Target: 개발밀도관리구역
Standard code: UQQ700
Resolution type: HYBRID_SPATIAL_NOTICE
Latest validated stage: S206
Current resolution: UNKNOWN
Next stage: S207 NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY contract forensic
```

```text
SITE TRUE                BLOCKED
SITE FALSE               BLOCKED
negative evidence        DISABLED
legal absence inference  DISABLED
runtime registration     BLOCKED
```

## 2. Architecture 상태

```text
PHASE 0 Foundation              COMPLETE
PHASE 1 Building/SITE           COMPLETE
PHASE 2 Land/Spatial            CORE COMPLETE
PHASE 3 SITE Analysis           CORE COMPLETE
PHASE 4 Legal ingestion         IN PROGRESS
PHASE 5 Rule Engine             CORE STABLE / IN PROGRESS
PHASE 6 Runtime spatial         CORE STABLE
PHASE 7 Regulation Resolution   ACTIVE
PHASE 8 Authority/Historical    ACTIVE
PHASE 9+ Nationwide/AI/Product  FUTURE
```

개발 순서:
`OFFICIAL FACT → SITE FACT → REGULATION RESOLUTION → LEGAL RULE → DETERMINISTIC ENGINE → AI ANALYSIS → VERIFICATION`

## 3. 안정화된 runtime spatial

```text
지구단위계획 LT_C_UPISUQ161 PASS
개발진흥지구 LT_C_UQ129     PASS
취락지구     LT_C_UQ128     PASS
방재지구     LT_C_UQ125     PASS
```

UQQ700은 official designation identity + current validity + SITE spatial inclusion 검증 전 registry 등록 금지.

## 4. UQQ700 evidence chain / 불변조건

```text
COMPETENT AUTHORITY
→ OFFICIAL SOURCE
→ DESIGNATION DOCUMENT IDENTITY
→ CURRENT VALIDITY
→ SITE SPATIAL INCLUSION
→ TRUE / FALSE / UNKNOWN
```

```text
검색 결과 ≠ 법적 사실
document 발견 ≠ current validity
query failure ≠ FALSE
source 미발견 ≠ FALSE
technical unresolved ≠ FALSE
historical no-hit ≠ legal absence
```

현재 `negative_evidence_allowed=False`, verified positive/negative 모두 False, UQQ700 UNKNOWN.

## 5. CLOSED source families / DO NOT REPEAT

```text
CLOSED Seongnam Dynamic HWP Gazette — S72
CLOSED Seongnam POST-HWP5 Gazette — S133
CLOSED Seongnam PRE-HWP5 Gazette — S140 (47 HWP3 technical UNKNOWN)
CLOSED Seongnam /pm010301 Official Notice
CLOSED Seongnam EMINWON — S157
CLOSED EUM qualified metadata/detail HTML; live attachment technical UNKNOWN — S188
CLOSED National Archives of Korea — S205
```

Dynamic HWP: 1338 rows, processed 1328, quarantined 10, candidate 0. `S49` 재실행 금지.

EUM: Seongnam metadata 3409 rows/73 pages, title candidate 0, detail HTML 3409/3409 candidate 0. 현재 live surface는 access guard이므로 반복 probing 금지.

National Archives S205:
```text
qualified GET/POST search + result identity + org filter positive controls
S204 Seongnam organization-filtered bounded UQQ700 request_count 8
candidate 0 / technical unknown 0
operationally CLOSED
legal absence NOT established
```

## 6. S206 next official source-family discovery — PASS

S206 entry-surface discovery 결과:

```text
seed_count: 3
http_200_count: 3
technical_unknown_count: 0
ranked_family_order:
  1 NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY
  2 E_GAZETTE
  3 GYEONGGI_OFFICIAL_RECORD
next_family_for_contract_qualification:
  NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY
semantic:
  NEXT_OFFICIAL_HISTORICAL_SOURCE_FAMILY_ENTRY_SURFACES_DISCOVERED
```

Observed:
- 국가법령정보센터 `/ordinSc.do`: 자치법규/연혁/고시 관련 entry surface, forms 12, endpoint hints 11.
- 경기도 공식 홈페이지: official board endpoint hints 존재. 초기 decoder가 title/token을 mojibake 처리했으므로 향후 해당 family 진입 시 encoding부터 재qualification.
- 전자관보: HTTP 200 entry page이나 thin shell(280 bytes); 별도 application/search contract discovery 필요.

S206는 discovery only이며 어떤 source도 아직 qualified search surface로 승격하지 않는다.

## 7. S207 현재 작업

`NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY`를 먼저 contract-forensic한다.

목표:
1. 국가법령정보센터 자치법규 검색 form/action/method/control 복원.
2. 연혁/현행/폐지 및 detail/navigation endpoint 단서 확보.
3. 아직 검색 실행/absence inference를 하지 않는다.
4. 다음 단계에서 성남시 도시계획 조례 positive control을 먼저 qualification한다.
5. 이후 개발밀도관리구역 용어가 조례 연혁에서 관측되는 시점/법적 근거를 역추적하여 notice-number reverse discovery의 anchor로 사용한다.

Candidate가 나오더라도 조례 문구 자체를 UQQ700 지정 사실로 취급하지 않는다.

## 8. UQQ700 이후 남은 개발 단계

A. UQQ700 legal identity resolution — ACTIVE/최우선
```text
historical designation notice identity
competent authority / effective date
amendment/release history
current validity
spatial scope / parcel relationship
```

B. UQQ700 runtime integration — A 해결 전 BLOCKED
```text
provider/registry
parcel intersection
TRUE/FALSE/UNKNOWN regression
Rule Engine/API propagation
```

C. HYBRID_SPATIAL_NOTICE resolver generalization
```text
authority resolver
historical notice resolver
identity/provenance
validity timeline
spatial evidence binding
```

D. Legal ingestion / Rule Engine expansion
E. Nationwide official-source adapters / common notice schema
F. AI/RAG/evidence explanation/verification
G. FastAPI hardening, observability, reports, UI, security, deployment

현재 가장 큰 병목은 historical regulation resolver이며, UQQ700에서 검증한 패턴을 전국 고시형 규제로 일반화한다.

## 9. Git / local rules

Branch: `checkpoint/c12-fastapi-20260821`
Local root: `D:\site-ai`

`.env` commit 금지. `git add .`, `git add -A`, `git add --all` 금지. intended files만 명시적으로 stage/commit.
Large mutable output/PDF/HWP/HWPX는 commit하지 않는다. 의도적으로 versioned한 immutable manifest만 예외.
Local-only dependency: `xlrd==2.0.2`, `pypdf==6.16.2`. 현재 `Crypto/pycryptodome` 미설치 상태를 가정한다.

Known remote-tracking ref-lock recovery:
```powershell
git update-ref -d refs/remotes/origin/checkpoint/c12-fastapi-20260821
git fetch origin checkpoint/c12-fastapi-20260821
git pull
```

## 10. 채팅 handoff 정책

대화가 길어져 연속성 위험이 커지기 전에 새 채팅으로 전환한다. handoff package에는 반드시 아래를 포함한다.

```text
repo / branch / local root
latest commit
current STEP / S-number
UQQ700 safety invariants
closed source families / DO-NOT-REPEAT
latest validated semantic/output
current unresolved issue
next exact action
Git ref-lock recovery
local dependency notes
```

새 채팅은 최신 `PROJECT_STATUS.md`와 handoff package를 기준으로 즉시 다음 S-number부터 이어간다.
