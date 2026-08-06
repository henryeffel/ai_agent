# IEUM 구현 진행 기록

## 공개 배포 완료 (2026-08-06)

- [x] Supabase PostgreSQL + pgvector migration 및 Demo seed
- [x] Render FastAPI 배포: `https://ieum-api-sgqw.onrender.com`
- [x] Vercel React 배포: `https://ai-agent-olive-nine.vercel.app`
- [x] Production CORS 검증
- [x] 공개 API Plan 생성 → 승인 → Mock 실행 검증
- [x] 최종 Backend 테스트 `75 passed, 1 skipped`

상세 장애 원인과 최종 검증 결과는 [`deployment-verification.md`](./deployment-verification.md)에 기록했다.

기준일: 2026-08-06

## Baseline

- 기준 코드: `ms-2nd-project-integration-ver-1`
- Mock 비통합 테스트: `23 passed`, 경고 1개
- `python -m compileall -q ieum main.py`: 통과
- 발견 사항: Mock 모드에서도 Legacy Azure 라우트 9개가 등록됨
- 알려진 경고: FastAPI TestClient가 `httpx` 호환 계층 deprecation 경고를 출력함

## P0 적용 결과

- [x] 루트 README와 CI badge 추가
- [x] `main.py`를 app 조립 책임으로 축소
- [x] health, meetings, knowledge, action plan router 분리
- [x] Mock 모드에서 Legacy Azure router import 및 라우트 등록 차단
- [x] React 호환 `/analyze-meeting` 유지
- [x] 앱 모드 회귀 테스트 추가
- [x] Logic Apps Productivity Provider 추가
- [x] URL 누락·timeout·HTTP 오류·잘못된 응답 계약 테스트
- [x] Agentic Coding 사례 문서 추가
- [x] 재현 가능한 데모 문서 추가

## 검증 결과

- Mock 비통합 테스트: `34 passed`, 경고 1개
- Python compile: 통과
- PostgreSQL/pgvector: 기존 CI 검증 유지, 이번 로컬 실행은 별도 DB가 없어 수행하지 않음

## 후속 작업

- Legacy application 내부를 순수 APIRouter로 한 번 더 축소

## P1-1 인증·권한 경계

- [x] `ActorContext` 도메인 모델 추가
- [x] 요청 body의 actor를 감사 identity로 사용하지 않음
- [x] Mock 모드 헤더 identity dependency 추가
- [x] 승인·거절에 `approver` 역할 적용
- [x] 실행에 `executor` 역할 적용
- [x] 위조 body actor와 역할 부족 회귀 테스트 추가
- [ ] 실제 Entra ID access token 검증

검증 결과: Mock 비통합 테스트 `37 passed`, 경고 1개. Entra ID가 없는 Azure 모드의 신규 Workflow identity dependency는 성공을 위장하지 않고 501을 반환한다.

## P1-2 RAG 전처리와 평가

- [x] 제목·문단 경계를 우선하는 chunker 추가
- [x] source, category, title, section, created/updated metadata 전달
- [x] 정규화된 완전 중복 Chunk 제거
- [x] UTF-8 Text/Markdown loader 추가
- [x] 10개 문서·20개 질문 평가셋 추가
- [x] Baseline·Improved 평가 스크립트와 결과 JSON 생성
- [x] Recall@3, Evidence Hit Rate, Grounded Decision Accuracy, 근거 부족 거부율과 latency 기록
- [x] Baseline 실패 5건 및 대표 실패 사례 3건 기록

현재 평가에서는 두 pipeline 모두 Recall@3 1.00이었지만 Baseline의 근거 부족 거부율은 0.00, Improved는 1.00이었다. 이는 category와 lexical threshold 효과를 확인하는 합성 평가일 뿐 embedding 모델의 운영 품질로 일반화하지 않는다.

P1-2 적용 후 Mock 비통합 테스트는 `40 passed`, PostgreSQL 통합 테스트는 로컬 DB 미설정으로 `1 skipped`, Python compile과 평가 스크립트 재실행은 통과했다.

## P1-3 Alembic migration

- [x] Alembic 설정과 초기 revision 추가
- [x] Action Plan, Action Execution, Knowledge Chunk schema migration 작성
- [x] PostgreSQL에서 pgvector extension과 `vector(2048)` column 생성
- [x] SQLite 검증에서는 embedding을 JSON column으로 대체
- [x] 요청 처리 중 `create_all()` 제거
- [x] Docker Compose가 Backend 시작 전에 `alembic upgrade head` 실행
- [x] 테스트 fixture가 migration으로 schema 준비
- [x] SQLite upgrade → downgrade → upgrade 자동 테스트 추가

로컬 SQLite에서 revision `20260806_0001 (head)`의 upgrade → downgrade → upgrade가 통과했다. PostgreSQL migration은 CI service container에서 통합 테스트 fixture가 실행하도록 변경했으며 현재 로컬에는 PostgreSQL DB가 없어 별도 실행하지 않았다.

P1-3 적용 후 비통합 테스트는 `41 passed`, PostgreSQL 통합 테스트는 로컬 DB 미설정으로 `1 skipped`, Python compile과 Secret 패턴 검사는 통과했다.

## P1-4 구조화 로그와 실행 추적

- [x] ContextVar 기반 request ID 전파
- [x] `X-Request-ID` 입력 지원 및 응답 헤더 반환
- [x] JSON formatter와 field allowlist 구현
- [x] Action 실행 시작·완료·실패 로그 구현
- [x] plan, action, meeting, provider, tool, status, latency, error code 기록
- [x] transcript, payload, Secret와 이메일 원문 비노출 테스트
- [x] 이메일 masking utility 추가
- [x] Alembic 실행 후 기존 애플리케이션 로거가 비활성화되지 않도록 수정

관리자 알림, OpenTelemetry와 Prometheus는 선택적 후속 범위로 남겼다. P1-4 적용 후 비통합 테스트는 `47 passed`, PostgreSQL 통합 테스트는 로컬 DB 미설정으로 `1 skipped`, Python compile·diff·Secret 패턴 검사는 통과했다.

## P2-1 Copilot Studio 연동 준비

- [x] 권장 5개 API에 안정적인 operation ID와 설명 추가
- [x] 승인과 실행 operation 책임 분리 명시
- [x] 공통 `{error:{code,message,retryable,details}}` 응답 schema 적용
- [x] validation error의 field 위치와 type을 안전하게 반환
- [x] connector 전용 `/openapi/copilot.json` 제공
- [x] schema 경로·operation ID·오류 `$ref` 회귀 테스트 추가
- [x] Custom Connector 연결 절차와 Entra ID 미구현 제한 문서화

실제 Copilot Studio tenant 연결은 수행하지 않았으며 connector용 계약과 검증 가능한 OpenAPI 준비까지만 완료했다.

P2-1 적용 후 비통합 테스트는 `51 passed`, PostgreSQL 통합 테스트는 로컬 DB 미설정으로 `1 skipped`, Python compile·diff·Secret 패턴 검사는 통과했다.

## P2-2 Microsoft Graph Provider

- [x] `MicrosoftGraphProductivityProvider` 추가
- [x] Calendar·To Do·Email Graph v1.0 payload 변환
- [x] delegated `/me`와 application `/users/{id}` 경로 분리
- [x] Client Credentials token provider와 메모리 만료 cache 구현
- [x] delegated development token provider 경계 구현
- [x] application mode에서 지원되지 않는 To Do 실행 차단
- [x] 429 `Retry-After` 보존 및 자동 쓰기 재시도 방지
- [x] 401·403·4xx·5xx·timeout·network 오류 sanitization
- [x] factory와 환경변수 연결
- [x] 최소 권한, tenant 분리, cache·rotation 한계 문서화

실제 tenant 자격증명 없이 HTTP mock 계약만 검증했다. delegated refresh flow, admin consent, mailbox scope 정책과 실제 전송 결과는 미검증 상태다.

P2-2 적용 후 비통합 테스트는 `60 passed`, PostgreSQL 통합 테스트는 로컬 DB 미설정으로 `1 skipped`, Python compile·diff·Secret 패턴 검사는 통과했다.

## 공개 배포 방향 변경

Azure 구독 만료로 Azure 중심 공개 배포 계획을 폐기하고 다음 구조를 목표로 결정했다.

```text
Vercel Frontend
→ Render FastAPI
→ Supabase PostgreSQL + pgvector
→ NVIDIA NIM
→ Mock Microsoft 365
```

Logic Apps와 Microsoft Graph Provider는 코드와 계약 테스트로 보존하되 공개 데모에서는 외부 부작용을 막기 위해 비활성화한다. 다음 구현 우선순위는 SharePoint Provider가 아니라 `APP_MODE=demo`, 공개 Knowledge 색인 보호와 Supabase PostgreSQL 통합 검증이다. 상세 내용은 `docs/open-demo-deployment-plan.md`를 따른다.

## 공개 Demo 모드 안전장치

- [x] `APP_MODE=demo` 추가
- [x] NVIDIA LLM·Embedding + pgvector + Mock Productivity 조합 강제
- [x] PostgreSQL DATABASE_URL 강제
- [x] Demo 모드 Legacy Azure Router 미등록 검증
- [x] Logic Apps와 Microsoft Graph Provider 선택 시 startup 실패
- [x] 공개 Knowledge 색인 API를 `demo_write_disabled` 403으로 차단
- [x] 사용자 제공 identity 헤더 대신 고정 Demo actor 사용

다음 단계는 외부 API가 아닌 배포용 seed command와 Demo 데이터 정리 정책을 구현한 뒤 Supabase PostgreSQL에서 migration과 통합 테스트를 실행하는 것이다.

Demo 안전장치 적용 후 비통합 테스트는 `65 passed`, PostgreSQL 통합 테스트는 로컬 DB 미설정으로 `1 skipped`, Python compile·diff·Secret 패턴 검사는 통과했다.

## Demo seed와 만료 데이터 정리

- [x] 5개 샘플 규정·10개 고정 Chunk seed 데이터 추가
- [x] 외부 API가 아닌 `python -m ieum.demo seed` CLI 제공
- [x] 고정 Chunk ID 기반 idempotent upsert 테스트
- [x] Demo API가 생성하는 meeting ID에 `demo-` scope 적용
- [x] `python -m ieum.demo cleanup --older-than-hours 24 --confirm` 추가
- [x] `--confirm` 없는 삭제 차단
- [x] 오래된 `demo-` Plan과 관련 Action만 삭제하는 범위 테스트
- [x] 최근 Demo Plan과 비 Demo 데이터 보존 테스트

Seed는 Render 시작 때마다 실행하지 않고 Supabase 연결이 가능한 승인된 운영자 환경에서 배포 전 한 번 실행한다. Cleanup은 초기에는 수동으로 실행하고 scheduler 추가 시 별도 Secret과 최소 권한을 검토한다.

Demo maintenance 적용 후 비통합 테스트는 `67 passed`, PostgreSQL 통합 테스트는 로컬 DB 미설정으로 `1 skipped`, Python compile·diff·Secret 패턴 검사는 통과했다.

## Supabase·Render·Vercel 배포 준비

- [x] Docker를 사용할 수 없는 로컬 환경 제약 기록
- [x] Render Docker Blueprint와 Demo 환경변수 placeholder 추가
- [x] Render 동적 `$PORT`, Alembic migration과 health check 구성
- [x] Vercel Vite build와 BrowserRouter SPA rewrite 설정
- [x] Supabase 전용 DB 검증 스크립트 추가
- [x] 통합 테스트에 `IEUM_INTEGRATION_DATABASE=1` 안전장치 추가
- [x] Vite production build 통과
- [x] Backend 비통합 테스트 `67 passed`
- [ ] Supabase DATABASE_URL 입력
- [ ] Supabase Alembic 왕복과 통합 테스트 실행
- [ ] Frontend Legacy endpoint 의존성을 신규 Workflow API로 전환

현재 PostgreSQL 통합 테스트는 연결 정보가 없어 `1 skipped` 상태다. 이는 Supabase 전용 DB 준비 후 `scripts/verify_supabase.py --confirm-empty-database`로 해소한다. Frontend build는 통과했지만 일부 화면이 Demo 모드에서 제공하지 않는 Legacy Azure API를 호출하므로 실제 공개 배포 전에 UI migration이 필요하다.

배포 설정 회귀 테스트 추가 후 비통합 테스트는 `70 passed`, PostgreSQL 통합 테스트는 `1 skipped`다. Vite production build는 통과했으며 1.16MB main chunk에 대한 code-splitting 경고가 남아 있다.
## 공개 데모 프런트엔드 전환 (2026-08-06)

- `/home`을 신규 `/api/v1/action-plans` 기반 Agent Workflow 화면으로 교체했다.
- 회의록 입력 → RAG 근거 검색 → Action Plan 생성 → 사용자 승인 → Mock Microsoft 365 실행을 한 화면에서 확인할 수 있다.
- Legacy Azure 화면은 소스 호환성을 위해 남겨두되 공개 데모 라우팅과 번들 진입점에서는 제외했다.
- Render 시작 시 마이그레이션 후 데모 지식을 멱등하게 적재한다.
- Vercel에는 `VITE_API_URL=https://<render-service>.onrender.com` 환경 변수가 필요하다.
- 검증 결과: 프런트엔드 프로덕션 빌드 성공, 백엔드 `70 passed, 1 skipped`.
