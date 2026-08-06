# Microsoft Graph Productivity Provider

IEUM의 `MicrosoftGraphProductivityProvider`는 기존 `ProductivityProvider` 경계에서 Calendar, Microsoft To Do와 Email 작업을 Microsoft Graph v1.0 요청으로 변환합니다. 구현과 HTTP mock 계약 테스트까지 완료했지만 실제 Microsoft tenant 동의·권한·메일 발송은 검증하지 않았습니다.

## 선택

```env
PRODUCTIVITY_PROVIDER=microsoft_graph
GRAPH_AUTH_MODE=delegated
PRODUCTIVITY_TIMEOUT_SECONDS=10
```

## Delegated 모드

```env
GRAPH_AUTH_MODE=delegated
GRAPH_ACCESS_TOKEN=
GRAPH_TODO_LIST_ID=
```

현재 delegated 모드의 `GRAPH_ACCESS_TOKEN` 입력은 로컬 계약 검증용입니다. refresh token을 저장하거나 자동 교체하지 않으므로 운영 인증 구현이 아닙니다. 운영에서는 Authorization Code 또는 On-Behalf-Of 흐름을 담당하는 별도 token provider와 안전한 cache를 연결해야 합니다.

필요한 최소 delegated permission:

| 기능 | Permission | Endpoint |
|---|---|---|
| Calendar | `Calendars.ReadWrite` | `POST /me/events` |
| To Do | `Tasks.ReadWrite` | `POST /me/todo/lists/{listId}/tasks` |
| Email | `Mail.Send` | `POST /me/sendMail` |

## Application 모드

```env
GRAPH_AUTH_MODE=application
GRAPH_TENANT_ID=
GRAPH_CLIENT_ID=
GRAPH_CLIENT_SECRET=
GRAPH_USER_ID=
```

Client Credentials token provider는 tenant별 token endpoint와 Graph `.default` scope를 사용하며, 만료 60초 전까지 token을 메모리에 cache하고 이후 새 token을 발급받습니다. 프로세스 간 cache 공유나 Secret rotation service는 포함하지 않습니다.

Application permission에서 Calendar와 Email은 대상 `GRAPH_USER_ID`를 명시해야 합니다. To Do task 생성 API는 application permission을 지원하지 않으므로 provider가 `configuration_error`로 차단합니다. 이를 우회하기 위해 과도한 권한이나 다른 API를 사용하지 않습니다.

권장 application permission:

- Calendar: `Calendars.ReadWrite`
- Email: `Mail.Send`
- To Do: 지원하지 않음

`Mail.Send` application permission은 넓은 권한이므로 실제 조직에서는 관리자가 mailbox 범위를 제한하는 정책을 별도로 검토해야 합니다.

## Tenant 분리

- application token URL에 `GRAPH_TENANT_ID`를 사용합니다.
- 대상 mailbox는 `GRAPH_USER_ID`로 명시합니다.
- Provider instance와 token cache를 tenant 간 공유하지 않는 구성이 필요합니다.
- 현재 환경변수 기반 factory는 프로세스당 단일 tenant만 지원합니다.
- 다중 tenant 운영에서는 tenant별 configuration과 token provider registry가 추가로 필요합니다.

## Rate limit과 재시도

Graph가 429를 반환하면 `Retry-After` 초를 `ProductivityRateLimitedError.retry_after_seconds`에 보존합니다. Calendar, To Do와 Email은 쓰기 요청이므로 provider 내부에서 즉시 자동 재시도하지 않습니다. 상위 orchestration이 idempotency와 최신 상태를 확인한 뒤 재시도해야 합니다.

Calendar payload에는 `action_id`를 `transactionId`로 전달합니다. Email의 202 응답은 배달 완료가 아니라 요청 접수이며, 응답의 `request-id`가 있으면 추적 ID로 저장합니다.

## 오류 처리

| HTTP/상황 | Provider error code |
|---|---|
| Token 또는 Graph 401 | `unauthorized` |
| Graph 403 | `authorization_error` |
| Graph 429 | `rate_limited` |
| Graph 4xx | `upstream_4xx` |
| Graph 5xx | `upstream_5xx` |
| timeout | `timeout` |
| network | `network_error` |
| 잘못된 JSON | `invalid_response` |

Graph 오류 body, access token과 client secret은 로그나 API 오류에 포함하지 않습니다.

## 공식 문서

- [Create event](https://learn.microsoft.com/en-us/graph/api/user-post-events?view=graph-rest-1.0)
- [Create To Do task](https://learn.microsoft.com/en-us/graph/api/todotasklist-post-tasks?view=graph-rest-1.0)
- [Send mail](https://learn.microsoft.com/en-us/graph/api/user-sendmail?view=graph-rest-1.0)
- [Microsoft Graph permissions](https://learn.microsoft.com/en-us/graph/permissions-reference)
- [Microsoft Graph throttling guidance](https://learn.microsoft.com/en-us/graph/throttling)

## 현재 제한사항

- 실제 tenant admin consent 미검증
- delegated OAuth authorization/refresh flow 미구현
- client secret vault와 rotation 미구현
- 프로세스 간 token cache 미지원
- national cloud Graph base URL 미지원
- Graph 변경 notification이나 delivery confirmation 미구현
