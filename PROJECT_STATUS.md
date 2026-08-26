# AI 대지분석 자동화 시스템 - PROJECT STATUS

최종 업데이트: 2026-08-26

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
Current detail: STEP 17-21-C-16-8-T-3
```

최근 hardened reverse discovery까지 수행했으나 UQQ700 historical target document identity는 아직 확인되지 않았다.

```text
SITE TRUE     BLOCKED
SITE FALSE    BLOCKED
UNKNOWN       MAINTAINED
```

현재 전체 상태: PASS / 안전 불변조건 유지

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
PHASE 8   Authority/Historical          STARTING
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

과거 한 차례 `502 / 건축HUB 응답 JSON 파싱 실패`가 있었으나 재실행은 정상 통과했다. 지속 코드 결함보다 upstream 일시적 non-JSON 응답 가능성이 높다.

운영 TODO: `fetch_building_items()` JSON parsing failure diagnostics에 HTTP status, Content-Type, response length, secret 제거 body preview를 추가한다.

---

## 9. STEP 17-21-C-16-8 — 개발밀도관리구역 UQQ700

현재 핵심 target.

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

## 10. UQQ700 현재까지 완료된 Resolution 기반

완료:

- regulation resolution type registry
- historical source family discovery/hardening
- historical source family entry endpoint qualification
- modern endpoint exclusion
- municipality exact region binding
- S-3 hardened endpoint qualification
- T-1 bounded historical target document discovery
- T-2 canonical reverse discovery
- semantic candidate gate hardening
- cross-source-family canonical URL dedupe
- provenance merge
- hardened reverse discovery
- no-document safety behavior

UQQ700을 `HYBRID_SPATIAL_NOTICE`로 분류한 결과 다음 safety를 유지한다.

```text
negative evidence disabled
verified positive blocked
runtime registration blocked
SITE TRUE blocked
SITE FALSE from source failure blocked
```

---

## 11. S-3 Historical Endpoint Qualification Hardening

Historical source family 탐색 과정에서 현대 게시판, generic navigation, unrelated official pages가 historical evidence로 오염되는 문제를 확인했다.

이를 방지하기 위해 endpoint qualification을 강화했다.

현재 hardened endpoint count:

```text
S-3 endpoints: 7
```

핵심 guard:

- official host requirement
- municipality exact region binding
- modern endpoint exclusion
- source-family qualification
- query 자체를 evidence로 사용 금지
- generic navigation 승격 금지

---

## 12. T-1 / T-2 Historical Target Discovery

S-3 hardened endpoint 범위에서 search-engine scraping 없이 official same-host bounded historical target discovery를 수행했다.

초기 reverse discovery에서는 검색 query 문자열, page-wide text, navigation, generic urban notice context에 의해 candidate가 잘못 승격될 가능성을 확인했다.

이에 다음을 추가했다.

```text
canonical document identity
canonical URL dedupe
cross-source-family dedupe
provenance merge
semantic candidate gate
```

핵심 원칙:

```text
URL candidate ≠ verified document
query evidence ≠ document evidence
```

---

## 13. Semantic Candidate Gate Hardening 결과

Candidate 승격 조건:

- official `go.kr` source
- region binding
- link-local target evidence
- document identity evidence
- navigation link 제외
- query-only evidence 제외
- page-title-only evidence 제외

결과:

```text
S-3 endpoints                    7
requests                       120
query contamination rejected 41664
raw candidates                   0
canonical candidates             0
next-stage documents             0
all_pass                      True
```

이전 reverse-discovery candidate 일부는 query-contaminated false positive였으며, hardening 후 현재 source scope에서 검증 가능한 UQQ700 historical document가 남지 않았다.

이 결과는 SITE FALSE가 아니다.

---

## 14. Hardened Historical Target Document Reverse Discovery

최종 실행 결과:

```text
S-3 endpoint count                         7
Request count                            120
HTTP success count                       120
Transport error count                      0
Query contamination rejected          41664
Page-title-only rejected                    0
Navigation links rejected                   0
Document identity rejected                  0
Raw candidate count                         0
Duplicate candidate removed                 0
Canonical record count                      0
Candidate document count                    0
Next-stage document pool count              0
```

Resolution:

```text
HISTORICAL_TARGET_DOCUMENT_REVERSE_DISCOVERY_NO_DOCUMENT
```

현재 S-3 source 범위의 hardened reverse discovery에서도 개발밀도관리구역 historical document identity는 확인되지 않았다.

따라서:

```text
SITE FALSE로 판정하지 않음
UNKNOWN 유지
```

---

## 15. Hardened Reverse Discovery Validation

전체 validation:

```text
all_pass: True
```

주요 안전 검증:

- target name / standard code valid
- resolution type hybrid spatial notice
- negative evidence disabled
- T-1 / S-3 input 존재 및 parsing 성공
- hardened endpoints loaded
- bounded reverse query matrix enabled
- search engine scraping disabled
- same-host reverse discovery enabled
- endpoint brute-force repeat disabled
- official go.kr candidate guard enabled
- region binding required
- generic urban notice promotion disabled
- query contamination disabled
- page title alone cannot qualify candidate
- link-local target evidence required
- generic navigation leakage zero
- document identity leakage zero
- canonical URL dedupe enabled
- cross-source-family dedupe enabled
- provenance merge enabled
- verified positive leakage zero
- runtime registration leakage zero
- SITE TRUE leakage zero
- final positive promotion leakage zero
- false-from-no-document leakage zero

Leakage counters는 전부 0이다.

---

## 16. UQQ700 현재 해석

현재까지 확인된 사실:

1. S-3 historical endpoint qualification은 정상 동작한다.
2. same-host bounded reverse discovery transport는 정상이다.
3. 120/120 request가 HTTP 성공했다.
4. 기존 candidate contamination은 hardening으로 제거되었다.
5. 현재 source scope에서 UQQ700 document identity는 발견되지 않았다.
6. 이것은 규제가 존재하지 않는다는 증거가 아니다.
7. 따라서 UNKNOWN이 올바른 현재 상태다.

현재 막힌 지점은 transport가 아니라 discovery model이다.

같은 endpoint에 brute-force query를 반복하지 않고 historical system이 실제 사용했던 검색 form/action 또는 notice-number identity를 복원해야 한다.

---

## 17. UQQ700 다음 단계

다음 핵심 작업:

```text
STEP 17-21-C-16-8-T-3
Historical Search Form Action & Notice Identity Recovery
```

### A. Historical Search Form Action Recovery

- historical page `<form>` 구조 분석
- action endpoint 복원
- GET / POST 확인
- hidden input 확인
- 실제 query parameter 이름 확인
- category / board / region / date parameter 확인
- JavaScript submit handler 확인

목표: 추정 query matrix가 아니라 당시 게시판의 실제 search contract를 복원한다.

### B. Notice-number Reverse Lookup Source Family

Form 복원이 불가능하거나 불충분한 경우:

- 고시번호 기반 index
- 시보/군보/구보 archive
- gazette issue index
- 첨부파일 index
- historical notice-number lookup

source family를 추가한다.

### C. Competent Authority / Source Scope

`go.kr`만으로 source authority를 인정하지 않는다.

```text
OFFICIAL HOST
→ REGION BINDING
→ SOURCE ROLE
→ LEGAL AUTHORITY SCOPE
→ TARGET REGULATION COMPATIBILITY
```

UQQ700 지정권한과 source role을 확인한 뒤 document discovery 범위를 결정한다.

---

## 18. UQQ700 Runtime Registration Gate

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

## 19. Git / Large Output 관리

최근 GitHub push에서 대용량 discovery JSON이 100 MB 제한을 초과한 문제가 발생했고, 해당 대용량 artifact를 Git history에서 제거한 후 push를 완료했다.

향후 Git 포함 권장:

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

필요 시 `.gitignore` 및 별도 artifact storage를 사용한다.

---

## 20. 최근 주요 회귀 검증 상태

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
resolution type registry                 PASS
historical source-family qualification  PASS
endpoint qualification hardening        PASS
municipality exact region binding       PASS
bounded historical target discovery     PASS
canonical reverse discovery hardening   PASS
semantic candidate gate hardening       PASS
hardened reverse discovery              PASS
safety leakage checks                    PASS
```

---

## 21. 현재 완료 판정

```text
C-16-5 Runtime Spatial Generalization       COMPLETE
C-16-7 Disaster Prevention District        COMPLETE
C-16-8 Development Density Management      IN PROGRESS
```

C-16-8 완료된 부분:

- resolution type registry
- source family discovery/hardening
- S-3 endpoint qualification
- exact region binding
- T-1 bounded target discovery
- T-2 canonical reverse discovery
- semantic candidate hardening
- hardened reverse discovery
- no-document safety behavior

미완료:

- competent authority final resolution
- actual historical search form contract recovery
- notice-number reverse lookup
- verified designation document identity
- designation timeline / current validity
- authoritative spatial scope
- positive/negative parcel regression
- runtime registry registration
- Rule Engine propagation
- FastAPI integration

---

## 22. 핵심 설계 원칙

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
- UNKNOWN은 정상적인 판정 상태

Provenance:

모든 TRUE/FALSE 핵심 evidence는 최종 공식 source까지 역추적 가능해야 한다.

---

## 23. 현재 안정 상태 요약

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
UQQ700 region binding                      PASS
UQQ700 candidate contamination guard       PASS
UQQ700 canonical dedupe                    PASS
UQQ700 provenance merge                    PASS
UQQ700 hardened reverse discovery          PASS
UQQ700 positive leakage                    0
UQQ700 false-from-no-document leakage      0

UQQ700 verified historical document        NOT FOUND
UQQ700 runtime registration                BLOCKED
UQQ700 SITE status                         UNKNOWN
```

---

## 24. 바로 다음 실행 순서

```text
1. Historical Search Form Action Recovery
2. Notice-number Reverse Lookup Source Family
3. Competent Authority / Source Scope Resolution
4. Verified Designation Document Identity
5. Designation Timeline / Current Validity
6. Authoritative Spatial Scope Recovery
7. Positive / Negative Parcel Regression
8. UQQ700 Runtime Registry Registration
9. Rule Propagation
10. Multi-SITE / FastAPI Regression
```

1~3 조사 결과에 따라 순서는 조정할 수 있다.
같은 hardened endpoint에 동일 brute-force query를 반복하지 않는다.

---

## 25. 다음 작업 성공 기준

다음 T-3 계열 작업에서 성공은 document 발견만을 의미하지 않는다.

성공 조건:

```text
A. 실제 historical search contract를 복원하거나
B. notice-number lookup source family를 공식 근거와 함께 확보하거나
C. 현재 source가 UQQ700 지정문서를 보유할 수 없는 authority/source임을 검증
```

어느 경우든 false positive 없이 다음 discovery scope를 좁히는 것이 목표다.

문서가 발견되지 않더라도 authoritative negative evidence가 없다면 UNKNOWN을 유지한다.

---

## 26. 현재 체크포인트 결론

SITE / spatial / Rule Engine / API 기반은 안정적인 회귀 상태다.

UQQ700에서는 기존 단순 spatial dataset 확장 방식에서 벗어나 `HYBRID_SPATIAL_NOTICE` 규제를 위한 Regulation Resolution architecture가 실제 적용되고 있다.

Historical reverse discovery에서 target document가 발견되지 않았지만 false positive를 제거하고 TRUE/FALSE leakage를 차단했으므로 이를 실패로 판정하지 않는다.

현재 올바른 판정:

```text
UQQ700 = UNKNOWN
```

다음 개발은 검색량을 늘리는 것이 아니라 실제 historical search form action, notice identity, competent authority/source scope를 복원하는 방향으로 진행한다.
