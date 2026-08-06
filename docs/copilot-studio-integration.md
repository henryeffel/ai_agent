# Copilot Studio / Custom Connector 연동 준비

이 문서는 IEUM API를 Copilot Studio Action 또는 Power Platform Custom Connector에 연결하기 위한 계약을 설명합니다. 저장소에는 실제 Copilot Studio 환경, Microsoft tenant 연결 또는 Entra ID 인증 구현이 포함되어 있지 않습니다.

## Connector용 OpenAPI

실행 중인 Backend에서 다음 schema를 가져옵니다.

```text
GET /openapi/copilot.json
```

전체 FastAPI schema와 달리 connector에 노출할 5개 작업만 포함합니다.

| Operation ID | Method와 경로 | 책임 |
|---|---|---|
| `analyzeMeeting` | `POST /api/v1/meetings/analyze` | Transcript를 구조화하며 외부 Tool은 실행하지 않음 |
| `createGroundedActionPlan` | `POST /api/v1/action-plans/grounded` | 조직 지식 근거가 있는 승인 대기 Plan 생성 |
| `getActionPlan` | `GET /api/v1/action-plans/{plan_id}` | 상태와 Action별 결과 조회 |
| `approveActionPlan` | `POST /api/v1/action-plans/{plan_id}/approve` | Human approval gate 통과, 실행하지 않음 |
| `executeApprovedActionPlan` | `POST /api/v1/action-plans/{plan_id}/execute` | 승인된 Plan만 외부 Tool로 실행 |

Copilot instruction에서는 `approveActionPlan`의 성공이 Tool 실행 성공을 의미하지 않는다고 명시해야 합니다. 승인 후 사용자의 별도 실행 의사가 확인됐을 때만 `executeApprovedActionPlan`을 호출합니다.

## 연결 절차

1. IEUM Backend를 Power Platform에서 접근 가능한 HTTPS endpoint에 배포합니다.
2. `/openapi/copilot.json` 응답을 파일로 저장하거나 connector import URL로 사용합니다.
3. 환경에 맞는 host와 server URL을 확인합니다.
4. 다섯 operation의 표시 이름과 설명이 import됐는지 확인합니다.
5. 인증 정책을 구성한 뒤 연결을 생성합니다.
6. Mock 환경에서 analyze → grounded plan → get → approve → execute 순서를 검증합니다.
7. 승인 전 execute, 권한 부족, 근거 부족과 중복 execute 오류도 검증합니다.

Power Platform UI와 지원 OpenAPI 버전은 변경될 수 있으므로 실제 tenant의 connector import 화면에서 schema 호환성을 다시 확인해야 합니다.

## Identity와 보안

Mock 모드는 다음 테스트 헤더를 사용합니다.

```text
X-Actor-Id
X-Actor-Email
X-Actor-Roles: approver,executor
```

이 헤더는 개발 재현용이며 운영 인증 수단이 아닙니다. 실제 배포에서는 connector 사용자가 임의 역할 헤더를 만들 수 없도록 제거하고, Entra ID access token의 `oid`, `tid`, `roles` claim을 서버에서 검증해야 합니다. 현재 Azure 모드의 신규 Workflow API는 Entra ID 검증이 없으므로 운영 연결 준비가 완료된 상태가 아닙니다.

`X-Request-ID`를 전달하면 응답과 Action JSON log에서 같은 값을 확인할 수 있습니다. Secret, transcript 전문과 Action payload는 audit log에 남지 않습니다.

## 오류 계약

모든 신규 API 오류는 다음 envelope를 사용합니다.

```json
{
  "error": {
    "code": "insufficient_evidence",
    "message": "실행 계획을 뒷받침할 조직 문서 근거가 부족합니다.",
    "retryable": false,
    "details": {}
  }
}
```

주요 오류 code:

| Code | 의미 | 권장 처리 |
|---|---|---|
| `validation_error` | 입력 schema 오류 | 사용자에게 입력 보완 요청 |
| `insufficient_evidence` | 조직 문서 근거 부족 | 실행하지 않고 추가 정보 요청 |
| `plan_not_found` | Plan ID 없음 | Plan 생성 또는 ID 재확인 |
| `authorization_error` | 역할 부족 | 실행하지 않고 권한 안내 |
| `invalid_state_transition` | 미승인·거절·중복 실행 | 최신 Plan 상태 조회 |
| `duplicate_action` | 이미 존재하는 Action ID | 새 요청인지 중복인지 확인 |
| `llm_invalid_response` | LLM upstream/응답 오류 | `retryable` 확인 후 제한적 재시도 |

Connector나 Copilot instruction은 알 수 없는 오류를 성공으로 해석해서는 안 됩니다.

## 권장 Agent 흐름

```text
Transcript 수신
→ analyzeMeeting
→ createGroundedActionPlan
→ 결과와 근거를 사용자에게 표시
→ 명시적 승인 확인
→ approveActionPlan
→ 명시적 실행 확인
→ executeApprovedActionPlan
→ getActionPlan으로 최종 상태와 부분 실패 확인
```

## 현재 제한사항

- 실제 Copilot Studio tenant import 미검증
- Entra ID token 검증 미구현
- Custom Connector 인증 설정 미제공
- Logic Apps URL과 Microsoft 권한은 사용자 환경에서 별도 제공 필요
- OpenAPI는 FastAPI가 생성하는 3.x schema이며 tenant별 import 호환성 재확인 필요
