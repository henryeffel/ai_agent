# IEUM 재현 가능한 데모

이 데모는 Microsoft 365 자격증명 없이 안전한 meeting-to-action 흐름을 검증합니다.

## 준비

```powershell
cd ms-2nd-project-integration-ver-1/Backend
$env:APP_MODE="mock"
$env:LLM_PROVIDER="mock"
$env:VECTOR_SEARCH_PROVIDER="mock"
$env:PRODUCTIVITY_PROVIDER="mock"
$env:MOCK_PRODUCTIVITY_SCENARIO="success"
uvicorn main:app --reload
```

## 시나리오

1. `POST /api/v1/knowledge/chunks`로 출장비 또는 회의실 규정 Chunk를 등록합니다.
2. `POST /api/v1/meetings/analyze`로 회의 Transcript를 구조화합니다.
3. `POST /api/v1/action-plans/grounded`로 근거 기반 계획을 생성합니다.
4. 승인 전에 execute를 호출해 `409` 응답을 확인합니다.
5. approve API로 계획을 승인합니다.
6. execute API를 호출하고 `SUCCEEDED`, `attempts=1`, Mock Resource ID를 확인합니다.
7. 같은 계획을 다시 실행해 중복 실행이 차단되는지 확인합니다.

부분 실패는 새 계획을 만든 뒤 다음 값을 설정하여 재현합니다.

```powershell
$env:MOCK_PRODUCTIVITY_SCENARIO="partial_failure"
```

Calendar 작업은 성공하고 Email 작업은 실패하도록 계획을 구성하면 최종 상태가 `PARTIALLY_SUCCEEDED`가 됩니다. 자동화된 동일 시나리오는 `Backend/tests/test_action_workflow_api.py`와 `Backend/tests/integration/test_postgres_workflow.py`에서 확인할 수 있습니다.
