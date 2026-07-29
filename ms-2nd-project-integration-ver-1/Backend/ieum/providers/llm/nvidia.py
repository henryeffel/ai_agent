import json
import os
import re

from openai import OpenAI
from pydantic import TypeAdapter, ValidationError

from ieum.providers.llm.base import LLMProvider
from ieum.schemas.action_plan import ActionCreate
from ieum.schemas.knowledge import KnowledgeSearchHit
from ieum.schemas.meeting import MeetingAnalysis


class LLMProviderError(RuntimeError):
    """Raised when an LLM response cannot be used safely."""


class NvidiaLLMProvider(LLMProvider):
    def __init__(self):
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY 환경변수가 필요합니다.")

        self._model_name = os.getenv(
            "NVIDIA_LLM_MODEL",
            "nvidia/nemotron-3-super-120b-a12b",
        )
        self._client = OpenAI(
            base_url=os.getenv(
                "NVIDIA_BASE_URL",
                "https://integrate.api.nvidia.com/v1",
            ),
            api_key=api_key,
            timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
            max_retries=1,
        )

    @property
    def provider_name(self) -> str:
        return "nvidia"

    @property
    def model_name(self) -> str:
        return self._model_name

    def analyze_meeting(self, transcript: str) -> MeetingAnalysis:
        response = self._client.chat.completions.create(
            model=self._model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 업무 회의 분석기입니다. 제공된 Transcript에 근거한 "
                        "JSON 객체만 반환하세요. 추측하지 말고 알 수 없는 담당자와 "
                        "기한은 null로 반환하세요."
                    ),
                },
                {
                    "role": "user",
                    "content": self._build_prompt(transcript),
                },
            ],
            temperature=0.1,
            top_p=0.9,
            max_tokens=2048,
            stream=False,
        )

        content = response.choices[0].message.content
        if not content:
            raise LLMProviderError("LLM이 분석 결과를 반환하지 않았습니다.")

        try:
            payload = json.loads(self._strip_code_fence(content))
            return MeetingAnalysis.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMProviderError(
                "LLM 응답이 MeetingAnalysis Schema를 충족하지 않습니다."
            ) from exc

    def generate_grounded_actions(
        self,
        analysis: MeetingAnalysis,
        evidence: list[KnowledgeSearchHit],
    ) -> list[ActionCreate]:
        if not evidence:
            return []
        response = self._client.chat.completions.create(
            model=self._model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 근거 기반 업무 실행 계획 생성기입니다. 회의 분석과 "
                        "검색 근거에 모두 뒷받침되는 작업만 생성하세요. 근거에 없는 "
                        "수신자, 참석자, 날짜를 만들지 마세요. JSON 배열만 반환하세요."
                    ),
                },
                {
                    "role": "user",
                    "content": self._build_action_prompt(analysis, evidence),
                },
            ],
            temperature=0.1,
            top_p=0.9,
            max_tokens=2048,
            stream=False,
        )
        content = response.choices[0].message.content
        if not content:
            raise LLMProviderError("LLM이 실행 계획을 반환하지 않았습니다.")
        try:
            payload = json.loads(self._strip_code_fence(content))
            return TypeAdapter(list[ActionCreate]).validate_python(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMProviderError(
                "LLM 응답이 Action Plan Schema를 충족하지 않습니다."
            ) from exc

    @staticmethod
    def _strip_code_fence(content: str) -> str:
        stripped = content.strip()
        match = re.fullmatch(
            r"```(?:json)?\s*(.*?)\s*```",
            stripped,
            flags=re.DOTALL | re.IGNORECASE,
        )
        return match.group(1) if match else stripped

    @staticmethod
    def _build_prompt(transcript: str) -> str:
        return f"""
다음 회의 Transcript를 분석해 아래 JSON Schema와 정확히 일치하는 객체를 반환하세요.

{{
  "summary": "회의 핵심 요약",
  "decisions": ["확정된 결정사항"],
  "action_items": [
    {{
      "task": "실행할 작업",
      "assignee": "담당자 또는 null",
      "due_date": "YYYY-MM-DD 또는 null"
    }}
  ],
  "open_issues": ["결론이 나지 않은 안건"]
}}

규칙:
- Transcript에 없는 사실을 만들지 마세요.
- 결정사항과 미해결 안건을 구분하세요.
- 날짜가 명확하지 않으면 due_date는 null입니다.
- JSON 이외의 설명이나 Markdown을 출력하지 마세요.

[Transcript]
{transcript}
""".strip()

    @staticmethod
    def _build_action_prompt(
        analysis: MeetingAnalysis,
        evidence: list[KnowledgeSearchHit],
    ) -> str:
        evidence_payload = [
            {
                "chunk_id": hit.chunk_id,
                "title": hit.title,
                "content": hit.content,
                "score": hit.score,
            }
            for hit in evidence
        ]
        return f"""
다음 회의 분석과 검색 근거로 실행 가능한 작업을 만드세요.

[회의 분석]
{analysis.model_dump_json()}

[검색 근거]
{json.dumps(evidence_payload, ensure_ascii=False)}

아래 형태의 JSON 배열만 반환하세요.
[
  {{
    "action_id": "고유한 문자열",
    "payload": {{
      "tool": "todo",
      "title": "할 일",
      "due_at": "ISO 8601 날짜시간 또는 null",
      "description": "근거 chunk_id를 포함한 설명"
    }}
  }}
]

규칙:
- calendar는 시작과 종료 시각이 근거에 명시된 경우에만 허용합니다.
- email은 수신자 이메일이 근거에 명시된 경우에만 허용합니다.
- 정보가 불충분하면 안전한 todo를 사용하세요.
- 회의 분석과 검색 근거 양쪽에서 확인되지 않는 작업은 만들지 마세요.
- 최소 1개, 최대 50개의 작업만 반환하세요.
""".strip()
