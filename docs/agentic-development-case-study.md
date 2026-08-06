# IEUM Agentic Coding 의사결정 사례

## LLM 출력을 Tool에 바로 전달하지 않은 이유

가설은 “JSON 응답을 요청하면 그대로 실행 payload로 사용할 수 있다”였습니다. 그러나 LLM 응답은 malformed JSON, schema 불일치와 추가 필드를 만들 수 있습니다. Coding Agent에는 성공 경로보다 잘못된 JSON과 schema mismatch를 먼저 검증하도록 제약했습니다. 최종적으로 Pydantic의 `extra="forbid"` schema로 다시 검증하고, 잘못된 LLM 응답은 502로 변환했습니다. 남은 한계는 모델별 오류 복구 전략이 아직 없다는 점입니다.

## 승인만으로 중복 실행을 막을 수 없었던 이유

처음에는 승인 상태 확인으로 충분하다고 보았지만 반복 클릭이나 동시에 도착한 execute 요청은 둘 다 승인 상태를 읽을 수 있습니다. 이를 테스트 가능한 경쟁 조건으로 분해하고 DB 조건부 update로 한 요청만 실행권을 선점하게 했습니다. 각 작업에는 고유 `action_id`도 적용했습니다. PostgreSQL 통합 테스트에서 동시 요청 중 하나만 실행되고 attempts가 1인 것을 검증했습니다.

## 부분 실패 상태를 만든 이유

Calendar 생성 후 Email 전송이 실패해도 이미 생성된 외부 일정은 DB rollback으로 되돌릴 수 없습니다. 전체 성공/실패만 기록하면 실제 외부 상태를 잃습니다. 따라서 action별 성공, 실패, Resource ID와 error code를 저장하고 계획 상태를 `PARTIALLY_SUCCEEDED`로 계산했습니다. Mock partial-failure 테스트와 Workflow API 테스트로 검증했습니다.

## 로컬 Docker 실패 후 검증 장소를 바꾼 이유

6GB RAM Windows 환경에서 Docker Desktop이 리소스 부족 오류로 시작되지 않았습니다. 검증을 생략하는 대신 PostgreSQL/pgvector service container가 있는 GitHub Actions로 통합 테스트를 이동했습니다. CI에서 2,048차원 vector 저장, 동시 실행 선점과 전체 meeting-to-action 흐름을 검증했습니다. 로컬 Docker 재현은 환경 자원이 충분한 개발자에게 열어 두었습니다.

## Microsoft 자격증명 없이 재현되게 만든 이유

실제 서명 URL과 조직 계정에 테스트가 의존하면 공개 저장소에서 반복 검증할 수 없습니다. LLM, 검색과 생산성 도구를 Provider interface 뒤에 두고 Mock 구현과 HTTP 계약 테스트를 만들었습니다. Logic Apps adapter는 URL 미설정을 성공으로 위장하지 않으며 timeout과 주요 HTTP 오류를 명시적으로 반환합니다. 실제 tenant 권한과 운영 장애 대응은 아직 검증 범위 밖입니다.

## 요청 body의 승인자 이메일을 신뢰하지 않은 이유

클라이언트가 전송한 이메일은 누구나 바꿀 수 있으므로 승인자의 신원을 증명하지 못합니다. API dependency가 `ActorContext`를 주입하도록 도메인 경계를 만들고, 승인에는 `approver`, 실행에는 `executor` 역할을 요구했습니다. Mock 모드에서는 재현 가능한 헤더 identity를 사용하지만 body의 actor는 호환 목적으로만 받고 무시합니다. 위조 이메일과 권한 부족 요청이 상태를 변경하지 않는 것을 API 테스트로 검증했습니다. 실제 Entra ID token의 `oid`, `tid`, `roles` 검증은 아직 구현하지 않았으며 Azure 모드에서는 이를 성공으로 가장하지 않습니다.
