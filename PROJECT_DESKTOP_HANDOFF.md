# AI 대지분석 자동화 시스템 — 두 데스크탑 개발 인계 운영 절차

최종 업데이트: 2026-09-18
기준 branch: `cleanup/repository-organization-20260916`
문서 목적: 두 데스크탑을 번갈아 사용하면서 Git 상태, 로컬 환경, 검증 결과와 미완료 작업을 안전하게 인계한다.

## 1. 운영 일정

- Desktop A: 월요일 ~ 목요일 주 사용
- Desktop B: 금요일 ~ 일요일 주 사용
- 목요일: Desktop A → Desktop B 인계일
- 일요일: Desktop B → Desktop A 인계일

요일은 기본 운영 패턴이다. 실제 전환 시에는 반드시 이 문서의 종료/시작 점검을 수행한다.

## 2. 단일 코드 인계 기준

두 PC 사이의 프로젝트 코드 인계 기준은 GitHub의 working branch 하나로 통일한다.

```text
local work
→ focused validation
→ user-local behavioral validation when required
→ status/document synchronization
→ exact-file commit
→ push
→ clean working tree 확인
→ other desktop pull --ff-only
```

한 PC에 미커밋 프로젝트 코드를 남긴 상태로 다른 PC에서 같은 작업을 시작하지 않는다.

GitHub commit 성공과 behavioral PASS는 같은 의미가 아니다. 실제 동작 검증이 필요한 기능은 사용자 로컬 실행 결과를 behavioral validation 기준으로 유지한다.

## 3. 작업 시작 절차 — 다른 PC에서 작업을 이어받을 때

먼저 현재 로컬 상태를 확인한다. 변경사항을 확인하기 전에 pull/reset/restore/checkout/clean을 실행하지 않는다.

```powershell
cd D:\site-ai
git status --short
git branch --show-current
git rev-parse HEAD
```

working tree가 예상대로 안전한 경우에만 다음을 실행한다.

```powershell
git pull --ff-only
git rev-parse HEAD
git status --short
```

`pull --ff-only`를 사용하여 예상하지 못한 merge가 자동으로 만들어지는 것을 방지한다.

`UU`, `AA`, `DD` 등 unmerged 상태나 예상하지 못한 modified/untracked 파일이 나타나면 개발을 시작하지 않는다. 먼저 파일의 정체와 Git operation 상태를 READ-ONLY로 확인한다.

## 4. 작업 종료 및 인계 절차 — 목요일 / 일요일

인계 전에 현재 상태를 먼저 확인한다.

```powershell
cd D:\site-ai
git branch --show-current
git status --short
git rev-parse HEAD
```

진행한 기능의 focused test와 필요한 사용자 로컬 behavioral validation을 완료한다. 실제 구현 상태와 문서가 다르면 관련 status 문서를 실제 검증 결과에 맞춰 갱신한다.

커밋할 때는 승인된 정확한 파일만 stage/commit한다. 다음과 같은 광역 staging은 사용하지 않는다.

```text
git add .
git add -A
git add --all
```

작업 저장 후에는 다음을 확인한다.

```powershell
git status --short
git log -1 --oneline
git push
git status --short
```

다음 PC에 넘기기 전에 가능한 한 working tree를 clean 상태로 만든다. 의도적으로 보존해야 하는 로컬 예외가 있으면 해당 예외와 이유를 인계 내용에 명시한다.

GitHub 동기화가 끝났더라도 인계는 끝난 것이 아니다. `.env`, `frontend/.env.local` 등 GitHub에 올라가지 않는 로컬 전용 파일/설정을 별도로 챙겼는지 확인한 뒤 인계를 종료한다.

## 5. 목요일 인계

목요일에는 Desktop A의 검증된 코드와 문서를 GitHub에 push한 뒤 Desktop B가 금요일에 이어받을 수 있는 상태인지 확인한다.

인계 시 확인할 항목:

- working branch
- GitHub에 push된 최종 HEAD
- `git status --short`
- 그 주에 완료된 focused validation / behavioral PASS
- 미완료 작업과 다음 첫 작업
- status 문서 갱신 여부
- 로컬 전용 환경설정 변경 여부
- GitHub 비동기화 파일을 별도로 챙겼는지 여부
- historical JSON 예외 접촉 여부

## 6. 일요일 인계

일요일에는 Desktop B의 검증된 코드와 문서를 GitHub에 push한 뒤 Desktop A가 월요일에 이어받을 수 있는 상태인지 확인한다.

확인 항목과 종료 명령은 목요일 인계와 동일하다.

## 7. GitHub 비동기화 로컬 파일 / secret 인계

다음 파일과 secret은 GitHub를 통한 PC 간 코드 동기화 대상으로 취급하지 않는다.

```text
.env
frontend/.env.local
API keys / secrets
```

각 PC에 별도로 구성한다. Frontend Kakao Maps JavaScript key도 `frontend/.env.local`의 로컬 설정으로 유지한다.

중요: 이 문서에는 실제 API Key, token, password 또는 secret 값을 기록하지 않는다. GitHub commit, status 문서, 인계 문서에도 secret 값을 복사하지 않는다.

### 인계 전 로컬 전용 파일 체크

목요일/일요일 인계 때 다음을 별도로 확인한다.

```text
[ ] D:\site-ai\.env가 현재 작업 PC에 존재하는가
[ ] D:\site-ai\frontend\.env.local이 현재 작업 PC에 존재하는가
[ ] 이번 작업 기간에 API Key / endpoint / 로컬 환경변수 구성이 변경되었는가
[ ] 변경되었다면 다음 PC에도 동일한 로컬 설정 변경이 필요한가
[ ] GitHub에 올라가지 않는 새 로컬 설정 파일이 추가되었는가
[ ] 필요한 로컬 전용 파일을 사용자가 별도의 안전한 방법으로 챙겼는가
[ ] 실제 secret 값이 Git tracked 파일이나 commit에 들어가지 않았는가
```

이 체크리스트의 목적은 secret을 GitHub에 저장하는 것이 아니라, GitHub만으로는 전달되지 않는 로컬 설정이 있다는 사실을 인계 때 빠뜨리지 않는 것이다.

로컬 파일을 다른 PC로 전달하는 방법은 사용자가 관리하는 안전한 전달 수단을 사용한다. secret 값을 채팅이나 GitHub 문서에 붙여 넣도록 요구하지 않는다.

새로운 로컬 전용 설정 파일이 실제로 생기면 그 파일의 **경로와 용도만** 이 문서에 추가할 수 있다. 실제 secret 값은 추가하지 않는다.

## 8. Python / Frontend 환경

`.venv`와 `frontend/node_modules`는 GitHub를 통해 다른 PC로 전달하는 개발 산출물이 아니다. 각 PC의 로컬 환경을 사용한다.

현재 검증된 Desktop B 환경(2026-09-18 점검):

```text
Python 3.14.7
Python executable: D:\site-ai\.venv\Scripts\python.exe
Node.js v24.21.0
npm 11.19.0
Vite v8.3.0
```

환경이 이미 존재하는 PC에서는 무조건 재설치하지 않는다. 먼저 실제 버전, 가상환경 경로, `.env`, `.env.local`, `node_modules` 존재 여부와 focused test/build를 확인한다.

## 9. historical JSON 특별 예외

특별 관리 파일:

```text
law_data/output/urban_area_conversion_history_final_resolution.json
```

Desktop A에는 과거부터 의도적으로 보존 중인 uncommitted modified copy가 존재할 수 있다. 이 로컬 수정본의 정확한 차이를 추측하거나 자동 재구성하지 않는다.

Desktop B는 GitHub에 tracked된 버전을 기준으로 사용한다. Desktop B에서 이 파일이 clean인 것은 정상일 수 있다.

Desktop A의 보존본에 대해서는 명시적 조사/결정 전까지 다음 작업을 수행하지 않는다.

```text
restore
reset
checkout으로 덮어쓰기
clean/delete
overwrite
stage
commit
```

historical/legal 작업이 이 파일에 직접 관련되는 경우 두 PC의 상태 차이를 먼저 READ-ONLY로 조사한 뒤 별도 승인 범위를 정한다.

## 10. stash / conflict 안전 원칙

예상하지 못한 stash, unmerged path 또는 conflict를 발견하면 즉시 pull/reset/restore하지 않는다.

2026-09-18 Desktop B 점검에서는 과거 stash 적용 흔적으로 `PROJECT_STATUS.md`가 `UU` 상태였고 STEP28/29 patch 파일이 untracked로 남아 있었다. 조사 결과 현재 HEAD에 STEP28/29 구현이 이미 반영되어 있음을 확인한 뒤 정확한 대상만 정리했다. 이 사례를 일반 안전 원칙으로 사용한다.

안전한 조사 순서:

```text
status
→ Git operation state 확인
→ conflict diff/index 확인
→ stash 목록/내용 확인
→ untracked 파일의 정체 확인
→ 현재 HEAD와 실제 차이 확인
→ 최소 정리 범위 승인
→ 정확한 파일만 처리
```

과거 stash는 정체가 확인되지 않았다는 이유만으로 자동 삭제하지 않는다.

## 11. 기본 환경 검증

PC 전환 후 이상이 의심될 때는 설치부터 다시 하지 말고 실제 환경을 확인한다.

Backend의 현재 Frontend 연계 핵심 focused contracts 예시:

```powershell
python -m site_data.address_parcel_candidate_search_contract_test
python -m site_data.selected_parcel_candidate_verifier_contract_test
python -m site_data.selected_parcel_candidate_site_analysis_wiring_contract_test
python -m site_data.public_api_selected_parcel_candidate_site_analysis_contract_test
```

Frontend build:

```powershell
cd D:\site-ai\frontend
npm run build
```

필요하면 Backend/Frontend를 실제 실행하여 주소 검색 → 후보 필지 → 후보 경계 → Backend 확인 → VERIFIED polygon → SITE 분석 결과까지 브라우저 E2E로 검증한다.

대표 검증 주소:

```text
서울특별시 강남구 개포동 12
```

대표 선택 필지로 과거 검증된 PNU는 `1168010300100120002`이다. 외부 데이터가 개입하므로 과거 숫자와 다르다는 이유만으로 자동 오류 판정을 하지 않는다.

## 12. 인계 요청 시 적용 원칙

사용자가 목요일 또는 일요일에 다른 데스크탑으로 작업을 넘기기 위한 점검을 요청하면 이 문서를 기준으로 현재 실제 GitHub HEAD와 로컬 출력부터 확인한다.

대화의 과거 요약보다 현재 저장소와 사용자가 제공한 로컬 실행 결과를 우선한다.

인계 응답은 최소한 다음을 확인한다.

```text
1. 현재 branch / HEAD
2. working tree 상태
3. 완료된 검증
4. 미완료 작업
5. status 문서 동기화
6. exact-file commit / push 여부
7. 로컬 환경설정 변경사항
8. GitHub 비동기화 로컬 파일(.env, frontend/.env.local 등)을 별도로 챙겼는지 여부
9. API Key / secret 구성 변경이 다음 PC에도 필요한지 여부
10. historical JSON 접촉 여부
11. 다음 PC에서 실행할 첫 명령
```

인계 요청 시 GitHub 상태만 확인하고 끝내지 않는다. 반드시 사용자에게 GitHub에 올라가지 않는 로컬 전용 파일/설정을 별도로 챙겼는지 언급한다. 필요하면 실제 secret 값을 노출하지 않고 파일의 존재 여부와 변경 필요 여부만 확인한다.

사용자가 `오늘 다른 PC로 넘기기 전 작업 마감 점검해줘`처럼 요청하면 목요일/일요일에 맞는 인계 체크를 수행한다.

## 13. 금지 원칙 요약

- 로컬 상태 확인 전 `git pull` 금지
- 예상하지 못한 conflict를 추측으로 해결하지 않음
- `git add .`, `git add -A`, `git add --all` 금지
- untracked 파일을 정체 확인 없이 삭제하지 않음
- stash를 조사 없이 pop/drop하지 않음
- secret을 GitHub에 commit하지 않음
- 실제 API Key/token/password를 인계 문서에 기록하지 않음
- Desktop A historical JSON 보존본을 자동 동기화하지 않음
- GitHub commit을 behavioral PASS로 간주하지 않음
- 한 PC의 미커밋 프로젝트 코드를 다른 PC에서 추측하여 재작성하지 않음
