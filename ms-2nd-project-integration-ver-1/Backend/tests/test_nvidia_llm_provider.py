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

    with pytest.raises(LLMProviderError, match="MeetingAnalysis Schema"):
        provider.analyze_meeting("부산 출장을 진행하고 교통편을 예약합니다.")
