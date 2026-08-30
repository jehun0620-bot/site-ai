# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-08-30

> 이 문서는 현재 개발 상태, 최근 검증 결과, 체크포인트와 바로 다음 작업을 기록한다.
> 장기 전체 설계와 시작→완성 로드맵은 `PROJECT_ARCHITECTURE.md`를 기준으로 한다.

---

## 1. 현재 단계

현재 STEP 17 진행 중이다.

Runtime Spatial Condition 공통화와 방재지구까지의 안정화는 완료되었고, 현재 핵심 개발 대상은 `STEP 17-21-C-16-8` 개발밀도관리구역(UQQ700)이다.

```text
Target: 개발밀도관리구역
Standard code: UQQ700
Resolution type: HYBRID_SPATIAL_NOTICE
Current detail: STEP 17-21-C-16-8-T-35-S85
```

현재 UQQ700 historical resolution은 다음 상태다.

```text
SITE TRUE     BLOCKED
SITE FALSE    BLOCKED
UNKNOWN       MAINTAINED
```

현재 전체 상태: PASS / 안전 불변조건 유지

현재 개발은 일시 중단 체크포인트 상태이며, 다음 재개 시 S85 결과 해석 보정부터 진행한다.

---

## 2. Architecture 기준

장기 시스템 구조는 `PROJECT_ARCHITECTURE.md` v1.0을 기준으로 한다.

```text
PHASE 0   Foundation                    COMPLETE
PHASE 1   Building/SITE                 COMPLETE
PHASE 2   Land/Spatial                  CORE COMPLETE
PHASE 3   SITE Analysis                 CORE COMPLETE
PHASE 4   Legal ingestion               IN PROGRESS
PHASE 5   Rule Engine                   IN PROGRESS / CORE STABLE
PHASE 6   Runtime spatial               CORE STABLE
PHASE 7   Regulation Resolution         ACTIVE
PHASE 8   Authority/Historical          ACTIVE
PHASE 9+  Nationwide/AI/Product         FUTURE
```

현재 개발 순서:

```text
OFFICIAL FACT → SITE FACT → REGULATION RESOLUTION → LEGAL RULE
→ DETERMINISTIC ENGINE → AI ANALYSIS → VERIFICATION
```

AI/RAG보다 공식 데이터, 규제 판정, 법규 계산, provenance 기반을 우선한다.

---

## 3. Runtime Spatial Condition 안정 기반

현재 `spatial_condition_evaluator` registry 지원 SITE runtime spatial condition은 4종이다.

```text
지구단위계획   LT_C_UPISUQ161   PASS
개발진흥지구   LT_C_UQ129       PASS
취락지구       LT_C_UQ128       PASS
방재지구       LT_C_UQ125       PASS
```

Positive regression PNU:

- 개발진흥지구: `1123010300110820000`, Feature `LT_C_UQ129.2952`
- 취락지구: `1153011100100100039`, Feature `LT_C_UQ128.20689`
- 방재지구: `1211015700105800006`, Feature `LT_C_UQ125.22`

UQQ700은 아직 runtime registry에 등록하지 않는다.

이유: HYBRID_SPATIAL_NOTICE 규제이며 공식 지정문서 identity / validity / spatial scope가 아직 검증되지 않았다.

---

## 4. Parcel Geometry 정책

Runtime spatial condition은 POINT 포함 여부만으로 TRUE를 확정하지 않는다.

필수 검증:

- 현재 SITE PNU 확보
- `LP_PA_CBND_BUBUN` Parcel Polygon / MultiPolygon 확보
- Feature PNU와 target PNU 직접 일치
- CRS `EPSG:4326`
- 대상 공간 dataset geometry 확보
- Parcel geometry와 대상 geometry 실제 `intersects()` 확인

다른 PNU에 대표 SITE snapshot 재사용 금지.
대표 snapshot PNU와 target PNU가 불일치하면 VWorld live Parcel provider fallback을 사용한다.

---

## 5. 대표 BASE / LIVE SITE

### BASE

```text
SITE ID        11680-10300-0012-0000
주소           서울특별시 강남구 개포동 12번지
PNU            1168010300100120000
용도지역       제3종일반주거지역
BCR            50.0
FAR            250.0

지구단위계획   TRUE / HIGH
개발진흥지구   FALSE / HIGH
취락지구       FALSE / HIGH
방재지구       FALSE / HIGH

rules total        314
applicable          62
not_applicable     214
conditional         36
unknown              2
```

### LIVE

```text
SITE ID        11680-10300-0013-0000
주소           서울특별시 강남구 개포동 13번지
PNU            1168010300100130000
용도지역       제1종일반주거지역
BCR            60.0
FAR            150.0

지구단위계획   TRUE / HIGH
개발진흥지구   FALSE / HIGH
취락지구       FALSE / HIGH
방재지구       FALSE / HIGH

rules total        314
applicable          62
not_applicable     216
conditional         34
unknown              2
```

---

## 6. Runtime Spatial / 방재지구 완료 상태

`C-16-5 Runtime Spatial Condition Generalization` 완료.

`build_site_analysis()`는 특정 condition을 개별 하드코딩하지 않고 `get_supported_spatial_conditions()` registry 전체를 자동 실행한다.

`C-16-7 Disaster Prevention District` 완료.

방재지구 positive parcel:

```text
PNU                    1211015700105800006
Dataset                LT_C_UQ125
Feature                LT_C_UQ125.22
Parcel dataset         LP_PA_CBND_BUBUN
Parcel geometry        MultiPolygon
Strict PNU verified    True
Intersection           True
```

Runtime regression:

```text
BASE      FALSE / HIGH
LIVE      FALSE / HIGH
POSITIVE  TRUE / HIGH
all_pass  True
```

---

## 7. Clause 189 Rule Propagation / Numeric Guard

서울특별시 도시계획 조례 clause 189 `용적률의 완화`의 상위 근거는 국토계획법 시행령 제85조제5항이다.

필수 조건:

1. 방재지구 — SITE
2. 재해예방시설 — PROJECT

결과:

```text
방재지구 FALSE
→ NOT_APPLICABLE / INACTIVE

방재지구 TRUE + 재해예방시설 UNSET
→ CONDITIONAL / POTENTIAL_CONDITIONAL

방재지구 TRUE + 재해예방시설 TRUE
→ APPLICABLE / ACTIVE_CANDIDATE
→ direct relaxation 1
→ RECALC_REQUIRED
→ BCR/FAR None / None
```

Legacy static numeric guard가 runtime TRUE를 차단하던 leakage는 제거했다.

```text
STATIC_NUMERIC_GUARD_LEAKAGE_REMOVED: True
all_pass: True
```

조건이 충족되어도 계산식이 완전히 해결되기 전 숫자를 임의 확정하지 않는다.

---

## 8. Multi-SITE / FastAPI End-to-End

실제 흐름:

```text
Building HUB → create_site() → VWorld 토지정보 → analyze_site_object()
→ PNU-aware Parcel resolver → Runtime spatial conditions
→ Rule Engine overlay → Final SITE Analysis
```

Multi-SITE 검증:

- target PNU 일치
- 대표 BASE PNU 재사용 없음
- live Parcel geometry 확보
- strict PNU verified
- runtime condition 4종 존재
- zone / BCR / FAR 정상
- rules 314
- expected rule summary 일치
- all_pass: True

FastAPI 검증:

```text
Health HTTP     200
Analysis HTTP   200
Schema          SITE_ANALYSIS_API_V1
Status          READY
SITE ID         11680-10300-0012-0000
PNU             1168010300100120000
BCR             50.0
FAR             250.0
Building count  34
all_pass        True
```

운영 TODO: `fetch_building_items()` JSON parsing failure diagnostics에 HTTP status, Content-Type, response length, secret 제거 body preview를 추가한다.

---

## 9. STEP 17-21-C-16-8 — 개발밀도관리구역 UQQ700

```text
Name             개발밀도관리구역
Standard code    UQQ700
Resolution type  HYBRID_SPATIAL_NOTICE
```

최종 evidence chain:

```text
COMPETENT AUTHORITY
→ OFFICIAL SOURCE
→ DESIGNATION DOCUMENT IDENTITY
→ CURRENT VALIDITY
→ SITE SPATIAL INCLUSION
→ TRUE / FALSE / UNKNOWN
```

현재 상태: UNKNOWN.

UQQ700은 spatial dataset hit만으로 TRUE를 확정하지 않는다.

---

## 10. UQQ700 안전 불변조건

현재까지 모든 UQQ700 discovery/recovery 단계에서 다음을 유지한다.

```text
negative_evidence_allowed = False
verified_positive          = False
runtime_registration       = BLOCKED
SITE TRUE                  = BLOCKED
SITE FALSE                 = BLOCKED
final positive promotion   = BLOCKED
```

원칙:

```text
검색 결과 ≠ 법적 사실
document 발견 ≠ current validity
query failure ≠ FALSE
source 미발견 ≠ FALSE
technical unresolved ≠ FALSE
```

---

## 11. Municipal Gazette Dynamic-HWP Source Family — TERMINALLY CLOSED

성남시 시보 dynamic-HWP era에 대해 hardened recovery를 완료했다.

최종 terminal closure validation:

```text
STEP: S72
Era rows: 1338
Processed: 1328
Quarantined: 10
Remaining: 0
Candidates: 0
Unresolved: 10
all_pass: True
```

Technical quarantines:

```text
29098
29471
181109
181376
221174
323596
339293
343270
343615
343834
```

이 10건은 `TECHNICAL_UNRESOLVED_QUARANTINED`이며 법적 FALSE가 아니다.

Dynamic-HWP source family는 UQQ700 관점에서 terminally exhausted/closed 처리한다.

중요:

```text
S49 dynamic resume를 다시 실행하지 않는다.
No hit ≠ legal absence.
Final legal resolution = UNKNOWN.
```

---

## 12. Historical Hardened Reverse Discovery

기존 S-3 hardened endpoint 범위 결과:

```text
S-3 endpoint count                         7
Request count                            120
HTTP success count                       120
Transport error count                      0
Query contamination rejected          41664
Raw candidate count                         0
Canonical record count                      0
Candidate document count                    0
Next-stage document pool count              0
```

Resolution:

```text
HISTORICAL_TARGET_DOCUMENT_REVERSE_DISCOVERY_NO_DOCUMENT
```

의미:

```text
현재 source scope에서 verified historical document identity 미확인
SITE FALSE 아님
UNKNOWN 유지
```

---

## 13. Seongnam Official Notice Reverse Lookup — S73~S76

공식 endpoint:

```text
List/Search: https://www.seongnam.go.kr/pm010301
Detail:      https://www.seongnam.go.kr/pm010301/{document_id}
```

S73/S74에서 실제 검색 계약 복원:

```text
Method: GET
controls:
  cntPerPage
  curPage
  sortType
  srchKey
  srchText

srchKey:
  sj    = 제목
  cn    = 내용
  depNm = 담당부서
```

S75에서 row-local navigation 계약 복원:

```text
onclick="javascript:f_view('<document_id>'); return false;"
```

S76에서 4개 sample로 detail identity contract 검증:

```text
f_view(document_id)
→ /pm010301/{document_id}
→ expected notice number identity match
all_pass: True
```

---

## 14. Seongnam Notice Candidate Collection / Triage — S77~S79

S77 bounded candidate collection:

```text
canonical_candidate_count              163
direct_link_local_candidate_count        0
related_link_local_candidate_count       0
discovery_context_candidate_count      163
all_pass                              True
```

정확/광범위 target query:

```text
개발밀도관리구역
개발밀도
```

제목/내용 검색에서 direct result row는 0건이었다.
이것은 legal absence가 아니다.

S78 triage:

```text
input_candidate_count   163
ranked_candidate_count  163
priority_pool_count      40
observed years        2020~2026
all_pass                True
```

S79 priority detail probe:

```text
용도구역 포함 상위 5건 상세 HTML 검사
DIRECT_DETAIL_TEXT_CANDIDATE   0
STRONG_CONTEXT_DETAIL_CANDIDATE 0
RELATED_DETAIL_TEXT_CANDIDATE  0
NO_TARGET_TERM                  5
all_pass                     True
```

---

## 15. /pm010301 Historical Coverage Boundary — S80~S82

S80에서 broad query 전체 pagination을 확인했다.

### 도시관리계획

```text
page 1~9 reachable
last page row count: 28
oldest observed year: 2010
next page 10: 0 rows
```

### 지형도면

```text
page 1~7 reachable
last page row count: 28
oldest observed year: 2010
next page 8: 0 rows
```

전체 관측 연도:

```text
2010~2026
```

S82 결과:

```text
pre2010_notice_year_observed: False
도시관리계획 last_nonempty_page: 9
도시관리계획 first_empty_page: 10
지형도면 last_nonempty_page: 7
지형도면 first_empty_page: 8
all_pass: True
```

현재 해석:

```text
/pm010301에서 검증한 broad-query 결과의 관측 하한은 2010년.
이것은 2009년 이전 UQQ700 부재 증거가 아니다.
```

---

## 16. 2010~2015 Historical Candidate Probe — S81

2010~2015 broad-query candidate:

```text
historical_candidate_count: 72
detail_target_count: 18
direct_detail_candidate_count: 0
related_detail_candidate_count: 0
no_target_term_count: 18
oldest_candidate_year: 2010
newest_candidate_year: 2015
all_pass: True
```

우선순위 상위에는 다음 유형이 포함됐다.

- 용도지역 결정(변경)
- 도시관리계획 재정비
- 지구단위계획
- 도시계획시설

상위 18개 상세 HTML에서 `개발밀도관리구역` / `개발밀도` 직접 문구는 확인되지 않았다.

법적 negative evidence로 사용하지 않는다.

---

## 17. Pre-2010 Legacy Source Family Entry — S83

S82 page HTML에서 legacy candidate endpoint를 확보했다.

Qualification 결과:

```text
LEGACY_LOCAL_GAZETTE
  https://www.seongnam.go.kr/bbs010308
  qualified: True

LEGACY_LOCAL_NOTICE
  https://www.seongnam.go.kr/bbs010101
  qualified: True

LEGACY_LOCAL_NOTICE
  https://www.seongnam.go.kr/bbs010402
  qualified: True

LEGACY_LOCAL_NOTICE
  https://www.seongnam.go.kr/bbs010403
  qualified: True
```

요약:

```text
qualified_endpoint_count: 4
qualified_gazette_endpoint_count: 1
any_pre2010_year_visible_on_entry: False
next_stage_source_family_ready: True
all_pass: True
```

---

## 18. Legacy Gazette Search Contract — S84

`bbs010308` 시보 family에서 실제 form contract를 복원했다.

검색 form:

```text
Method: POST
Action: https://www.seongnam.go.kr/bbs010308

controls:
  bbsCrtSn
  cntPerPage
  csrfToken
  pstCn
  pstSn
  pstTtl
  radio
  sortType
  srchBgngYmd
  srchDtType
  srchEndYmd
  srchText
  srchTypeCd
```

검색 field:

```text
srchTypeCd=pstTtl  제목
srchTypeCd=pstCn   내용
```

Pagination:

```text
curPage
```

Attachment endpoints도 form에서 확인됨:

```text
/bbs010308/getFile
/bbs010308/filePreview
```

현재 단계에서는 attachment download 금지 유지.

---

## 19. Legacy Gazette Pre-2010 Reachability — S85

S85에서 날짜 범위를 다음처럼 probe했다.

```text
2009
2008
2005-2007
2000-2004
```

HTTP transport는 모두 정상이다.

```text
http_status: 200
official_host: True
all_pass: True
```

그러나 현재 S85의 `row_count_hint`는 실제 시보 결과행을 신뢰성 있게 식별하지 못했다.

관측된 sample:

```text
※ 초미세먼지(PM-2.5) 발령강화(2018.7.1.) ...
2017~2024년 월별 누적 발령 횟수
```

이는 날짜 검색 결과가 아니라 page-wide/common UI contamination일 가능성이 높다.

따라서 S85 결과 해석:

```text
pre-2010 reachability VERIFIED 아님
pre-2010 absence VERIFIED 아님
POST date-filter contract 적용 여부 UNRESOLVED
row selector / hidden form state / CSRF handling 재검증 필요
```

특히 다음을 아직 확인하지 못했다.

```text
- csrfToken 실제 제출 필요 여부
- bbsCrtSn / hidden field 유지 필요 여부
- srchDtType 유효 값
- POST 후 date filter가 실제 적용됐는지
- 실제 시보 result row DOM selector
- 실제 pstSn/detail navigation extraction
```

S85의 `any_row_hint=True`를 historical reachability 증거로 사용하지 않는다.

---

## 20. 다음 재개 지점 — S86

다음 작업은 대량 검색이 아니다.

```text
STEP 17-21-C-16-8-T-35-S86
Legacy Gazette POST Search State / Result Row Contract Hardening
```

우선순위:

1. GET base page에서 hidden input 전체 복원
2. `csrfToken`, `bbsCrtSn`, 기타 hidden state 확보
3. `srchDtType` option/value 복원
4. 실제 브라우저 form POST와 동일 payload 구성
5. 날짜 filter 적용 전/후 결과 identity 비교
6. 실제 result-row selector 복원
7. result row에서 `pstSn`, 시보 호수/제목/게시일 직접 추출
8. query echo / common page UI contamination 제거
9. 그 뒤에만 pre-2010 reachability 판정
10. reachability 확인 후 UQQ700 exact/broad term reverse discovery 진행

S86 전에는 `bbs010308`의 pre-2010 coverage를 확정하지 않는다.

---

## 21. UQQ700 Runtime Registration Gate

현재 UQQ700 runtime spatial condition registry 등록은 금지 상태다.

등록 허용 최소 조건:

```text
OFFICIAL DESIGNATION IDENTITY VERIFIED
+
CURRENT VALIDITY VERIFIED
+
SITE SPATIAL INCLUSION VERIFIED
```

그 전까지:

```text
verified_positive = False
runtime_registration_allowed = False
site_positive_allowed = False
```

FALSE 역시 authoritative negative evidence 확보 전에는 생성하지 않는다.

---

## 22. Git / Large Output 관리

Git 포함 권장:

- source code
- small regression fixtures
- summary JSON
- registry
- schema

Git 제외:

- 대용량 raw discovery JSON
- downloaded PDF/HWP binary
- cache
- temporary extraction
- API raw dump

`.env`는 절대 commit하지 않는다.

Git stage 정책:

```text
git add . 금지
git add -A 금지
git add --all 금지
명시적 intended file만 stage
```

---

## 23. 최근 UQQ700 주요 Commit Checkpoint

```text
S72 terminal closure validation     0d4d0b9ac852cb6c75012dc573bd73462f962a5d
S73 notice endpoint discovery       3a0b65d8cc5a92ab5b62881dcfc1ff1ecb841964
S74 search contract forensic        7f6acd531fa2130a3894c8bcb86002b23cf37ec0
S75 result-row detail forensic      64371f8e214851299ab7ca1ff19807694c20b606
S76 detail-ID validation            0bee13897972e9a9293df0d723a36f940fd9b036
S77 candidate collection            541518af52d757072096fce10fb087a14f04b578
S78 candidate triage                06be7282848199089ad1c3dbe2efd9c94d630405
S79 priority detail probe           e4abde8da2e11667a16421da649807e01daeac0c
S80 coverage boundary               ff140e845a39c4db6e49d07c8c7bea16ccacd779
S81 2010-2015 candidate probe       fd958d38c7f7a43e50616096b5f611addb445ef1
S82 pre-2010 boundary forensic      6297a2d989403259b06030a7957bec7d6158409f
S83 legacy entry qualification      d679d268e220037e4a6abdd0a0cd5b3b2725f09a
S84 legacy search contract          4c624c01fa08587709313dddbaa2b439c622e92a
S85 pre-2010 reachability probe     e00a88305fd6dbd1e8322e3dd78d3b239700a813
```

---

## 24. 최근 주요 회귀 검증 상태

Runtime / SITE / API 주요 regression은 PASS 상태다.

- `district_unit_plan_dual_site_regression_test`
- `development_promotion_district_runtime_regression_test`
- `settlement_district_runtime_regression_test`
- `disaster_prevention_district_runtime_regression_test`
- `development_promotion_rule_propagation_regression_test`
- `settlement_district_rule_propagation_regression_test`
- `disaster_prevention_district_rule_propagation_regression_test`
- `disaster_prevention_district_numeric_guard_runtime_regression_test`
- `runtime_spatial_condition_generalization_regression_test`
- `runtime_site_condition_overlay_regression_test`
- `site_data.test_site_analysis_service`
- `site_data.test_real_multi_site_analysis`
- `test_api_app.py`

UQQ700 Historical Resolution:

```text
resolution type registry                    PASS
historical source-family qualification     PASS
endpoint qualification hardening           PASS
municipality exact region binding          PASS
hardened reverse discovery                 PASS
dynamic HWP terminal closure               PASS
notice search/detail contract              PASS
2010~2026 coverage boundary                PASS
2010~2015 historical candidate probe       PASS
legacy source entry qualification          PASS
legacy gazette search contract             PASS
S85 transport/safety validation             PASS
S85 pre-2010 semantic reachability          UNRESOLVED
```

---

## 25. 현재 완료 판정

```text
C-16-5 Runtime Spatial Generalization       COMPLETE
C-16-7 Disaster Prevention District        COMPLETE
C-16-8 Development Density Management      IN PROGRESS / CHECKPOINTED
```

C-16-8 완료된 부분:

- resolution type registry
- historical source family discovery/hardening
- S-3 endpoint qualification
- exact region binding
- hardened reverse discovery
- dynamic-HWP source family terminal closure
- official notice `/pm010301` search contract recovery
- official notice detail-ID contract validation
- bounded candidate collection/triage
- `/pm010301` 2010~2026 coverage qualification
- 2010~2015 bounded detail probe
- pre-2010 legacy source-family entry qualification
- legacy gazette form/pagination contract recovery

미완료:

- S85 legacy POST semantics/result-row hardening
- pre-2010 legacy gazette reachability verification
- competent authority final resolution
- verified designation document identity
- designation timeline / current validity
- authoritative spatial scope
- positive/negative parcel regression
- runtime registry registration
- Rule Engine propagation
- FastAPI integration

---

## 26. 핵심 설계 원칙

SITE / Spatial:

- runtime evaluator registry 중심
- POINT 단독 TRUE 확정 금지
- PNU Parcel Polygon 검증 필수
- target PNU 직접 일치
- Polygon / MultiPolygon 판정
- CRS 명확성 필수
- 다른 SITE snapshot 재사용 금지

Rule Engine:

- runtime SITE condition 우선
- historical/static resolution이 runtime 결과를 잘못 덮어쓰지 않음
- PROJECT / PROCEDURE 조건을 SITE condition과 분리
- 조건 충족 전 numeric relaxation 확정 금지
- 계산 불완전 시 `RECALC_REQUIRED`

Regulation Resolution:

- 검색 결과 ≠ 법적 사실
- endpoint 발견 ≠ document verification
- document 발견 ≠ 현재 validity
- official host ≠ competent authority
- query text ≠ candidate evidence
- page title ≠ document identity
- generic navigation ≠ target document
- source 미발견 ≠ FALSE
- technical unresolved ≠ FALSE
- UNKNOWN은 정상적인 판정 상태

Provenance:

모든 TRUE/FALSE 핵심 evidence는 최종 공식 source까지 역추적 가능해야 한다.

---

## 27. 현재 안정 상태 요약

```text
Runtime Spatial Conditions                 4

지구단위계획                               PASS
개발진흥지구                               PASS
취락지구                                   PASS
방재지구                                   PASS

Parcel PNU verification                    PASS
Runtime condition overlay                  PASS
Rule propagation                           PASS
Clause 189 upper branch                    PASS
Numeric guard leakage removal              PASS
BASE regression                            PASS
LIVE multi-site regression                 PASS
FastAPI end-to-end                         PASS

UQQ700 resolution type                     PASS
UQQ700 source hardening                    PASS
UQQ700 candidate contamination guard       PASS
UQQ700 dynamic-HWP closure                 PASS
UQQ700 /pm010301 contract                  PASS
UQQ700 2010 boundary                       PASS
UQQ700 legacy entry qualification          PASS
UQQ700 S85 transport/safety                PASS

UQQ700 verified historical document        NOT FOUND
UQQ700 pre-2010 gazette reachability        UNRESOLVED
UQQ700 runtime registration                BLOCKED
UQQ700 SITE status                         UNKNOWN
```

---

## 28. 재개 시 실행 순서

```text
1. S86 Legacy Gazette POST Search State / Result Row Contract Hardening
2. Verify CSRF / hidden form state / srchDtType
3. Recover exact result-row DOM + pstSn identity
4. Re-run bounded pre-2010 reachability with hardened selector
5. If pre-2010 rows verified, run bounded UQQ700 exact/broad reverse discovery
6. If candidate appears, stop bulk and perform document identity/context qualification
7. Competent Authority / Source Scope Resolution
8. Verified Designation Document Identity
9. Designation Timeline / Current Validity
10. Authoritative Spatial Scope Recovery
11. Positive / Negative Parcel Regression
12. UQQ700 Runtime Registry Registration
13. Rule Propagation
14. Multi-SITE / FastAPI Regression
```

같은 endpoint에 동일한 brute-force query를 반복하지 않는다.

---

## 29. 현재 체크포인트 결론

SITE / spatial / Rule Engine / API 기반은 안정적인 회귀 상태다.

UQQ700은 `HYBRID_SPATIAL_NOTICE` 규제를 위한 Regulation Resolution architecture로 처리 중이다.

현재까지:

- dynamic-HWP gazette family는 terminally closed
- `/pm010301`은 2010~2026까지 historical notice search coverage가 검증됨
- 2010~2015 bounded detail probe에서는 target direct/related term 미확인
- pre-2010 legacy gazette endpoint와 form contract는 복원됨
- S85 POST date-range probe는 transport는 성공했으나 실제 결과행 식별에 contamination이 있어 semantic reachability는 미확정

따라서 현재 올바른 판정은 계속:

```text
UQQ700 = UNKNOWN
```

프로젝트 재개 시 S85를 법적/검색 부재 근거로 사용하지 않고, S86에서 POST hidden state와 실제 result-row identity부터 hardening한다.
