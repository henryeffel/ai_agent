# IEUM 포트폴리오 개발 계획

## 1. 프로젝트 방향

IEUM을 새로 만드는 것이 아니라 기존 구현을 다음 방향으로 제품화·리팩터링한다.

> **기존 IEUM을 업무 실행형 AI Agent로 제품화·리팩터링한다.**

최종 프로젝트 제목:

> **IEUM — Meeting-to-Action AI Agent**

한 줄 설명:

> 회의 내용을 구조화하고 조직 문서를 RAG로 검색한 뒤, 사용자 승인을 거쳐 Outlook 일정과 Microsoft To Do를 실행하는 FastAPI 기반 업무 자동화 Agent

이번 작업의 목표는 기능을 많이 추가하는 것이 아니다. 다음 단일 Workflow를 재현 가능하고 안전하게 완성하는 것이 목표다.

```text
회의 Transcript 입력
        ↓
LLM 구조화 분석
- summary
- decisions
- action_items
        ↓
RAG로 관련 조직 문서 검색
        ↓
실행 계획 생성
- Outlook 일정
- 이메일
- Microsoft To Do
        ↓
서버 정책 및 Schema 검증
        ↓
사용자 승인
        ↓
승인된 Tool만 실행
        ↓
결과·오류·외부 리소스 ID 기록
```

이 흐름으로 다음 JD 요구사항을 증명한다.

- AI Agent
- RAG
- Tool/Function Calling
- Workflow Orchestration
- Microsoft 365 및 외부 API 연동
- Python/FastAPI
- PostgreSQL/Vector DB
- Docker
- 보안·품질·운영 최적화

## 2. 개발 범위 결정

### 반드시 구현

- Secret 제거 및 설정 정리
- NVIDIA NIM을 이용한 실제 LLM 호출
- Transcript 구조화 분석
- RAG 문서 검색
- 실행 계획 생성과 서버 검증
- 상태 기반 Agent Workflow
- 사용자 승인
- DB 수준 중복 실행 방지
- 정상·장애 시나리오를 지원하는 Mock Microsoft 365 Provider
- PostgreSQL + pgvector
- Docker Compose
- 핵심 테스트

### 경쟁력 향상을 위해 구현

- 구조화 로그 및 correlation ID
- LLM token/latency 기록
- 20개 내외의 RAG 평가셋
- Microsoft Graph 직접 연동

### 이번 핵심 범위에서 제외

- LangGraph
- 멀티에이전트
- Bicep/Terraform
- Azure Container Apps 재배포
- STT 재구현
- 화자 분리
- Reranker
- NVIDIA NIM self-hosting
- 모든 Azure 서비스를 완벽하게 추상화하는 작업

후순위 항목은 P0/P1이 완성된 후 필요성을 다시 평가한다.

## 3. 현재와 목표 실행 환경

### 과거 실제 환경

- Azure OpenAI
- Azure AI Search
- Azure Blob Storage
- Azure Speech
- Azure Logic Apps
- Microsoft Graph

교육용 Azure 구독 만료로 현재 엔드포인트와 키는 사용할 수 없다. 과거 구현과 시연 자료는 Azure 활용 경험의 근거로 보존한다.

### 현재 개발 환경

| 역할 | 현재 구현 |
|---|---|
| LLM | NVIDIA NIM |
| Vector Search | PostgreSQL + pgvector |
| Embedding | 1차 구현 시 선택 |
| Microsoft 365 | Mock Provider |
| API | FastAPI |
| Frontend | React/Vite |
| 실행 환경 | Docker Compose |

### 포트폴리오 표현 원칙

- 과거 Azure에서 실제 검증한 기능
- 현재 Local/NVIDIA/Mock 환경에서 검증한 기능
- 코드 또는 설계만 있고 실제 배포하지 않은 기능
- 목표로만 존재하고 아직 구현하지 않은 기능

위 네 가지 상태를 README에서 명확히 구분한다.

## 4. 최소 Provider 구조

처음에는 다음 세 가지 인터페이스만 분리한다.

```text
LLMProvider
VectorSearchProvider
ProductivityProvider
```

구현체:

```text
LLMProvider
├─ NvidiaLLMProvider
└─ MockLLMProvider

VectorSearchProvider
├─ PgVectorSearchProvider
└─ AzureAISearchProvider (기존 구현 보존)

ProductivityProvider
├─ MockMicrosoft365Provider
├─ MicrosoftGraphProvider (기존 구현 및 선택적 재연동)
└─ LogicAppsProvider (기존 구현 보존)
```

초기 단계에서는 `SpeechProvider`, `StorageProvider`, `EmbeddingProvider`까지 모두 추상화하지 않는다. 실제 교체 요구가 생길 때 추가한다.

## 5. NVIDIA LLM 연동

Azure OpenAI를 현재 호출할 수 없으므로 NVIDIA LLM 최소 연동은 P0에 포함한다.

초기 모델:

```text
nvidia/llama-3.3-nemotron-super-49b-v1.5
```

초기 적용 범위:

- 회의 Transcript 구조화 분석
- 요약, 결정사항, 액션 아이템 생성
- 실행 계획 생성
- 가능하면 Function Calling
- JSON Schema/Pydantic 검증

제외 범위:

- NVIDIA Whisper
- NVIDIA Reranker
- 여러 LLM 비교
- NIM self-hosting
- 모델 자동 failover

환경변수 예시:

```env
APP_MODE=development

LLM_PROVIDER=nvidia
VECTOR_STORE_PROVIDER=pgvector
PRODUCTIVITY_PROVIDER=mock

NVIDIA_API_KEY=
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_LLM_MODEL=nvidia/llama-3.3-nemotron-super-49b-v1.5
```

실제 키는 `.env`에만 저장하고 저장소에는 빈 값이 있는 `.env.example`만 제공한다.

## 6. Agent Workflow

### Workflow 상태

```text
PENDING_APPROVAL
APPROVED
REJECTED
EXECUTING
SUCCEEDED
PARTIALLY_SUCCEEDED
FAILED
```

회의 분석 자체의 실패 상태가 필요하면 `ANALYSIS_FAILED`를 별도로 둔다.

### 실행 규칙

- 승인 전에는 어떤 Action도 실행할 수 없다.
- UI 상태를 신뢰하지 않고 서버가 승인 상태를 다시 확인한다.
- LLM이 생성한 실행 인자는 Pydantic Schema로 검증한다.
- 허용된 Tool만 실행할 수 있다.
- 동일한 `action_id`는 한 번만 실행한다.
- 외부 API 요청에는 timeout을 지정한다.
- 재시도 가능한 오류만 제한적으로 재시도한다.
- 일부 Action만 성공하면 `PARTIALLY_SUCCEEDED`로 기록한다.
- 실행 결과와 외부 리소스 ID를 저장한다.
- 승인과 실행 상태 변경을 감사 로그로 남긴다.

### Action 데이터 예시

```json
{
  "action_id": "uuid",
  "meeting_id": "uuid",
  "type": "calendar",
  "status": "PENDING_APPROVAL",
  "payload": {
    "title": "후속 회의",
    "start_at": "2026-08-03T14:00:00+09:00"
  },
  "approved_by": null,
  "approved_at": null,
  "execution_attempts": 0,
  "external_resource_id": null,
  "error_code": null,
  "error_message": null
}
```

## 7. DB 트랜잭션과 멱등성

단순한 Python `if executed` 검사만으로는 중복 실행을 막을 수 없다. 동시에 요청이 들어와도 하나의 실행만 시작되도록 DB 수준에서 보장한다.

기본 실행 순서:

```text
1. DB에서 Action 조회
2. 승인 상태 확인
3. 실행 여부 확인
4. PENDING/APPROVED → EXECUTING 조건부 상태 변경
5. 상태 변경에 성공한 요청만 외부 API 호출
6. 결과와 external_resource_id 저장
7. 최종 상태 갱신
```

구현 후보:

- `action_id` unique constraint
- 조건부 `UPDATE ... WHERE status = 'APPROVED'`
- 필요 시 row lock
- 별도 idempotency key 테이블

초기 구현에서는 조건부 UPDATE와 unique constraint를 우선 사용한다.

## 8. 최소 데이터 모델

처음에는 세 개의 핵심 엔티티만 구현한다.

### Meeting

- `id`
- `title`
- `transcript`
- `summary`
- `decisions`
- `created_at`

### ActionPlan

- `id`
- `meeting_id`
- `status`
- `created_at`
- `approved_at`
- `approved_by`

### ActionExecution

- `id` 또는 `action_id`
- `action_plan_id`
- `tool`
- `payload`
- `status`
- `attempts`
- `external_resource_id`
- `error_code`
- `error_message`
- `started_at`
- `finished_at`

문서 및 Chunk 테이블은 RAG 구현 단계에서 추가한다.

## 9. Mock Microsoft 365 Provider

Azure 또는 Microsoft 계정 없이도 전체 Workflow를 실행할 수 있어야 한다.

지원 Tool:

- Outlook Calendar 일정 생성
- Microsoft To Do 작업 생성
- 이메일 발송

지원 시나리오:

```text
success
unauthorized
timeout
partial_failure
duplicate_action
```

Mock은 성공 여부만 반환하지 않고 실제 Provider와 유사한 결과를 반환한다.

```json
{
  "success": true,
  "provider": "mock_microsoft_365",
  "tool": "calendar",
  "external_resource_id": "mock-event-1234",
  "latency_ms": 120
}
```

UI와 API 응답에는 Mock Mode임을 명확하게 표시한다.

## 10. RAG 최소 구현

### 기본 흐름

```text
샘플 조직 문서
→ Chunk 생성
→ Embedding 생성
→ PostgreSQL/pgvector 저장
→ 질문 Vector 검색
→ 관련 문서와 출처 반환
→ LLM 실행 계획의 근거로 사용
```

### 초기 목표

- 샘플 조직 문서 5~10개
- 문서별 metadata 저장
- top-k 검색
- 답변과 실행 계획에 출처 표시
- 근거가 부족하면 답변 또는 실행 계획 생성 거부

### P1 평가

20개 내외의 질문으로 다음을 측정한다.

- Recall@3
- 정답 문서 검색 여부
- 출처 일치 여부
- 근거 부족 시 답변 거부 여부
- 검색 latency

실제 측정한 결과만 README와 이력서에 사용한다.

## 11. 보안 P0

가장 먼저 처리한다.

- 프런트엔드의 장기 Speech Key 제거
- API Key 로그 출력 제거
- `.env`, `BE.env`, token cache 제외
- `.env.example` 작성
- 고정 이메일 주소 제거
- 환경별 CORS 설정
- Git 이력 secret scan
- 로그에서 API token과 이메일 마스킹
- NVIDIA API 키는 백엔드에서만 사용
- LLM 출력과 Tool 입력을 신뢰하지 않고 검증

`.gitignore` 기준:

```gitignore
.env
.env.*
!.env.example
*.pem
*.key
token_cache.bin
```

## 12. Docker Compose

JD 필수 기술이므로 P0에 포함한다.

```text
docker-compose.yml
├─ backend
└─ postgres + pgvector
```

완료 조건:

```bash
docker compose up --build
```

위 명령 한 줄로 Backend와 PostgreSQL/pgvector 검증 환경이 실행돼야 한다.
Frontend는 P0 Docker 검증 범위에서 제외하고 로컬 `npm run dev`로 실행한다.

추가 요구사항:

- 단순하고 재현 가능한 Backend Dockerfile
- Backend non-root 사용자
- Backend 및 DB health check
- DB health 이후 Backend 시작
- 환경변수 기반 설정
- `.dockerignore`
- 정상 종료 처리

이번 P0에서 하지 않는 작업:

- Frontend 컨테이너화
- Nginx 및 reverse proxy
- Kubernetes 또는 Docker Swarm
- 복잡한 multi-stage 이미지 최적화
- NVIDIA NIM 자체 호스팅
- Production 배포용 Compose

## 13. 핵심 테스트

P0 완료를 위해 다음 테스트가 반드시 통과해야 한다.

```text
승인되지 않은 Action 실행 거부
동일 action_id 중복 실행 방지
동시 요청에서도 외부 실행 한 번만 수행
LLM JSON Schema 오류 처리
허용되지 않은 Tool 실행 거부
외부 Provider timeout 처리
일정 성공·이메일 실패 시 부분 성공 기록
external_resource_id 저장
RAG 근거가 없을 때 답변 또는 실행 계획 거부
로그에서 token 및 이메일 마스킹
```

테스트 계층:

- 상태 전이 및 검증 단위 테스트
- FastAPI API 테스트
- PostgreSQL 연동 통합 테스트
- Mock Provider 기반 전체 Workflow 테스트

## 14. 구조화 로그

P1에서 다음 형태의 로그를 구현한다.

```json
{
  "correlation_id": "request-uuid",
  "meeting_id": "meeting-uuid",
  "workflow_state": "EXECUTING",
  "action_id": "action-uuid",
  "tool": "calendar",
  "provider": "mock_microsoft_365",
  "latency_ms": 340,
  "attempt": 1,
  "result": "success"
}
```

LLM 호출에는 다음을 추가한다.

- Provider
- 모델명
- 입력/출력 token
- latency
- 성공 여부
- 오류 유형

## 15. Microsoft Graph 재연동

Microsoft Graph 직접 연동은 P1 선택 항목이다.

우선순위:

1. Outlook Calendar 일정 생성
2. Microsoft To Do 작업 생성
3. 이메일 발송

현재 유효한 Microsoft 계정과 Entra 애플리케이션을 준비할 수 있을 때만 실제 재연동한다. 계정 준비 때문에 전체 프로젝트 완료가 지연돼서는 안 된다.

실제 계정이 없어도 다음은 구현·검증한다.

- Provider 요청/응답 계약
- 인증 실패 처리
- timeout 처리
- HTTP 429 처리
- 부분 실패 처리
- Mock Provider 기반 전체 Workflow

기존 Logic Apps 구현은 삭제하지 않고 과거 Azure 구조로 보존한다.

## 16. 단계별 실행 계획

### P0-1 — 저장소 정리와 보안

- [x] 기준 코드베이스 결정: `ms-2nd-project-integration-ver-1`
- [x] 기존 Azure `.env`, `BE.env` 및 하드코딩 Secret 제거
- [x] API 키 로그 제거
- [x] 고정 팀원 이메일 제거
- [x] `.env.example` 작성
- [x] 현재 작업 트리 secret scan
- [x] Azure 키 없이 Mock Mode로 Backend 시작
- [ ] Git 저장소 정상화 후 전체 커밋 이력 secret scan

완료 조건:

- 저장소와 Git 이력에서 유효한 Secret이 발견되지 않는다.
- 외부 키가 없어도 Mock Mode로 Backend가 시작된다.

현재 루트 `.git` 디렉터리가 비어 있어 커밋 이력 검사는 수행할 수 없다. Git 저장소를 정상화한 뒤 `gitleaks` 등으로 전체 이력을 다시 검사한다. 현재 작업 트리에서는 NVIDIA 키가 들어 있는 루트 `.env`만 로컬에 유지하며 `.gitignore`로 제외한다.

검증 결과:

- `/`, `/health/live`, `/health/ready`가 `APP_MODE=mock`에서 HTTP 200을 반환한다.
- Azure Provider는 Mock Mode에서 import 및 초기화되지 않는다.
- NVIDIA NIM smoke test가 실제 API 호출에 성공했다.

### P0-2 — 최소 Provider 분리

- [x] `LLMProvider` 정의
- [x] `VectorSearchProvider` 정의
- [x] `ProductivityProvider` 정의
- [x] `NvidiaLLMProvider` 구현
- [x] `MockLLMProvider` 구현
- [x] `MockMicrosoft365Provider` 구현
- [ ] 기존 Azure 구현 위치 정리

완료 조건:

- 설정만 변경해 NVIDIA LLM과 Mock LLM을 전환할 수 있다.
- API 및 Workflow 코드가 구체적인 NVIDIA/Azure SDK에 직접 의존하지 않는다.

### P0-3 — Transcript 분석

- [x] Transcript 입력 API
- [x] summary/decisions/action_items Schema
- [x] NVIDIA LLM 구조화 응답
- [x] Pydantic 검증
- [x] 잘못된 JSON 및 누락 필드 오류 처리

완료 조건:

- 한국어 Transcript에서 검증된 구조화 결과를 생성한다.
- 잘못된 LLM 응답을 Tool 실행으로 전달하지 않는다.

### P0-4 — 상태 기반 Workflow

- [x] ActionPlan/ActionExecution 모델
- [x] 상태 전이 규칙
- [x] 승인 및 거절 API
- [x] 승인된 Action 실행 API
- [x] DB 조건부 상태 변경
- [x] 멱등성 및 unique constraint
- [x] 부분 성공 계산
- [x] 결과와 외부 리소스 ID 저장
- [ ] PostgreSQL 컨테이너에서 동일 Workflow 통합 검증

완료 조건:

- 승인 전에는 실행할 수 없다.
- 동시에 같은 Action을 실행해도 외부 호출은 한 번만 발생한다.
- 부분 성공과 실패 원인을 조회할 수 있다.

현재 SQLAlchemy Repository와 SQLite 통합 테스트로 상태 전이 및 동시 실행 방지를 검증했다. PostgreSQL 실제 검증은 P0-6 Docker Compose 단계에서 수행한다.

### P0-5 — RAG

- [x] PostgreSQL + pgvector Provider 구현
- [x] 샘플 문서 적재 API
- [x] Chunk 및 metadata Schema
- [x] top-k 검색
- [x] 카테고리 필터
- [x] 출처 표시
- [x] 근거 부족 시 `grounded=false`
- [x] NVIDIA 다국어 임베딩 실제 API 검증
- [x] RAG 근거 기반 Action Plan 생성
- [x] Action Plan에 근거 Chunk ID 저장
- [x] 근거 없는 실행 계획 생성 거부
- [ ] PostgreSQL/pgvector 실제 DB 통합 검증

완료 조건:

- 조직 문서 근거가 실행 계획에 포함된다.
- 근거가 없는 요청은 사실을 만들어 실행하지 않는다.

Mock Vector Store, NVIDIA 임베딩 실제 호출과 근거 기반 Action Plan 생성 흐름을 검증했다. PostgreSQL/pgvector 실제 DB 검증은 로컬 Docker가 설치되지 않아 P0-6 Docker Compose 단계에 남아 있다.

### P0-6 — Docker와 테스트

- [x] Backend Dockerfile
- [x] PostgreSQL/pgvector Docker Compose
- [x] Health check 구성
- [ ] vector extension 및 2,048차원 저장·검색 검증
- [ ] PostgreSQL 조건부 상태 변경 동시성 검증
- [ ] 동일 Action 외부 호출 1회 검증
- [ ] Meeting-to-Action 통합 테스트

완료 조건:

```bash
docker compose up --build
```

위 명령으로 Backend와 PostgreSQL/pgvector가 실행되고 핵심 통합 테스트가 통과한다. Frontend 컨테이너화는 P0 이후 선택 작업으로 둔다.

### P1 — 포트폴리오 경쟁력

- [ ] 구조화 로그 및 correlation ID
- [ ] LLM token/latency 기록
- [ ] RAG 평가 질문 약 20개
- [ ] Recall@3 및 출처 정확성 측정
- [ ] Microsoft Graph Calendar 재연동
- [ ] Microsoft Graph To Do 재연동
- [ ] GitHub Actions
- [ ] 3~5분 시연 영상
- [ ] README 포트폴리오 문구 정리

## 17. 작업 순서

```text
Secret 제거
→ 기준 코드베이스 정리
→ 최소 Provider 분리
→ NVIDIA LLM 구조화 분석
→ PostgreSQL 데이터 모델
→ 상태 기반 Workflow
→ Mock Microsoft 365
→ 멱등성·부분 성공
→ RAG
→ Docker Compose
→ 핵심 테스트
→ 구조화 로그와 RAG 평가
→ 선택적 Microsoft Graph 재연동
```

## 18. 최종 데모 시나리오

```text
1. docker compose up --build
2. NVIDIA/Local/Mock Mode 표시
3. 샘플 회의 Transcript 입력
4. LLM 구조화 분석 결과 확인
5. RAG 문서와 출처 확인
6. 일정·메일·To-do 실행 계획 확인
7. 일정과 To-do만 승인
8. 승인된 Tool만 실행되는 것을 확인
9. external_resource_id와 실행 이력 확인
10. 이메일 timeout 시 부분 성공 확인
11. 같은 Action을 다시 실행해 중복 실행이 차단되는지 확인
12. 구조화 로그와 latency 확인
13. 과거 Azure 실제 동작 화면 또는 자료 제시
```

## 19. README 상태 구분

### 과거 Azure 환경에서 실제 검증

- Azure OpenAI
- Azure AI Search
- Blob Storage
- Azure Speech
- Azure Logic Apps
- Microsoft Graph

### 현재 로컬 환경에서 검증

- NVIDIA NIM
- FastAPI
- PostgreSQL/pgvector
- Mock Microsoft 365
- 상태 기반 Agent Workflow
- Docker Compose
- 테스트

### 선택적 또는 미구현

- Azure 재배포
- Azure IaC
- Key Vault/Managed Identity 실제 구성
- LangGraph
- 멀티에이전트
- STT 및 화자 분리

### 본인 담당 범위

실제 본인 역할을 기준으로 작성하고 팀 전체 결과를 개인 구현으로 표현하지 않는다.

- FastAPI 백엔드
- LLM 구조화 및 검증
- RAG
- 업무 자동화 Workflow
- Azure/Microsoft 서비스 통합

프런트엔드, STT, 화자 분리 등 비담당 영역은 별도로 표시한다.

## 20. 성공 기준

다음 조건을 모두 만족하면 P0 개발이 완료된 것으로 본다.

- 저장소에 Secret이 없다.
- Azure 계정 없이 실행할 수 있다.
- 실제 NVIDIA LLM 호출로 Transcript를 구조화한다.
- RAG 근거를 실행 계획에 포함한다.
- 사용자 승인 전에는 실행되지 않는다.
- 동일 Action은 중복 실행되지 않는다.
- timeout과 부분 성공이 기록된다.
- 외부 리소스 ID를 저장한다.
- Docker Compose로 전체 환경을 실행한다.
- 핵심 정상·장애 시나리오가 테스트로 검증된다.

이 성공 기준을 달성하기 전에는 LangGraph, 멀티에이전트, IaC, STT 및 화자 분리 작업을 시작하지 않는다.
