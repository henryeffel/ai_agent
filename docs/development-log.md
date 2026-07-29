# IEUM 개발 작업 로그

## 2026-07-29 — GitHub Actions PostgreSQL 통합 검증 구성

### 배경

- 로컬 PC는 약 6GB RAM 환경이다.
- Docker Desktop이 WSL2 VM 생성 중 `0x800705aa` 리소스 부족 오류로
  시작되지 않았다.
- SFC 검사에서는 Windows 시스템 파일 무결성 위반이 발견되지 않았다.
- 로컬 장비 제약과 무관하게 Docker 및 PostgreSQL 검증을 재현할 수 있도록
  GitHub Actions로 검증 위치를 전환했다.

### 구현

- `.github/workflows/backend-ci.yml`을 추가했다.
- CI에서 `pgvector/pgvector:pg16` 서비스 컨테이너를 실행한다.
- 기존 SQLite·Mock 테스트와 PostgreSQL 통합 테스트를 분리했다.
- 실제 pgvector에 2,048차원 Embedding을 저장하고 검색하는 테스트를
  추가했다.
- PostgreSQL에서 동시 실행 요청 중 하나만 Action Plan을 선점하고,
  최종 실행 횟수가 1로 유지되는 테스트를 추가했다.
- Backend Docker 이미지 빌드 단계를 추가했다.

### 로컬 검증

- 기존 SQLite·Mock 테스트: `23 passed`
- PostgreSQL 전용 테스트: DB가 없으면 명시적으로 `1 skipped`
- Python compile 검사: 통과
- 로컬 `.env` Git 제외 확인
- 작업 트리 Secret 후보 패턴 검사: 발견 없음

### 남은 작업

- PostgreSQL 기반 전체 Meeting-to-Action E2E 테스트 확장

### GitHub Actions 최초 실행 결과

- Workflow: `Backend CI`
- 결과: 성공
- 실행 시간: 56초
- SQLite·Mock 테스트: 통과
- PostgreSQL/pgvector 통합 테스트: 통과
- Backend Docker 이미지 빌드: 통과
- Node.js 20 사용 중단 경고를 제거하기 위해 `actions/checkout@v5`와
  `actions/setup-python@v6`로 갱신했다.

## 2026-07-29 — Docker Compose 구성

### 구현

- Python 3.12 기반 Backend Dockerfile을 추가했다.
- Backend를 non-root `ieum` 사용자로 실행하도록 구성했다.
- Backend 빌드 컨텍스트용 `.dockerignore`를 추가했다.
- `pgvector/pgvector:pg16` PostgreSQL과 Backend를 실행하는 `compose.yaml`을 추가했다.
- PostgreSQL health check 성공 후 Backend가 시작되도록 구성했다.
- Backend `/health/ready` health check를 추가했다.
- NVIDIA API 키 없이 pgvector를 검증할 수 있도록 Mock Embedding 차원을 환경변수로 설정 가능하게 만들고, Compose에서는 2,048차원을 사용한다.

### 검증

- `docker compose config`: 통과
- Python compile 검사: 통과
- 자동 테스트: `23 passed`

### 남은 작업

- 관리자 PowerShell에서 WSL 선택적 구성 요소 활성화
- Windows 재부팅 후 Docker Engine 정상화 확인
- `docker compose up --build` 실제 기동
- vector extension, 2,048차원 저장·검색, PostgreSQL 동시성 및 전체 Workflow 통합 검증

## 2026-07-28 — P0 개발 시작

### 기준 코드베이스

- `ms-2nd-project-integration-ver-1`을 향후 개발 기준으로 확정했다.
- `ms-2nd-project-publish`는 기존 배포 형태를 참고하기 위한 보존본으로 취급한다.
- 프로젝트 방향을 신규 개발이 아닌 기존 IEUM의 업무 실행형 AI Agent 제품화·리팩터링으로 확정했다.

### 개발 범위

P0의 핵심 범위를 다음으로 제한했다.

- Secret 및 개인정보 제거
- NVIDIA NIM 기반 실제 LLM 호출
- 상태 기반 Agent Workflow
- 사용자 승인 및 DB 수준 멱등성
- Mock Microsoft 365 Provider
- PostgreSQL + pgvector RAG
- Docker Compose
- 핵심 정상·장애 테스트

다음 항목은 P0 완료 이후로 미뤘다.

- LangGraph
- 멀티에이전트
- Azure IaC 및 재배포
- STT 재구현
- 화자 분리
- Reranker

### Secret 및 개인정보 정리

- 기존 통합본의 프런트엔드 `.env`를 제거했다.
- 기존 `Backend/BE.env`를 제거했다.
- 루트와 통합본에 `.env.example`을 추가했다.
- 루트 및 각 프로젝트의 `.gitignore` 규칙을 강화했다.
- Azure OpenAI API 키를 출력하던 디버그 로그를 제거했다.
- 테스트 코드에 하드코딩되어 있던 서명된 Logic Apps URL을 제거했다.
- 백엔드에 하드코딩되어 있던 팀원 이메일 목록을 제거했다.
- 기존 팀원 이메일 주소가 작업 트리에 남아 있지 않은 것을 검사했다.
- CORS origin과 메일 수신자 목록을 환경변수 기반으로 변경했다.

현재 NVIDIA API 키는 루트 `.env`에만 보관하며 Git에서 제외한다. 실제 키 값은 문서나 코드에 기록하지 않는다.

### 테스트 메일 정책

개발용 메일 테스트는 다음 단일 주소만 허용한다.

```text
alfzm102435@gmail.com
```

- 테스트 스크립트는 `TEST_EMAIL_RECIPIENT`를 읽는다.
- 위 주소가 아닌 값이 설정되면 발송을 거부한다.
- 다중 수신자 테스트를 허용하지 않는다.
- 이번 작업 중 실제 테스트 메일은 발송하지 않았다.

### NVIDIA NIM 연결

- NVIDIA API 키를 코드에서 제거하고 `NVIDIA_API_KEY` 환경변수로 이동했다.
- Base URL과 모델명을 환경변수로 변경할 수 있게 했다.
- Smoke test의 빈 prompt를 한국어 테스트 문장으로 교체했다.
- 첫 연결 테스트에 맞게 출력 token 및 reasoning budget을 축소했다.
- `nvidia/nemotron-3-super-120b-a12b` 모델의 실제 API 호출에 성공했다.
- 한국어 응답이 정상적으로 반환되는 것을 확인했다.

### Mock Mode 부팅

- 백엔드에 `APP_MODE=mock|azure` 설정을 추가했다.
- Azure Provider 모듈은 `APP_MODE=azure`일 때만 import하고 초기화하도록 변경했다.
- Azure 키가 없는 환경에서도 FastAPI가 시작되도록 했다.
- 다음 health endpoint를 추가했다.

```text
GET /health/live
GET /health/ready
```

검증 결과:

```text
GET /              200
GET /health/live   200
GET /health/ready  200
```

Mock Mode에서는 `azure_providers_loaded=false`가 반환되는 것을 확인했다.

### 검증

- 변경한 Python 파일의 문법 검사를 통과했다.
- 현재 작업 트리에서 하드코딩된 NVIDIA 키를 찾지 못했다.
- 현재 작업 트리에서 서명된 Logic Apps URL을 찾지 못했다.
- 기존 팀원 이메일 주소 6개가 남아 있지 않은 것을 확인했다.
- 생성된 `__pycache__`는 검증 후 제거했다.

### Git 저장소

작업 시작 시 비어 있던 루트 `.git` 디렉터리를 정상 Git 저장소로 초기화했다. 다음 저장소를 fetch/push `origin`으로 등록했다.

```text
https://github.com/henryeffel/ai_agent.git
```

- 기본 브랜치: `main`
- 현재 상태: 커밋 및 push 전
- 저장소가 새로 초기화되어 검사할 과거 로컬 커밋 이력은 없다.
- 최초 커밋 전 작업 트리 Secret scan을 다시 수행한다.
- 이후 `gitleaks` 등의 도구로 커밋 이력을 지속적으로 검사한다.

## 다음 작업

P0-2 최소 Provider 분리를 진행한다.

```text
LLMProvider
├─ NvidiaLLMProvider
└─ MockLLMProvider

VectorSearchProvider
├─ PgVectorSearchProvider
└─ 기존 AzureAISearchProvider

ProductivityProvider
├─ MockMicrosoft365Provider
├─ 기존 MicrosoftGraphProvider
└─ 기존 LogicAppsProvider
```

우선 `NvidiaLLMProvider`를 FastAPI에 연결하고 Transcript 구조화 분석 API를 구현한다.

## 2026-07-28 — LLM Provider 및 Transcript 분석

### 구현

- `LLMProvider` 추상 인터페이스를 추가했다.
- `NvidiaLLMProvider`와 `MockLLMProvider`를 구현했다.
- `LLM_PROVIDER=mock|nvidia` 설정으로 구현체를 선택할 수 있게 했다.
- NVIDIA API 키, Base URL, 모델명과 timeout을 환경변수로 관리한다.
- 회의 분석용 Pydantic Schema를 추가했다.

구조화 결과:

```text
MeetingAnalysis
├─ summary
├─ decisions
├─ action_items
│  ├─ task
│  ├─ assignee
│  └─ due_date
└─ open_issues
```

- Schema에 정의되지 않은 추가 필드는 거부한다.
- Transcript 길이는 10~100,000자로 제한한다.
- 담당자와 기한을 알 수 없으면 `null`을 허용한다.
- LLM이 반환한 JSON을 Pydantic으로 다시 검증한다.
- 잘못된 JSON 또는 Schema 불일치는 안전한 502 오류로 변환한다.

### API

새 API:

```text
POST /api/v1/meetings/analyze
```

기존 React 호환 API:

```text
POST /analyze-meeting
```

기존 API는 `actionItems`, `openIssues`, `deadline` 필드명을 유지하면서 내부적으로 새 Provider를 사용한다.

`GET /health/ready` 응답에 현재 LLM Provider와 모델명을 추가했다.

### 검증

- Mock Provider 분석 API: HTTP 200
- 기존 React 호환 분석 API: HTTP 200
- 10자 미만 Transcript: HTTP 422
- NVIDIA NIM 실제 구조화 분석: HTTP 200
- 한국어 회의에서 요약, 결정사항, 담당자, 기한과 미해결 안건 추출 확인
- Mock API 회귀 테스트 3개 통과

실제 NVIDIA 검증 모델:

```text
nvidia/nemotron-3-super-120b-a12b
```

PowerShell 파이프에 한국어 리터럴을 전달한 최초 검증에서는 콘솔 인코딩으로 입력이 손상됐다. Unicode 입력으로 다시 검증해 Provider와 API가 정상 동작하는 것을 확인했다.

### 다음 작업

- `ProductivityProvider` 인터페이스
- 정상·인증 실패·timeout·중복 실행을 지원하는 `MockMicrosoft365Provider`
- Action Plan과 실행 상태 Schema

## 2026-07-28 — Mock Microsoft 365 Provider

### 구현

- `ProductivityProvider` 인터페이스를 추가했다.
- `MockMicrosoft365Provider`를 구현했다.
- `PRODUCTIVITY_PROVIDER=mock` 설정을 추가했다.
- `/health/ready`에서 현재 Productivity Provider를 표시한다.

지원 Tool:

```text
calendar
todo
email
```

지원 Mock 시나리오:

```text
success
unauthorized
timeout
partial_failure
duplicate_action
```

`partial_failure`에서는 Calendar와 To Do는 성공하고 Email만 실패하도록 구성했다. 이를 통해 다음 Workflow 단계에서 Plan 전체의 `PARTIALLY_SUCCEEDED` 계산을 검증할 수 있다.

### Tool Schema

- Calendar 제목, 시작·종료 시각, 참석자와 설명
- To Do 제목, 기한과 설명
- Email 수신자, 제목과 본문
- 알 수 없는 추가 필드 거부
- 이메일 주소 형식 검증
- Calendar 종료 시간이 시작 시간보다 늦은지 검증

모든 Tool 실행 결과는 다음 정보를 동일한 형태로 반환한다.

```text
success
provider
tool
external_resource_id
latency_ms
error_code
error_message
```

Mock 성공 결과에도 외부 서비스 응답과 유사한 `external_resource_id`를 생성한다.

### 안전 범위

- 이번 단계에서는 실제 Outlook, To Do 또는 Email을 호출하지 않았다.
- 테스트 Email payload는 허용된 단일 테스트 주소만 사용했다.
- Mock의 중복 오류는 시나리오 재현용이며 실제 멱등성은 DB 단계에서 구현한다.

### 검증

전체 테스트:

```text
10 passed
```

검증 항목:

- Calendar, To Do, Email 정상 결과
- 외부 리소스 ID 생성
- 인증 실패 예외
- timeout 예외
- 중복 Action 예외
- Email 부분 실패
- 잘못된 Mock 시나리오 거부
- 종료 시간이 시작보다 빠른 Calendar payload 거부
- 기존 Transcript 분석 API 회귀 테스트

### 다음 작업

- Action Plan 및 Action Execution Schema
- 승인/거절 상태 전이
- PostgreSQL 저장소
- 조건부 상태 변경을 통한 실제 중복 실행 방지

## 2026-07-28 — Action Plan 승인 및 실행 Workflow

### 데이터 모델

SQLAlchemy 기반으로 다음 모델을 추가했다.

```text
ActionPlan
├─ meeting_id
├─ status
├─ approved_by
├─ approved_at
└─ actions

ActionExecution
├─ action_id (unique)
├─ tool
├─ payload
├─ status
├─ attempts
├─ provider
├─ external_resource_id
├─ latency_ms
├─ error_code
└─ error_message
```

SQLite와 PostgreSQL에서 같은 모델을 사용할 수 있도록 SQLAlchemy 2.x로 구현했다. 개발 기본값은 SQLite이며 Docker 환경에서는 `DATABASE_URL`을 PostgreSQL로 설정한다.

### 상태 전이

```text
PENDING_APPROVAL
├─ REJECTED
└─ APPROVED
      ↓
   EXECUTING
      ├─ SUCCEEDED
      ├─ PARTIALLY_SUCCEEDED
      └─ FAILED
```

지원하지 않는 상태 전이는 HTTP 409로 거부한다.

### API

```text
POST /api/v1/action-plans
GET  /api/v1/action-plans/{plan_id}
POST /api/v1/action-plans/{plan_id}/approve
POST /api/v1/action-plans/{plan_id}/reject
POST /api/v1/action-plans/{plan_id}/execute
```

- 승인과 거절 요청에는 actor 이메일이 필요하다.
- 승인되지 않은 Plan은 실행할 수 없다.
- 거절된 Plan을 다시 승인하거나 실행할 수 없다.
- 존재하지 않는 Plan은 HTTP 404를 반환한다.

### DB 수준 중복 실행 방지

Plan 실행 전 다음 조건부 변경을 수행한다.

```text
APPROVED → EXECUTING
```

해당 UPDATE에 성공한 요청만 Tool 실행을 시작한다.

각 Action도 다음 조건부 변경을 수행한다.

```text
PENDING → EXECUTING
```

추가 안전장치:

- `action_id` unique constraint
- 실행 횟수 `attempts` 기록
- 실행 완료 후 반복 요청 HTTP 409
- 외부 리소스 ID 저장

두 개의 실행 요청을 동시에 보낸 테스트에서 하나는 HTTP 200, 다른 하나는 HTTP 409를 반환했다. Action 실행 횟수는 1로 유지됐다.

### 오류 및 부분 성공

- Provider 인증 실패를 Action 실패로 기록한다.
- timeout을 `error_code=timeout`으로 저장한다.
- 예상하지 못한 오류는 외부 상세정보를 노출하지 않고 `internal_error`로 저장한다.
- 모든 Action이 성공하면 `SUCCEEDED`
- 모든 Action이 실패하면 `FAILED`
- 일부만 성공하면 `PARTIALLY_SUCCEEDED`

### 검증

전체 테스트:

```text
17 passed
```

주요 검증:

- 승인 전 실행 거부
- 승인 후 단일 실행
- 반복 실행 차단
- 동시 실행 선점
- 거절 후 승인 및 실행 차단
- action_id 중복 생성 거부
- timeout 실패 기록
- 부분 성공 계산
- external_resource_id 저장

현재 동시성 테스트는 SQLite로 수행했다. PostgreSQL에서의 실제 동시성 및 transaction 동작은 Docker Compose 단계에서 추가 검증한다.

### 다음 작업

- VectorSearch Provider
- PostgreSQL/pgvector 문서 및 Chunk 저장
- RAG 검색 결과와 Action Plan 근거 연결

## 2026-07-28 — Vector Search 및 RAG 기반

### Provider

다음 인터페이스와 구현체를 추가했다.

```text
EmbeddingProvider
├─ MockEmbeddingProvider
└─ NvidiaEmbeddingProvider

VectorSearchProvider
├─ MockVectorSearchProvider
└─ PgVectorSearchProvider
```

### NVIDIA Embedding

사용 모델:

```text
nvidia/llama-nemotron-embed-1b-v2
```

구현:

- 문서에는 `input_type=passage`
- 질의에는 `input_type=query`
- 긴 입력은 `truncate=END`
- 예상 벡터 차원 2,048 검증
- API timeout 및 제한된 재시도

실제 NVIDIA API 검증 결과:

```text
vector dimension: 2048
한국어 질의 top-1 검색: 정답 Chunk
```

“마케팅 광고 예산”과 “서버 보안 패치” 문서를 색인한 뒤 마케팅 질의를 실행했으며, 마케팅 문서가 1순위로 반환됐다.

### Knowledge Schema

Chunk Metadata:

```text
chunk_id
document_id
title
content
category
chunk_index
source_url
created_at
```

검색 설정:

```text
query
category
top_k
min_score
```

검색 결과는 유사도 점수와 출처 Metadata를 함께 반환한다. 임계값을 통과한 문서가 없으면 `grounded=false`와 빈 결과를 반환한다.

### API

```text
POST /api/v1/knowledge/chunks
POST /api/v1/knowledge/search
```

### PostgreSQL/pgvector

`PgVectorSearchProvider`에 다음을 구현했다.

- vector 확장 활성화
- 2,048차원 Vector 컬럼
- Chunk ID 기반 upsert
- cosine distance 정렬
- category 필터
- top-k 및 minimum score

현재 개발 시스템에는 Docker가 설치돼 있지 않아 실제 PostgreSQL/pgvector 컨테이너 검증은 수행하지 못했다. 코드는 Mock 검색과 Python import/테스트로 검증했으며 실제 DB 검증은 Docker 단계에서 수행한다.

### 검증

전체 테스트:

```text
21 passed
```

추가된 테스트:

- 샘플 Chunk 색인
- 관련 문서 top-1 검색
- category 필터
- 출처 URL 반환
- 근거 부족 시 `grounded=false`
- 너무 짧은 Chunk 입력 거부

### 다음 작업

- RAG 검색 결과를 LLM Context로 전달
- 실행 계획에 근거 Chunk ID 저장
- 근거가 없는 Action 실행 계획 거부

## 2026-07-28 — RAG 근거 기반 Action Plan 연결

### 구현

- `POST /api/v1/action-plans/grounded` API를 추가했다.
- Transcript 분석 결과로 조직 지식 검색 Query를 구성한다.
- 검색된 Chunk를 LLM 실행 계획 Context로 전달한다.
- 생성된 Action Plan에 `evidence_chunk_ids`를 저장한다.
- 근거가 없거나 근거로 안전한 작업을 생성할 수 없으면 HTTP 422로 거부한다.
- NVIDIA Provider에는 구조화된 Action Schema 검증을 추가했다.
- Mock Provider에는 재현 가능한 근거 기반 To Do 생성을 추가했다.
- 기존 수동 Action Plan 생성 API는 호환성을 위해 유지한다.

### 검증

전체 테스트:

```text
23 passed
```

추가 검증 항목:

- 근거 기반 계획 생성
- 근거 Chunk ID의 DB 저장 및 조회
- 근거 부족 시 계획 생성 차단
- 기존 분석·RAG·승인·실행 API 회귀 테스트

### 다음 작업

- Backend Dockerfile
- PostgreSQL/pgvector Docker Compose
- PostgreSQL/pgvector 실제 통합 검증
- PostgreSQL 환경의 동시 실행 검증
- 전체 Meeting-to-Action Workflow 통합 테스트

## 2026-07-28 — Docker P0 범위 조정

- Docker의 목적을 배포 장식이 아닌 PostgreSQL/pgvector와 Workflow 동시성의 실제 검증으로 명확히 했다.
- P0 범위를 Backend와 PostgreSQL/pgvector Compose로 제한했다.
- Frontend는 로컬 `npm run dev`로 실행하고 컨테이너화는 P0 이후로 미뤘다.
- 복잡한 multi-stage 최적화, Nginx, Kubernetes와 Production Compose는 현재 범위에서 제외했다.
- Windows WSL 2 및 Docker Desktop 설치·확인 절차를 `docs/docker-setup.md`에 추가했다.

다음 구현 순서:

1. Backend Dockerfile
2. PostgreSQL/pgvector Compose
3. DB health 이후 Backend 시작
4. vector extension과 2,048차원 검색 검증
5. PostgreSQL 동시 요청과 외부 호출 1회 검증
6. 전체 Meeting-to-Action 통합 테스트

## 2026-07-28 — Docker Desktop 및 WSL 설치 체크포인트

설치 확인:

- Docker CLI `29.6.2`
- Docker Compose `v5.3.1`
- WSL `2.7.11.0`
- WSL Kernel `6.18.33.2-2`
- Docker Desktop 설치 경로 `C:\Program Files\Docker\Docker`

Docker Desktop 앱은 실행됐지만 Engine은 `stopped` 상태였다. 진단 결과 WSL 선택적 구성 요소가 아직 적용되지 않아 다음 오류가 발생했다.

```text
Wsl/WSL_E_WSL_OPTIONAL_COMPONENT_REQUIRED
```

Docker 로그에서도 WSL 가상 네트워크가 준비되지 않은 상태를 확인했다.

```text
A socket operation encountered a dead network.
```

최신 WSL 패키지 설치는 완료했으며 Windows 재부팅 후 선택적 구성 요소 적용과 Docker Engine 시작 여부를 검증한다. 구체적인 재개 명령은 `docs/docker-setup.md`의 “현재 설치 체크포인트”에 기록했다.
