# IEUM 공개 데모 배포 계획

작성일: 2026-08-06

## 결정 배경

Azure 구독이 만료된 상태이므로 공개 데모를 위해 Azure 계정을 다시 결제하지 않는다. Microsoft 365 업무 연동 구조와 Agent Workflow는 Provider 구현과 과거 Legacy 코드로 설명하고, 공개 데모는 외부 부작용과 자격증명 노출을 막기 위해 Mock Productivity Provider를 사용한다.

이 결정은 Azure 기능을 구현하지 못했다는 의미가 아니다. 외부 구독 만료로 프로젝트 전체가 실행 불가능해지는 문제를 줄이기 위해 LLM, Vector Search와 Productivity 계층을 Provider로 분리하고 공개 재현 환경을 별도로 구성하는 것이다.

## 최종 배포 구조

```text
React/Vite Frontend
→ Vercel

FastAPI Backend
→ Render

PostgreSQL + pgvector
→ Supabase

LLM / Embedding
→ NVIDIA NIM

Productivity Provider
├── 공개 데모: MockMicrosoft365Provider
├── 코드 계약: LogicAppsMicrosoft365Provider
└── 코드 계약: MicrosoftGraphProductivityProvider
```

## 환경 모드

공개 배포를 위해 `APP_MODE=demo`를 새로 추가한다.

| 모드 | 목적 | LLM/Search | Productivity | Legacy Azure Router |
|---|---|---|---|---|
| `mock` | 로컬·CI 재현 | Mock | Mock | 미등록 |
| `demo` | 공개 포트폴리오 | NVIDIA NIM + pgvector | Mock만 허용 | 미등록 |
| `azure` | 과거 Legacy 호환 | Azure 환경 설정에 따름 | 설정에 따름 | 등록 |

권장 공개 환경변수:

```env
APP_MODE=demo
LLM_PROVIDER=nvidia
EMBEDDING_PROVIDER=nvidia
VECTOR_SEARCH_PROVIDER=pgvector
PRODUCTIVITY_PROVIDER=mock
DATABASE_URL=postgresql+psycopg://...
ALLOWED_ORIGINS=https://<production-vercel-domain>
```

`demo` 모드에서는 Logic Apps나 Microsoft Graph Provider를 선택해도 startup 또는 readiness 단계에서 명시적으로 거부해야 한다.

## 현재 완료된 기반 작업

- 루트 README
- 신규 API와 Legacy Azure Router 격리
- Mock 모드에서 Legacy route 미등록
- Logic Apps Productivity Provider
- Microsoft Graph Productivity Provider와 HTTP mock 계약
- PostgreSQL/pgvector Provider
- Alembic migration
- 승인·중복 실행·부분 실패 처리
- 구조화 로그와 request ID
- RAG 전처리 및 소규모 평가
- Copilot Studio connector용 OpenAPI

따라서 다음 단계는 구조 재작성보다 공개 배포 안전장치와 실제 PostgreSQL 환경 검증이다.

## 배포 전 필수 변경

### 1. Demo 모드 안전장치

- [x] `APP_MODE=demo` 허용
- [x] Legacy Azure Router 미등록
- [x] `PRODUCTIVITY_PROVIDER=mock` 강제
- [x] NVIDIA LLM·Embedding, pgvector, PostgreSQL 조합 검증
- [x] 실제 Calendar, To Do와 Email 외부 실행 차단 테스트
- [x] 사용자 입력 역할 헤더를 무시하는 고정 Demo identity

### 2. 공개 Knowledge 색인 보호

다음 API를 인증 없이 공개하면 임의 문서가 DB에 계속 저장될 수 있다.

```text
POST /api/v1/knowledge/chunks
```

공개 데모에서는 다음 방식으로 보호한다.

1. 배포용 seed command로 샘플 문서를 미리 색인한다.
2. [x] `demo` 모드에서는 외부 Knowledge 색인 API를 비활성화한다.
3. 검색 API는 공개하되 category와 결과 수 제한을 유지한다.
4. [x] `demo-` Plan만 대상으로 하는 만료 정리 command를 추가한다.
5. IP 또는 request 단위 rate limit을 검토한다.

### 3. 사용자 데이터 안내

공개 화면에 다음 내용을 표시한다.

> 공개 데모에는 실제 회사 기밀, 개인정보, 고객 이메일을 입력하지 마세요. 입력된 회의 내용은 분석에 사용되며 생성된 Action Plan 일부는 데모 DB에 저장될 수 있습니다.

가능하면 demo session ID를 도입하고 일정 시간이 지난 Plan과 Action 결과를 삭제한다.

### Demo seed와 데이터 정리

외부 색인 API 대신 배포 전에 신뢰된 운영자 환경에서 다음 명령을 실행한다.

```powershell
cd ms-2nd-project-integration-ver-1/Backend
python -m ieum.demo seed
```

번들된 5개 규정 문서는 제목·문단 기준으로 10개 Chunk가 되며 고정 `chunk_id`를 사용해 재실행해도 upsert된다. Render 재시작마다 NVIDIA embedding 비용이 발생하지 않도록 Web Service 시작 명령에는 seed를 넣지 않는다. Supabase 연결이 가능한 로컬 운영자 환경이나 별도 승인된 배포 작업에서 한 번 실행한다.

24시간이 지난 공개 Demo Plan과 Action을 정리한다.

```powershell
python -m ieum.demo cleanup --older-than-hours 24 --confirm
```

`--confirm` 없이는 삭제가 실행되지 않는다. 정리 대상은 `meeting_id`가 `demo-`로 시작하는 Plan뿐이며 관련 Action을 먼저 삭제한다. 공개 Demo API에서 생성되는 Plan에는 서버가 자동으로 이 prefix를 적용한다. 초기에는 운영자가 수동 실행하고, 이후 GitHub Actions schedule 또는 별도 scheduler를 도입할 때 Supabase Secret 범위를 최소화한다.

## Supabase PostgreSQL 검증

현재 작업 PC에서는 Docker daemon을 사용할 수 없으므로 로컬 container 검증은 더 이상 시도하지 않는다. PostgreSQL 검증은 비어 있는 전용 Supabase 프로젝트에서 수행한다.

Supabase에서 `vector` extension을 활성화하고 다음 설정을 사용한다.

```env
DATABASE_URL=postgresql+psycopg://...
VECTOR_SEARCH_PROVIDER=pgvector
EMBEDDING_PROVIDER=mock
MOCK_EMBEDDING_DIMENSION=2048
```

검증 순서:

```powershell
cd ms-2nd-project-integration-ver-1/Backend
alembic upgrade head
alembic downgrade -1
alembic upgrade head
python -m pytest -q tests/integration
```

전용 DB를 확인한 뒤 제공된 보호 스크립트를 사용할 수 있다.

```powershell
python scripts/verify_supabase.py --confirm-empty-database
```

이 스크립트는 IEUM table을 downgrade하고 다시 생성하므로 기존 Demo 데이터가 있거나 다른 서비스가 공유하는 DB에서는 실행하면 안 된다. PostgreSQL URL이 아니거나 명시적 확인 옵션이 없으면 실행을 거부한다. CI도 `IEUM_INTEGRATION_DATABASE=1`이 설정된 전용 service database에서만 통합 테스트를 실행한다.

검증 항목:

- `vector` extension 생성 또는 사전 활성화
- `document_chunks.embedding vector(2048)`
- `section`, `document_updated_at` metadata column
- pgvector 색인·유사도 검색
- Action Plan 동시 실행 선점
- meeting-to-action PostgreSQL E2E
- migration downgrade와 재적용

Supabase 권한으로 `CREATE EXTENSION`이 불가능하면 Dashboard에서 extension을 한 번 활성화하고 migration 책임을 문서화한다. 애플리케이션 연결에는 session pooler를 검토하고, migration에는 가능하면 direct connection을 사용한다. SSL 연결도 적용한다.

현재 로컬 결과의 `PostgreSQL integration: 1 skipped`는 실패가 아니라 DB 연결 부재로 인한 의도적 skip이다. Supabase 검증이 통과하기 전에는 PostgreSQL 최신 변경 검증 완료로 표시하지 않는다.

## Render Backend

저장소 루트의 `render.yaml`에 Docker build context, Singapore region, Demo Provider 조합, health check와 Secret placeholder를 선언했다. `DATABASE_URL`, `NVIDIA_API_KEY`, `ALLOWED_ORIGINS`는 Blueprint에 값을 저장하지 않고 Render Dashboard에서 입력한다.

Render 시작 명령은 migration 적용과 동적 port를 포함해야 한다.

```sh
sh -c "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT"
```

주의사항:

- 무료 Web Service는 유휴 상태에서 sleep될 수 있다.
- cold start 동안 사용자에게 “서버 시작 중” 안내를 표시한다.
- SQLite, upload 파일과 token cache를 로컬 filesystem에 저장하지 않는다.
- DB와 외부 API 연결 timeout을 유지한다.
- 면접 기간에는 필요하면 일시적으로 유료 instance 사용을 검토한다.
- 여러 instance를 실행하기 전 migration 동시 실행 전략을 별도로 검토한다.

## Vercel Frontend

Frontend 루트의 `vercel.json`에 Vite build와 BrowserRouter SPA rewrite를 추가했다. Vercel 프로젝트 생성 시 Root Directory를 `ms-2nd-project-integration-ver-1`로 지정한다.

Vite build 환경변수:

```env
VITE_API_URL=https://<render-service>.onrender.com
```

Backend CORS:

```env
ALLOWED_ORIGINS=https://<production-vercel-domain>
```

Preview domain 전체를 무제한 wildcard로 허용하지 않는다. Production domain을 우선 고정하고 필요한 Preview origin만 명시적으로 추가한다.

Frontend에 추가할 UX:

- Render cold start 안내와 재시도
- 실제 M365가 아닌 Mock 실행이라는 표시
- 실제 회사 기밀·개인정보 입력 금지 안내
- `PARTIALLY_SUCCEEDED`와 도구별 오류 표시
- Backend readiness 실패 안내

### 현재 Frontend 배포 차단 항목

Production Vite build 자체는 통과했지만 일부 화면은 아직 다음 Legacy Azure endpoint를 호출한다.

```text
/chat
/dashboard-data
/files
/upload
/delete
/execute-action
/approve-calendar
/create-outlook-task
/generate-minutes
```

Demo Backend는 이 route를 의도적으로 등록하지 않으므로 현재 Frontend를 그대로 공개하면 Upload, Legacy chat과 기존 자동화 버튼이 실패한다. 실제 배포 전 다음 중 하나가 필요하다.

1. 공개 Demo UI를 신규 meeting/action-plan API 흐름으로 전환한다.
2. 지원하지 않는 Legacy 메뉴를 Demo build에서 숨기고 이유를 표시한다.

Legacy route를 Demo Backend에 다시 노출하는 방식은 사용하지 않는다.

## README 표현 원칙

### 실제 공개 배포 환경

```text
Frontend: Vercel
Backend: Render
Database: Supabase PostgreSQL + pgvector
LLM: NVIDIA NIM
Productivity: Mock Microsoft 365
```

실제 배포가 완료된 뒤 URL과 상태를 기록한다. 완료 전에는 목표 구조라고 표시한다.

### 과거 Azure 구현

실제 본인 실행 기록이 확인될 때만 “Azure에서 실제 연동했다”고 표현한다. 증거가 부족하면 다음 문구를 사용한다.

> 기존 팀 프로젝트의 Azure AI Search·Blob Storage·Logic Apps 연동 코드를 보존하고, 개인 개선 과정에서 외부 자격증명 없이 재현 가능한 Provider 구조로 분리했습니다.

### Microsoft Graph

현재 정확한 표현:

> Microsoft Graph REST 계약과 OAuth token provider 경계를 구현하고 HTTP mock으로 검증했습니다. 실제 tenant admin consent와 delegated OAuth flow는 아직 검증하지 않았습니다.

## 실행 순서

```text
1. [완료] APP_MODE=demo 추가
2. [완료] Demo Productivity Provider 강제 및 회귀 테스트
3. [완료] Knowledge 색인 API 보호
4. [완료] Demo seed command와 정리 정책 추가
5. Supabase project와 vector extension 준비
6. Alembic migration 왕복 검증
7. PostgreSQL 통합 테스트의 skip 제거
8. Render 환경과 시작 명령 구성
9. Backend 배포와 readiness 확인
10. Vercel API URL과 CORS 구성
11. Frontend 배포와 cold start UX 확인
12. README에 실제 URL·검증 결과 추가
```

현재 1~4번과 Render/Vercel 설정 파일 작성은 완료됐으며, Supabase 자격증명과 Frontend 신규 Workflow 전환이 남아 있다.

## 외부 참고

- [Vercel Vite React template](https://vercel.com/templates/react/vite-react)
- [Render FastAPI deployment](https://render.com/docs/deploy-fastapi)
- [Render free service limitations](https://render.com/docs/free)
- [Supabase pgvector](https://supabase.com/docs/guides/database/extensions/pgvector)
- [Supabase PostgreSQL connections](https://supabase.com/docs/guides/database/connecting-to-postgres)

## 최종 포트폴리오 메시지

> Azure 구독 만료로 프로젝트가 실행 불가능해지는 문제를 해결하기 위해 LLM·Vector Search·Productivity 계층을 Provider로 분리했습니다. 공개 데모는 Vercel, Render, Supabase, NVIDIA NIM과 Mock Microsoft 365로 안전하게 재현하며, 실제 업무 환경을 위한 Logic Apps와 Microsoft Graph Provider 계약은 별도로 보존하고 테스트합니다.
## 공개 데모 UI 적용 상태 (2026-08-06)

- 공개 화면은 Legacy Azure API를 호출하지 않고 `/api/v1/action-plans` 승인 워크플로를 사용한다.
- Vercel 환경 변수 `VITE_API_URL`에는 `/api`가 아닌 Render 서비스의 전체 HTTPS 주소를 설정한다.
- Render 시작 명령은 Alembic 마이그레이션과 데모 지식 seed를 완료한 뒤 FastAPI를 실행한다.
- 기존 Azure 화면 소스는 과거 구현 설명을 위해 보존하지만 공개 라우터에서는 접근할 수 없다.
