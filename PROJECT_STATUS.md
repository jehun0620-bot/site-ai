# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-09-06

> 현재 개발 상태와 안전 불변조건을 기록한다. 장기 로드맵은 `PROJECT_ARCHITECTURE.md` 기준.

## 1. 현재 단계

```text
STEP 17
Target: 개발밀도관리구역
Standard code: UQQ700
Resolution type: HYBRID_SPATIAL_NOTICE
Latest validated stage: S216
Current resolution: UNKNOWN
Next stage: S217 NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY 42-version body/term scan
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

UQQ700은 아래 3개가 모두 검증되기 전 registry 등록 금지.

```text
OFFICIAL DESIGNATION IDENTITY VERIFIED
CURRENT VALIDITY VERIFIED
SITE SPATIAL INCLUSION VERIFIED
```

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
조례 문구/연혁 hit ≠ 지정고시 identity
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

## 6. S206 source-family discovery — PASS

Ranked source families:

```text
1 NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY
2 E_GAZETTE
3 GYEONGGI_OFFICIAL_RECORD
```

현재 `NATIONAL_LAW_LOCAL_ORDINANCE_HISTORY` family를 먼저 qualification 중이다. 이 family는 authority/context/timeline anchor이며 designation notice 자체를 대체하지 않는다.

## 7. National Law local ordinance chain — S207~S216

### S207 — entry/search contract forensic PASS

`ordinSc.do`의 form/function/endpoint 단서를 확보.

### S208 — guessed positive-control params FAILED SAFELY

`query`, `keyword`, `lsNm` GET guess는 positive control을 resolve하지 못함. 법적/source failure가 아니라 계약 미복원 상태로 처리.

### S209 — JS search contract forensic PASS

실제 JS 계약 확인:

```text
endpoint: ordinScListR.do
q = search term
section = ordinNm
idxList = LsKwdNm_idx,OrdinNm_idx
p3 = 3   # current
pg = 1
outmax = 50
```

### S210 — GET replay FAILED SAFELY

HTTP 200 / row 0. 이후 원인은 실제 browser method/navigation context 미재현으로 판명.

### S211 — runtime-state forensic PASS

복원:

```text
menuId=3
subMenuId=27
tabMenuId=139
subMenuIdx=1
tabMenuIdx=1
```

`OrdinSearchObj()` 및 외부 JS 추가 복원이 필요함을 확인.

### S212 — external JS contract forensic PASS

확정:

```text
OrdinSearchObj defaults:
q=""
outmax=50
p1..p7=""
p12=""
d1..d3=""
idxList=""
pg=1
dsort=""
fsort=""
section=""
ordinSeq=0
dtlYn=N
dtlBdyKeyword=""
```

`makeParam()`은 empty 값을 생략하고, `fOrdinUpdate()`는 AJAX `POST`를 사용함.

### S213 — browser-equivalent POST search technically succeeded; validator false negative

실제 결과:

```text
HTTP 200
result count: 5
direct1: 2111431
direct2: 2
direct3: 성남시 도시계획 조례
direct4: 3
gubun1: ELIS
gubun2: 1
```

HTML rendering이 `도시 계획`처럼 공백을 삽입하여 exact-string validator가 실패한 것뿐이며 검색 자체는 성공.

### S214 — normalized positive-control qualification PASS

정식 qualified:

```text
positive_control_resolved: True
current_ordin_seq: 2111431
search_contract_qualified: True
result_identity_qualified: True
semantic:
NATIONAL_LAW_SEONGNAM_URBAN_PLANNING_ORDINANCE_SEARCH_AND_RESULT_IDENTITY_QUALIFIED
```

현재 ordinance identity:

```text
ordinance: 성남시 도시계획 조례
ordinSeq: 2111431
status: current
nwYn/current code: 3
gubun: ELIS
```

### S215 — ordinance history contract forensic PASS

Current detail hidden identity:

```text
ordinNm: 성남시 도시계획 조례
ordinSeq: 2111431
ordinId: 2146953
ancYd: 20260224
ancNo: 4356
gubun: ELIS
hstLnkDpYn: 0
```

연혁 JS 계약:

```text
fOrdinHstShow()
→ POST ordinHstListR.do
→ makeParam(ordinVO.ordinValue)
```

Historical version navigation:

```text
ordinViewOrdinHst(seq, nwYn)
→ ordinInfoP.do?ordinSeq=<seq>&chrClsCd=<...>&gubun=<...>&nwYn=<...>&conDatGubunCd=<...>
```

### S216 — history positive-control replay PASS

```text
history HTTP: 200
version rows: 42
unique ordinSeq: 42
current seq seen: True
older versions: 41
history_contract_qualified: True
history_version_identity_qualified: True
technical_unknown_count: 0
semantic:
NATIONAL_LAW_SEONGNAM_URBAN_PLANNING_ORDINANCE_HISTORY_VERSION_IDENTITY_QUALIFIED
```

Current anchor:

```text
ordinSeq=2111431
ordinId=2146953
ancNo=4356
ancYd=20260224
gubun=ELIS
```

주의: S216의 broad-context `date_hint`/`anc_no_hint`는 일부 row에서 이웃 row metadata를 끌어올 수 있다. S217에서는 반드시 각 `ordinSeq` detail에서 metadata를 다시 추출/정규화한다.

## 8. S217 다음 정확한 작업

목표: 검증된 42-version chain을 이용해 historical ordinance body에서 UQQ700 관련 term/timeline anchor를 찾는다.

권장 순서:

```text
1. S216의 42 unique ordinSeq를 입력으로 사용
2. 각 version detail을 공식 endpoint로 조회
3. 각 detail에서 직접 identity 재추출:
   ordinSeq
   ordinId
   ordinNm
   ancYd
   ancNo
   시행일
   개정구분
   gubun
4. 본문 text layer에서 아래 term을 normalized scan:
   개발밀도관리구역
   개발밀도 관리구역
   개발 밀도 관리 구역
   개발밀도
5. version별 HIT / NO_HIT / TECHNICAL_UNKNOWN 분리
6. 최초 등장, 마지막 등장, 변경 경계 후보를 계산
7. term hit는 authority/context/timeline anchor로만 기록
8. designation fact / SITE TRUE/FALSE / legal absence로 승격 금지
```

S217에서 term hit가 발견되면 bulk progression을 멈추고 해당 version 전후의 조문/부칙/개정문 context를 diagnostic inspect한다.

S217 no-hit이어도 `legal absence=False`, UQQ700 UNKNOWN 유지.

## 9. UQQ700 이후 남은 개발 단계

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

## 10. Git / local rules

Repository: `jehun0620-bot/site-ai`
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

## 11. 채팅 handoff 정책

대화가 길어져 연속성 위험이 커지기 전에 새 채팅으로 전환한다. 현재는 S216에서 source-family search/result/history qualification이 완료되었으므로 새 채팅 전환에 적합한 checkpoint다.

handoff package에는 반드시 아래를 포함한다.

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

새 채팅은 최신 `PROJECT_STATUS.md`와 `PROJECT_HANDOFF_S216.md`를 기준으로 S217부터 이어간다.
