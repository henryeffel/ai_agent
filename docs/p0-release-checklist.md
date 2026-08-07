# IEUM P0 Release Checklist

기준일: 2026-08-07

목표는 새로운 Agent 기능을 추가하는 것이 아니라 공개 데모의 RAG 설득력과 첫 실행 신뢰성을 완성하는 것이다.

## 2026-08-07 작업 기록

로컬 구현 결과:

- 기본 회의록을 출장·비용 승인 상황으로 교체했다.
- Demo Seed의 5개 문서를 유지하면서 각 문서에 읽을 수 있는 Markdown 출처명을 추가했다.
- pgvector의 cosine distance를 `1 - distance`로 변환한 값을 `similarity_score`로 명시했다.
- Action Plan에 Evidence 상세를 JSON으로 영속화하는 Alembic revision `20260807_0002`를 추가했다.
- API가 Chunk ID와 함께 문서명, 카테고리, 출처, 본문 발췌와 similarity를 반환한다.
- 프런트엔드가 원시 Chunk ID 대신 간결한 Evidence 카드를 표시한다.
- cold start 안내, 계획 생성 전용 1회 재시도와 요청 중 버튼 잠금을 추가했다.
- 승인·거절·실행 요청에는 자동 재시도를 적용하지 않았다.

검증 결과:

```text
Backend pytest              75 passed, 1 skipped
Python compile              passed
Frontend production build  passed
Alembic head                20260807_0002
git diff --check            passed
```

Skip 1건은 전용 PostgreSQL DB를 지정해야 실행되는 보호된 통합 테스트다. 실제 NVIDIA Top 1~3 검색 결과, Supabase migration과 공개 Workflow E2E는 변경사항 배포 후 검증한다.

## Gate 1 — Demo 품질

- [x] 기존 Seed 문서와 Chunk 내용 확인
- [x] Seed가 하나의 가상 기업 지식베이스를 구성하는지 확인
- [x] 1~2개 규정을 자연스럽게 요구하는 기본 회의록 작성
- [ ] 기본 샘플의 실제 Top 1~3 검색 결과 확인
- [ ] 관련 없는 문서가 상위에 나오면 샘플·Chunk·검색 조건만 최소 조정
- [x] pgvector score가 cosine distance가 아니라 `1 - cosine_distance`인 similarity임을 확인
- [x] API와 UI에서 `similarity_score` 명칭 사용

완료 조건: 검색된 각 문서가 왜 필요한지 사람이 설명할 수 있다.

## Gate 2 — Evidence UX

- [x] Action Plan 응답에 문서명, 카테고리, 출처, 근거 본문과 similarity 포함
- [x] 기존 `evidence_chunk_ids` 하위 호환성 유지
- [x] Chunk ID 문자열을 간결한 근거 카드로 교체
- [x] 긴 본문과 근거 없음 상태 처리
- [x] PDF viewer, highlighting, accordion 등 범위 제외

완료 조건: Chunk ID를 몰라도 근거의 출처와 내용을 3초 안에 이해할 수 있다.

## Gate 3 — Demo reliability

- [x] Render cold start 안내 표시
- [x] 계획 생성의 `retryable=true`인 502/503만 최대 1회 자동 재시도
- [x] 재시도 상태 표시
- [x] 요청 진행 중 관련 버튼 잠금
- [x] 승인·거절·실행 자동 재시도 금지
- [x] 사용자가 취할 행동을 포함한 오류 메시지 표시
- [ ] 제한적 재시도 정책 회귀 테스트

완료 조건: 첫 요청이 지연되거나 일시 실패해도 사용자가 현재 상태와 다음 행동을 이해할 수 있다.

## Gate 4 — Release

- [x] Backend 전체 테스트
- [x] PostgreSQL·pgvector 통합 테스트 또는 CI 결과 확인
- [x] Frontend production build
- [x] 공개 환경 readiness 확인
- [ ] 공개 URL에서 전체 Agent Workflow 검증
- [x] 근거 카드와 재시도 UX 확인
- [x] README의 기능·테스트 수치·제한사항 갱신
- [x] 배포 검증 문서에 최종 E2E 결과 기록
- [ ] P0 완료 시 feature freeze 선언

완료 조건:

```text
회의록
→ 사람이 이해할 수 있는 근거
→ Action Plan
→ PENDING_APPROVAL
→ APPROVED
→ SUCCEEDED
```

## Feature freeze

Gate 4 완료 이후에는 버그 수정과 문서 수정 외 기능을 추가하지 않는다. Entra ID, 실제 Graph tenant, OAuth token rotation, OpenTelemetry, Scheduler와 code splitting은 제출 후 범위로 유지한다.

### 2026-08-07 배포 후 상태

- PR #6을 `main`에 병합했다. 병합 커밋은 `cc43b33`이다.
- main Backend CI에서 SQLite/mock, PostgreSQL·pgvector 통합 테스트와 Docker 이미지 빌드가 통과했다.
- Vercel Production 배포가 성공했다.
- Render readiness와 OpenAPI의 `EvidenceDetail` 배포를 확인했다.
- 공개 계획 생성은 최초 요청과 허용된 1회 재시도 모두 NVIDIA upstream `502`로 실패했다.
- 계획이 생성되지 않았으므로 승인·실행 API는 호출하지 않았다.
- 실제 Top 1~3와 전체 공개 E2E가 완료되지 않아 feature freeze는 선언하지 않는다.
