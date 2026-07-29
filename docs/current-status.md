# IEUM 현재 개발 현황

기준일: 2026-07-29

## 현재 단계

```text
P0-1 저장소·보안 정리                  완료
P0-2 LLM Provider                     완료
P0-2 VectorSearch Provider            완료
P0-2 Productivity Provider            완료
P0-3 Transcript 구조화 분석           완료
P0-4 Action Schema·승인 Workflow       구현 완료
P0-4 PostgreSQL 실제 통합 검증          Docker 단계 대기
P0-5 RAG Provider·API                 구현 완료
P0-5 RAG 근거·Action Plan 연결         완료
P0-5 PostgreSQL/pgvector 실제 검증     Docker 설치 대기
P0-6 Docker 구성                       구현 완료
P0-6 로컬 Docker 실행                  6GB RAM 리소스 제약으로 중단
P0-6 GitHub Actions CI                 완료
P0-6 PostgreSQL/pgvector CI 통합 테스트 완료
P0-6 Meeting-to-Action PostgreSQL E2E  완료
```

## 기준 코드베이스

```text
ms-2nd-project-integration-ver-1
```

`ms-2nd-project-publish`는 과거 배포 구조를 참고하기 위한 보존본으로 취급한다.

Git 설정:

```text
branch: main
origin: https://github.com/henryeffel/ai_agent.git
```

아직 최초 커밋과 push는 수행하지 않았다.

## 완료된 보안 작업

- 기존 Azure 환경파일 제거
- `.env.example` 작성
- `.env` 및 token cache Git 제외
- API 키 로그 출력 제거
- 서명된 Logic Apps URL 하드코딩 제거
- 기존 팀원 이메일 주소 제거
- CORS와 메일 수신자 설정을 환경변수로 이동
- 작업 트리 Secret 패턴 검사
- NVIDIA API 키를 백엔드 환경변수로만 사용

현재 작업 트리 Secret 검사 결과:

```text
하드코딩 NVIDIA 키: 0
서명된 Logic Apps URL: 0
기존 팀원 이메일: 0
```

## 테스트 메일 정책

메일 연동 테스트는 다음 단일 수신자만 허용한다.

```text
alfzm102435@gmail.com
```

- 다른 수신자가 설정되면 테스트 스크립트가 실행을 거부한다.
- 다중 수신자 테스트를 허용하지 않는다.
- 현재까지 실제 테스트 메일은 발송하지 않았다.

## 실행 모드

백엔드 실행 모드:

```env
APP_MODE=mock
```

또는:

```env
APP_MODE=azure
```

Mock Mode에서는 Azure Provider 모듈을 import하거나 초기화하지 않는다. 따라서 만료된 Azure 자격증명 없이 FastAPI를 실행할 수 있다.

Health endpoint:

```text
GET /
GET /health/live
GET /health/ready
```

검증 결과:

```text
GET /              HTTP 200
GET /health/live   HTTP 200
GET /health/ready  HTTP 200
```

`/health/ready`는 다음 정보를 제공한다.

- 현재 실행 모드
- LLM Provider
- LLM 모델
- Azure Provider 로드 여부

## LLM Provider

현재 구조:

```text
LLMProvider
├─ NvidiaLLMProvider
└─ MockLLMProvider
```

환경변수:

```env
LLM_PROVIDER=mock
```

또는:

```env
LLM_PROVIDER=nvidia
```

NVIDIA 설정:

```env
NVIDIA_API_KEY=
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_LLM_MODEL=nvidia/nemotron-3-super-120b-a12b
LLM_TIMEOUT_SECONDS=60
```

실제 키 값은 `.env`에만 저장하며 문서와 코드에는 기록하지 않는다.

## Transcript 구조화 분석

신규 API:

```text
POST /api/v1/meetings/analyze
```

요청:

```json
{
  "transcript": "회의 Transcript"
}
```

응답:

```json
{
  "status": "success",
  "provider": "nvidia",
  "model": "nvidia/nemotron-3-super-120b-a12b",
  "data": {
    "summary": "회의 핵심 요약",
    "decisions": ["확정된 결정사항"],
    "action_items": [
      {
        "task": "실행할 작업",
        "assignee": "담당자 또는 null",
        "due_date": "YYYY-MM-DD 또는 null"
      }
    ],
    "open_issues": ["미해결 안건"]
  }
}
```

기존 React 호환 API도 유지한다.

```text
POST /analyze-meeting
```

기존 API에서는 다음 필드명을 유지한다.

- `actionItems`
- `openIssues`
- `deadline`

## Schema 검증 정책

- Transcript는 10~100,000자만 허용한다.
- LLM 응답은 Pydantic `MeetingAnalysis`로 검증한다.
- Schema 외 추가 필드는 거부한다.
- 담당자와 기한이 명확하지 않으면 `null`을 허용한다.
- 잘못된 JSON과 Schema 불일치는 HTTP 502로 변환한다.
- 검증되지 않은 LLM 결과를 Tool 실행 단계로 전달하지 않는다.

## 검증 결과

Mock Provider:

```text
신규 분석 API               HTTP 200
기존 React 호환 API         HTTP 200
10자 미만 Transcript        HTTP 422
```

NVIDIA Provider:

```text
실제 API 연결               성공
한국어 Transcript 분석      HTTP 200
요약 추출                   성공
결정사항 추출               성공
담당자 추출                 성공
기한 추출                   성공
미해결 안건 추출            성공
```

자동 테스트:

```text
23 passed
```

테스트 내용:

- Mock Provider health 상태
- 구조화 분석 응답
- 짧은 Transcript 입력 거부
- Calendar, To Do, Email 정상 실행 결과
- Microsoft 365 인증 실패
- Microsoft 365 timeout
- 중복 Action 오류
- 이메일 부분 실패
- 지원하지 않는 Mock 시나리오
- 잘못된 일정 시간 범위
- 승인 전 Action 실행 거부
- 승인 및 거절 상태 전이
- 실행 결과와 외부 리소스 ID 저장
- timeout 시 Action/Plan 실패 기록
- Calendar 성공·Email 실패 시 부분 성공
- 동일 action_id unique constraint
- 실행 API 반복 호출 차단
- 동시 실행 요청 중 하나만 Plan 선점
- 문서 Chunk 색인
- top-k 유사도 검색
- 카테고리 필터
- 출처 Metadata 반환
- 근거 부족 시 `grounded=false`
- RAG 근거 기반 Action Plan 생성
- Action Plan 근거 Chunk ID 저장
- 근거 부족 시 외부 실행 계획 생성 거부

## 현재 주요 파일

```text
Backend/
├─ main.py
├─ ieum/
│  ├─ schemas/
│  │  └─ meeting.py
│  └─ providers/
│     └─ llm/
│        ├─ base.py
│        ├─ factory.py
│        ├─ mock.py
│        └─ nvidia.py
└─ tests/
   └─ test_meeting_analysis_api.py
```

## Action Plan 및 승인 Workflow

현재 상태:

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

DB에 저장할 핵심 정보:

```text
action_id
meeting_id
tool
payload
status
approved_by
approved_at
attempts
external_resource_id
error_code
error_message
```

구현할 핵심 규칙:

- 승인 전 실행 거부
- DB 조건부 상태 변경
- 동일 Action 중복 실행 방지
- Action별 결과 저장
- 전체 Plan의 부분 성공 계산

구현된 API:

```text
POST /api/v1/action-plans
GET  /api/v1/action-plans/{plan_id}
POST /api/v1/action-plans/{plan_id}/approve
POST /api/v1/action-plans/{plan_id}/reject
POST /api/v1/action-plans/{plan_id}/execute
```

중복 실행 방지:

- Plan은 `APPROVED → EXECUTING` 조건부 UPDATE에 성공한 요청만 실행한다.
- Action은 `PENDING → EXECUTING` 조건부 UPDATE를 거친다.
- `action_id`에 unique constraint를 적용했다.
- 동시 실행 API 테스트에서 HTTP 200 하나와 HTTP 409 하나가 반환됐다.
- 최종 Action `attempts`는 1로 유지됐다.

현재 SQLite 통합 테스트로 검증했다. PostgreSQL 실제 통합 검증은 Docker Compose 단계에서 수행한다.

## Productivity Provider

현재 구조:

```text
ProductivityProvider
└─ MockMicrosoft365Provider
```

지원 Tool:

- Outlook Calendar
- Microsoft To Do
- Email

지원 Mock 시나리오:

- `success`
- `unauthorized`
- `timeout`
- `partial_failure`
- `duplicate_action`

현재 Mock의 `duplicate_action`은 장애 시나리오 재현용이다. 실제 중복 실행 방지는 다음 단계에서 PostgreSQL의 unique constraint와 조건부 상태 변경으로 구현한다.

실제 Workflow 중복 실행 방지는 SQLAlchemy Repository의 unique constraint와 조건부 UPDATE로 구현됐다. PostgreSQL 환경의 동시성 검증은 Docker 단계에 남아 있다.

## RAG 근거와 실행 계획 연결

신규 API:

```text
POST /api/v1/action-plans/grounded
```

처리 흐름:

```text
Transcript 분석
→ 관련 조직 문서 검색
→ 검색 결과를 LLM 실행 계획 Context로 전달
→ Action Plan 생성
→ evidence_chunk_ids 저장
```

- 검색 근거가 없으면 HTTP 422로 계획 생성을 거부한다.
- LLM이 근거에서 안전한 작업을 만들지 못해도 계획 생성을 거부한다.
- 생성된 계획은 기존과 동일하게 `PENDING_APPROVAL` 상태로 시작한다.
- 수동 `POST /api/v1/action-plans` API는 하위 호환을 위해 유지한다.

## Vector Search 및 RAG

현재 구조:

```text
EmbeddingProvider
├─ MockEmbeddingProvider
└─ NvidiaEmbeddingProvider

VectorSearchProvider
├─ MockVectorSearchProvider
└─ PgVectorSearchProvider
```

API:

```text
POST /api/v1/knowledge/chunks
POST /api/v1/knowledge/search
```

지원 기능:

- Chunk ID와 문서 ID
- 제목, 본문, 카테고리
- Chunk 순서
- 원본 URL
- 문서 생성 시각
- top-k
- 최소 유사도 점수
- 카테고리 필터
- 출처가 있는 검색 결과
- 근거 유무 `grounded` 표시

NVIDIA 실제 검증:

```text
model: nvidia/llama-nemotron-embed-1b-v2
dimension: 2048
한국어 질의 top-1 문서: 정답
```

검증용 “마케팅 광고 예산” 질의에서 관련 마케팅 Chunk가 무관한 인프라 Chunk보다 높은 순위로 반환됐다.

PostgreSQL 구현:

- `CREATE EXTENSION IF NOT EXISTS vector`
- `Vector(2048)` 컬럼
- Chunk ID 기반 upsert
- cosine distance 검색
- category 조건 검색
- minimum score 필터

Docker CLI와 Compose 설치는 완료했지만 6GB RAM 환경에서 Docker Desktop의
WSL2 VM 생성이 `0x800705aa` 리소스 부족 오류로 중단됐다. 로컬 장비에
의존하지 않도록 GitHub Actions에서 PostgreSQL/pgvector 서비스 컨테이너를
실행하는 통합 검증으로 전환했다.

### 이후 작업

1. 전체 Git 이력 Secret scan
2. 기존 Azure 구현 위치 정리
3. 구조화 로그와 correlation ID 구현
4. RAG 평가셋과 Recall@3 측정
5. README 포트폴리오 문구 및 CI 배지 정리

P0 Docker 범위는 Backend와 PostgreSQL/pgvector로 제한한다. Frontend는 로컬 `npm run dev`로 실행하며 컨테이너화는 P0 이후 선택 작업으로 둔다.

사용자 준비 작업과 설치 확인 명령은 [Docker 설치 및 검증 준비](./docker-setup.md)에 정리했다.

Docker Desktop, Docker Compose와 최신 WSL 패키지 설치 및 재부팅은 완료했다.
SFC 검사에서 무결성 위반은 발견되지 않았다. Docker Desktop 초기화는
WSL2 VM 생성 시 `0x800705aa`로 실패했으며, 당시 전체 약 6GB RAM 중
사용 가능 물리 메모리는 약 467MB였다. Compose 파일은 보존하고 실제
Docker·PostgreSQL 검증은 GitHub Actions runner에서 수행한다.

## 주의사항

- P0 완료 전에는 LangGraph를 추가하지 않는다.
- P0 완료 전에는 멀티에이전트 구조를 추가하지 않는다.
- STT, 화자 분리, Reranker와 Azure IaC는 후순위다.
- 측정하지 않은 검색 성능, 비용 절감 및 latency 수치는 포트폴리오에 사용하지 않는다.
- 과거 Azure 검증과 현재 NVIDIA/Local 검증을 README에서 구분한다.
