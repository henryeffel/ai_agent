from types import SimpleNamespace

import pytest

from ieum.providers.llm.nvidia import LLMProviderError, NvidiaLLMProvider


class FakeCompletions:
    def __init__(self, content):
        self.content = content

    def create(self, **kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


def _provider_with_response(content):
    provider = NvidiaLLMProvider.__new__(NvidiaLLMProvider)
    provider._model_name = "test-model"
    provider._client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions(content))
    )
    return provider


def test_analysis_accepts_json_after_reasoning_wrapper():
    provider = _provider_with_response(
        "<think>회의 내용을 구조화합니다.</think>\n"
        '{"summary":"출장 결정","decisions":["부산 출장"],'
        '"action_items":[{"task":"교통편 예약","assignee":null,'
        '"due_date":null}],"open_issues":[]}'
    )

    result = provider.analyze_meeting("부산 출장을 진행하고 교통편을 예약합니다.")

    assert result.summary == "출장 결정"
    assert result.action_items[0].task == "교통편 예약"


def test_analysis_rejects_response_without_valid_json_object():
    provider = _provider_with_response("구조화 결과를 만들 수 없습니다.")

    with pytest.raises(LLMProviderError, match="JSON 객체를 찾지 못했습니다"):
        provider.analyze_meeting("부산 출장을 진행하고 교통편을 예약합니다.")


def test_analysis_reports_only_safe_validation_locations():
    provider = _provider_with_response(
        '{"summary":"출장 결정","decisions":[],"action_items":[],'
        '"open_issues":[],"secret_payload":"do-not-echo"}'
    )

    with pytest.raises(LLMProviderError) as caught:
        provider.analyze_meeting("부산 출장을 진행하고 교통편을 예약합니다.")

    assert "secret_payload:extra_forbidden" in str(caught.value)
    assert "do-not-echo" not in str(caught.value)


def test_analysis_uses_grounded_transcript_when_summary_is_empty():
    transcript = "부산 출장을 진행하고 교통편을 금요일까지 예약합니다."
    provider = _provider_with_response(
        '{"summary":"","decisions":["부산 출장"],'
        '"action_items":[],"open_issues":[]}'
    )

    result = provider.analyze_meeting(transcript)

    assert result.summary == transcript
