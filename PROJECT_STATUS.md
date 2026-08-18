# AI 대지분석·법규검토 자동화 시스템

## 1. 프로젝트 목표

건축/토지 관련 공공 API와 GIS 데이터를 활용하여

대지정보 수집
→ 대지분석
→ 건축법규 검토
→ 사업성 검토
→ 설계조건 생성
→ Grasshopper 연계

를 자동화하는 시스템 구축.

---

## 2. 개발환경

- Windows 11
- Python
- VS Code
- PowerShell
- Git
- Python virtual environment (.venv)

프로젝트 경로:

D:\site-ai

---

## 3. 현재 단계

STEP 17

STEP 16-16까지 완료.

다음 작업은 STEP 17에서 진행한다.

---

## 4. 완료된 단계

### STEP 9
건축HUB API 연결

### STEP 10
API 인증키 및 요청 URL 문제 해결

### STEP 11
건축HUB API에서 34개 건축물 조회 성공

### STEP 12
Site / Building 데이터 모델 구축

### STEP 13
API 데이터를 Building 객체로 변환

### STEP 14
실제 건축HUB API → Site → Building 34개 연결

### STEP 15
Site Analyzer 구축 및 실제 API 데이터 분석 성공

### STEP 16
VWorld 토지특성정보 API 연결 및 Land 데이터 통합

#### STEP 16-1 ~ 16-5
VWorld 토지특성정보 API 사용 준비 및 인증키 설정.

VWorld API 인증키 환경변수:

VWORLD_API_KEY

기존 건축HUB API 인증키 환경변수:

DATA_API_KEY

두 인증키를 서로 구분하여 사용한다.

#### STEP 16-6 ~ 16-9
VWorld 토지특성정보 API 호출 테스트 및 응답 데이터 확인.

테스트 PNU:

1168010300100120000

API 응답:
- HTTP 200
- 토지 데이터 2건 수신
- 최신 데이터의 최종수정일: 2025-01-16
- 기준연도: 2024
- 지번: 12
- 토지면적: 121040.4㎡
- 지목: 대
- 용도지역: 제3종일반주거지역

동일 PNU에 여러 토지 데이터가 반환될 수 있으므로 lastUpdtDt 기준으로 최신 데이터를 선택한다.

#### STEP 16-10 ~ 16-13
VWorld API 관련 모듈 및 Land 변환/통합 기능 구축.

주요 기능:
- create_pnu()
- get_land_characteristics()
- select_latest_land_record()
- convert_land_record()

Land 객체로 변환 성공.

#### STEP 16-14 ~ 16-15
건축HUB API의 34개 Building과 VWorld Land를 하나의 Site로 통합.

실제 통합 테스트 성공.

최종 Site:
- SITE ID: 11680-10300-0012-0000
- 주소: 서울특별시 강남구 개포동 12번지
- 도로명주소: 서울특별시 강남구 개포로109길 21 (개포동)
- 시군구코드: 11680
- 법정동코드: 10300
- 본번: 0012
- 부번: 0000
- 건축물 수: 34

#### STEP 16-16
Site Analyzer에 현황 건폐율 및 현황 용적률 계산 기능 추가.

실제 API 데이터 분석 성공.

최종 실제 분석 결과:

대지정보:
- 대지면적: 121040.4㎡
- 지목: 대
- 용도지역: 제3종일반주거지역
- 지구: ""
- 토지이용규제: ""

건축물정보:
- 총 건축물 수: 34
- 총 건축면적: 16771.93㎡
- 총 연면적: 226900.99㎡
- 현황 건폐율: 13.86%
- 현황 용적률: 187.46%
- 최고 지상층수: 15층
- 최대 지하층수: 1층
- 총 세대수: 4199세대

용도별 건축물 수:
- 공동주택: 28
- 노유자시설: 2
- 판매시설: 2
- 교육연구시설: 1
- 종교시설: 1

현황 건폐율 계산식:

건축면적 ÷ 대지면적 × 100

현황 용적률 계산식:

연면적 ÷ 대지면적 × 100

주의:
현황 건폐율/용적률과 법정 건폐율/용적률은 구분한다.
현재까지 법정 기준값은 시스템에 입력하지 않았다.

---

## 5. 건축HUB API

URL:

http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo

테스트 지번:

sigunguCd = 11680
bjdongCd = 10300
bun = 0012
ji = 0000

현재 API 결과:

- HTTP 200
- resultCode = 00
- resultMsg = NORMAL SERVICE
- totalCount = 34

인증키 환경변수:

DATA_API_KEY

---

## 6. VWorld 토지특성정보 API

API:

getLandCharacteristics

URL:

http://api.vworld.kr/ned/data/getLandCharacteristics

인증키 환경변수:

VWORLD_API_KEY

테스트 PNU:

1168010300100120000

주요 응답 필드:

- pnu
- ldCode
- ldCodeNm
- regstrSeCode
- regstrSeCodeNm
- mnnmSlno
- ladSn
- stdrYear
- stdrMt
- lndcgrCode
- lndcgrCodeNm
- lndpclAr
- prposArea1
- prposArea1Nm
- prposArea2
- prposArea2Nm
- ladUseSittn
- ladUseSittnNm
- tpgrphHgCode
- tpgrphHgCodeNm
- tpgrphFrmCode
- tpgrphFrmCodeNm
- roadSideCode
- roadSideCodeNm
- pblntfPclnd
- lastUpdtDt

---

## 7. 현재 데이터 구조

현재 Site는 Land와 Building을 함께 보유한다.

Site
 ├── Land
 └── Building × N

Site 주요 필드:
- site_id
- address
- road_address
- sigungu_cd
- bjdong_cd
- bun
- ji
- land
- buildings

Land 주요 필드:
- land_area
- land_category
- zoning
- district
- land_use_regulation

Building 주요 필드:
- building_id
- management_id
- dong_name
- building_name
- main_use
- land_area
- building_area
- total_floor_area
- building_coverage_ratio
- floor_area_ratio
- ground_floor_count
- underground_floor_count
- household_count
- approval_date

Site Analyzer 결과 주요 필드:
- land_area
- land_category
- zoning
- district
- land_use_regulation
- building_count
- use_count
- total_building_area
- total_floor_area
- current_building_coverage_ratio
- current_floor_area_ratio
- max_ground_floor_count
- max_underground_floor_count
- total_household_count

---

## 8. 주요 파일

D:\site-ai

기존 건축HUB 관련:
- building_api_test.py
- building_api_parse.py

site_data/:
- site_data_model.py
- building_converter.py
- site_builder.py
- site_analyzer.py
- test_real_api_to_site.py
- test_site_analyzer.py
- land_api_test.py
- land_converter.py
- vworld_api.py
- test_integrated_analysis.py

환경변수:
- .env

---

## 9. 현재 정상 작동

### 건축HUB
- API 인증키 정상
- API 요청 정상
- HTTP 200
- 34개 건축물 조회
- JSON parsing 정상
- Building 객체 변환 정상

### VWorld
- VWORLD_API_KEY 정상
- HTTP 200
- 토지특성정보 조회 정상
- PNU 생성 정상
- 여러 토지 레코드 중 최신 데이터 선택 정상
- Land 객체 변환 정상

### 통합
건축HUB Building 34개 + VWorld Land → Site 통합 정상.

### 분석
Site Analyzer를 통해 실제 대지분석 지표 계산 정상.

---

## 10. STEP 16에서 발생했던 오류 및 해결

### 오류 1
ModuleNotFoundError: No module named 'site_data'

원인:
site_data 내부에서 실행되는 테스트 파일과 import 경로 문제.

해결:
프로젝트 루트 및 site_data 경로 구조에 맞게 import를 조정하여 실제 테스트 정상 실행.

### 오류 2
KeyError: 'current_building_coverage_ratio'

원인:
site_analyzer.py에서 현황 건폐율/용적률 계산식은 추가했지만 result 딕셔너리에 해당 값을 넣지 않았음.

해결:
result에 다음 두 항목 추가.

- current_building_coverage_ratio
- current_floor_area_ratio

현재 정상 작동.

---

## 11. 현재 시스템 흐름

현재까지:

건축HUB API
      ↓
Building 데이터
      ↓
Building 객체
      ↓
      ┐
      ├── Site
      │    ├── Land ← VWorld API
      │    └── Building × 34
      └──
      ↓
Site Analyzer
      ↓
현황 대지분석
      ├── 대지면적
      ├── 건축면적
      ├── 연면적
      ├── 현황 건폐율
      ├── 현황 용적률
      ├── 층수
      ├── 세대수
      └── 용도별 건축물 수

---

## 12. 다음 단계

## STEP 17

목표:

법규 데이터를 시스템에 통합하기 위한 데이터 구조 및 법규 검토 기반 구축.

우선 다음을 설계한다.

1. Regulation 데이터 모델
2. Site와 Regulation 연결
3. 용도지역에 따른 법규 데이터 구조
4. 법정 건폐율/용적률 데이터의 출처 및 적용 우선순위 설계
5. 이후 실제 법규 데이터 연결

중요:
STEP 17에서는 현황 건폐율/용적률과 법정 건폐율/용적률을 명확히 분리한다.

법규 데이터는 단순 숫자 하나가 아니라 다음 정보를 포함할 수 있도록 설계한다.

- zoning
- building_coverage_ratio
- floor_area_ratio
- height_limit
- use_restriction
- source
- legal_basis

법정 기준은 아직 코드에 임의로 입력하지 않는다.

---

## 13. 개발 원칙

개발 경험이 거의 없는 초보자 기준으로 설명.

한 번에 하나의 단계만 진행.

각 단계마다:

1. 목표 설명
2. 폴더/파일 위치 설명
3. 코드 작성
4. 실행 명령
5. 예상 결과
6. 오류 발생 시 해결
7. 정상 확인
8. Git commit
9. 다음 단계

순서로 진행.

기존 정상 작동 코드는 가능한 한 보존한다.

API 인증키는 코드에 직접 입력하지 않고 .env 환경변수를 사용한다.

현재 인증키 변수명:
- DATA_API_KEY = 기존 건축HUB API
- VWORLD_API_KEY = VWorld 토지특성정보 API

현황 데이터와 법규 데이터를 명확히 분리한다.

---

## 14. Git 저장 기준

STEP 16-16까지 정상 작동한 상태를 기준으로 Git commit을 생성한다.

권장 commit message:

STEP 16 complete: integrate VWorld land data and current site analysis

다음 채팅에서는 PROJECT_STATUS.md를 기준으로 STEP 17부터 시작한다.
