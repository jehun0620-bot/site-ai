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

---

## 3. 현재 단계

STEP 15

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
Site Analyzer 구축 진행

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

---

## 6. 현재 데이터 구조

Site
 └── Building × N

Site:
- site_id
- address
- road_address
- sigungu_cd
- bjdong_cd
- bun
- ji
- buildings

Building:
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

---

## 7. 주요 파일

D:\site-ai

building_api_test.py
building_api_parse.py

site_data/
    site_data_model.py
    building_converter.py
    site_builder.py
    site_analyzer.py
    test_real_api_to_site.py
    test_site_analyzer.py

---

## 8. 현재 정상 작동

건축HUB API 인증키 정상
건축HUB API 요청 정상
HTTP 200
34개 건축물 조회
API JSON parsing
Site 생성
Building 객체 생성
Site Analyzer

---

## 9. 현재 문제

STEP 15 실제 API 데이터에 Site Analyzer 적용 및 결과 확인

---

## 10. 다음 단계

STEP 16

토지정보 API 연결

목표:

Site
 ├── Building 정보
 └── Land 정보

Land 정보:
- 토지면적
- 지목
- 용도지역
- 용도지구
- 토지이용규제 등

이후 법규검토 엔진 구축.

---

## 11. 개발 원칙

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