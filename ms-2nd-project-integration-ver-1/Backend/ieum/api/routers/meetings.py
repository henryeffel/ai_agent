from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ieum.providers.llm import get_llm_provider
from ieum.providers.llm.nvidia import LLMProviderError
from ieum.schemas.meeting import MeetingAnalysisRequest, MeetingAnalysisResponse
from ieum.api.errors import ApiException, ERROR_RESPONSES


router = APIRouter(tags=["meetings"])


class MeetingSummaryData(BaseModel):
    summary_text: str


@router.post(
    "/api/v1/meetings/analyze",
    response_model=MeetingAnalysisResponse,
    operation_id="analyzeMeeting",
    summary="Analyze a meeting transcript",
    description="Validate and convert a transcript into summary, decisions, action items, and open issues. This operation does not execute external tools.",
    responses=ERROR_RESPONSES,
)
def analyze_meeting_v1(request: MeetingAnalysisRequest):
    provider = get_llm_provider()
    try:
        analysis = provider.analyze_meeting(request.transcript)
    except LLMProviderError as exc:
        raise ApiException(
            502, "llm_invalid_response", str(exc), retryable=True
        ) from exc
    return MeetingAnalysisResponse(
        provider=provider.provider_name,
        model=provider.model_name,
        data=analysis,
    )


@router.post("/analyze-meeting")
async def analyze_meeting(request: MeetingSummaryData):
    if not request.summary_text.strip():
        raise HTTPException(status_code=400, detail="텍스트가 비어있습니다.")
    provider = get_llm_provider()
    try:
        analysis = provider.analyze_meeting(request.summary_text)
    except LLMProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "status": "success",
        "provider": provider.provider_name,
        "model": provider.model_name,
        "data": {
            "summary": analysis.summary,
            "decisions": analysis.decisions,
            "actionItems": [
                {
                    "task": item.task,
                    "assignee": item.assignee,
                    "deadline": item.due_date.isoformat() if item.due_date else None,
                }
                for item in analysis.action_items
            ],
            "openIssues": analysis.open_issues,
        },
    }
