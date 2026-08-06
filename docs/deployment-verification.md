# IEUM 공개 배포 및 검증 기록

기준일: 2026-08-06

## 최종 배포 환경

| 영역 | 서비스 | 공개 주소 또는 구성 |
|---|---|---|
| Frontend | Vercel | `https://ai-agent-olive-nine.vercel.app` |
| Backend | Render | `https://ieum-api-sgqw.onrender.com` |
| Database | Supabase | PostgreSQL + pgvector, Session pooler |
| LLM / Embedding | NVIDIA NIM | Render 비밀 환경 변수로 설정 |
| Productivity | Mock Microsoft 365 | 실제 외부 부작용 없음 |

비밀번호, API 키, 전체 `DATABASE_URL`은 저장소와 문서에 기록하지 않는다.

## 공개 데모 흐름

```text
회의록 입력
→ Supabase pgvector 근거 검색
→ NVIDIA NIM 기반 Action Plan 생성
→ 사용자 승인
→ Mock Microsoft 365 실행
→ 실행 상태와 Mock 리소스 ID 표시
```

공개 프런트엔드는 Legacy Azure API를 호출하지 않는다. Azure 전용 `/chat`, `/files`, `/upload`, `/execute-action` 등의 경로는 Demo Backend에서 등록되지 않는다.

## 배포 과정에서 해결한 문제

### Render Blueprint가 `render.yaml`을 찾지 못함

- 원인: 파일이 기능 브랜치에만 있고 Render가 읽는 `main`에는 없었다.
- 해결: PR #1을 `main`에 병합하고 원격 `main`에서 `render.yaml` 존재를 확인했다.

### Render 시작 명령 종료 코드 127

- 원인: `dockerCommand`에서 `sh -c` 중복 래핑으로 명령 전체가 실행 파일 이름으로 해석됐다.
- 후속 문제: `&&` 역시 Render에서 셸 연산자로 해석되지 않고 Alembic 인자로 전달됐다.
- 해결: 셸 문법을 제거하고 `python -m ieum.start` 단일 entrypoint로 migration, seed, Uvicorn 실행을 순차 처리했다.
- 관련 병합: PR #2, PR #3.

### `No module named 'psycopg2'`

- 원인: 일반 `postgresql://` URL을 받은 SQLAlchemy가 기본 psycopg2 dialect를 선택했지만 프로젝트는 psycopg 3만 설치한다.
- 해결: `postgresql://` 및 `postgres://`를 `postgresql+psycopg://`로 자동 정규화했다. 애플리케이션과 Alembic에 동일하게 적용했다.
- 관련 병합: PR #4, 병합 커밋 `552a0e6`.

### Supabase 인증 실패

- 원인: Session pooler의 사용자명을 `postgres`로 설정했다.
- 해결: Supabase가 제공한 `postgres.PROJECT_REF` 사용자명과 Session pooler 포트 `5432`를 사용했다.
- 비밀번호는 Supabase `Database → Settings`에서 재설정하고 Render 환경 변수에만 저장했다.
- 반복 인증 실패로 Supavisor Circuit Breaker가 동작했으며, 자격증명 수정 후 재시도를 중단하고 임시 차단 해제를 기다렸다.

### Vercel CORS 거부

- 증상: preflight 요청이 `400 Disallowed CORS origin`을 반환했다.
- 해결: Render의 `ALLOWED_ORIGINS`를 아래 값으로 설정하고 다시 배포했다.

```text
https://ai-agent-olive-nine.vercel.app
```

Origin 값에는 따옴표와 마지막 `/`를 넣지 않는다.

## 최종 운영 검증

### Backend 상태

```text
GET /health/live  → 200 {"status":"ok"}
GET /health/ready → 200, mode=demo
GET /openapi.json → 200
GET /chat         → 404
```

Readiness에서 확인한 Provider:

- LLM: `nvidia`
- Vector Search: `pgvector`
- Productivity: `mock_microsoft_365`
- Azure Provider loaded: `false`

### CORS

Vercel Production Origin을 사용한 preflight 요청 결과:

```text
status=200
access-control-allow-origin=https://ai-agent-olive-nine.vercel.app
```

### 전체 Agent Workflow

실제 공개 API에서 다음 상태 전이를 검증했다.

```text
POST /api/v1/action-plans/grounded → 201 PENDING_APPROVAL
POST /api/v1/action-plans/{id}/approve → 200 APPROVED
POST /api/v1/action-plans/{id}/execute → 200 SUCCEEDED
```

검증 실행 결과:

- 승인자: `demo.user@example.com`
- 실행 Provider: `mock_microsoft_365`
- 실행 횟수: 1
- Mock 리소스 ID 생성 확인
- 실제 Microsoft 365 부작용 없음

## 자동화 검증 결과

- Backend: `75 passed, 1 skipped`
- Skip 1건: 전용 PostgreSQL 통합 테스트의 명시적 실행 보호
- Frontend Vite production build: 성공
- 배포 설정, migration, URL 정규화, entrypoint 회귀 테스트: 통과

## 확인된 후속 개선점

1. 첫 NVIDIA 요청에서 일시적인 `502`가 발생할 수 있으므로 제한된 재시도와 사용자 안내를 추가한다.
2. 현재 샘플 회의록과 seed 지식 간 관련성이 낮아 구매·회의실·릴리스 규정이 함께 검색될 수 있다.
3. 공개 데모의 샘플 회의록을 seed 문서에 맞추거나 마케팅 관련 지식을 추가하고 RAG 평가를 다시 수행한다.
4. Render 무료 인스턴스 cold start 동안 프런트엔드에 “서버 시작 중” 상태를 표시한다.

## 배포 환경 변수 요약

Render:

```text
APP_MODE=demo
LLM_PROVIDER=nvidia
EMBEDDING_PROVIDER=nvidia
VECTOR_SEARCH_PROVIDER=pgvector
PRODUCTIVITY_PROVIDER=mock
DATABASE_URL=<Supabase secret>
NVIDIA_API_KEY=<secret>
ALLOWED_ORIGINS=https://ai-agent-olive-nine.vercel.app
```

Vercel:

```text
VITE_API_URL=https://ieum-api-sgqw.onrender.com
```
