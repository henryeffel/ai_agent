from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os, shutil, uuid
from datetime import timedelta, datetime
import requests
from typing import List
from dotenv import load_dotenv
from ieum.providers.llm import get_llm_provider
from ieum.providers.llm.nvidia import LLMProviderError
from ieum.providers.productivity import get_productivity_provider
from ieum.providers.vector_search import get_vector_search_provider
from ieum.repositories.action_plan import (
    ActionPlanNotFoundError,
    DuplicateActionIdError,
    InvalidStateTransitionError,
)
from ieum.schemas.action_plan import (
    ActionPlanCreate,
    ActionPlanDecision,
    ActionPlanResponse,
    GroundedActionPlanCreate,
)
from ieum.schemas.meeting import MeetingAnalysisRequest, MeetingAnalysisResponse
from ieum.schemas.knowledge import (
    ChunkIndexRequest,
    ChunkIndexResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from ieum.services.action_workflow import (
    InsufficientEvidenceError,
    get_action_workflow_service,
)

load_dotenv()

APP_MODE = os.getenv("APP_MODE", "mock").lower()
if APP_MODE not in {"mock", "azure"}:
    raise RuntimeError("APP_MODE는 'mock' 또는 'azure'여야 합니다.")

# Legacy Azure 모듈은 Azure 모드에서만 초기화한다. 이를 통해 자격증명이
# 없는 환경에서도 Mock 모드로 API와 health check를 실행할 수 있다.
if APP_MODE == "azure":
    from upload_pipeline import upload_file_to_rag, search_client, blob_service_client
    from rag_engine import ask_bot, analyze_meeting_script
    from delete_manager import delete_file_and_index
    from meeting_doc_generator import (
        extract_text_with_coordinates,
        get_coordinates_json_from_llm,
        update_docx_by_coordinates,
    )
    import outlook_service
    from llm_agent import process_chat_request

app = FastAPI()

# ==========================================
# 1. CORS 설정 (프론트엔드 포트 허용)
# ==========================================
origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:5174",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 2. 데이터 모델 정의
# ==========================================
class ChatRequest(BaseModel):
    message: str
    category: Optional[str] = "history"

class DeleteRequest(BaseModel):
    filename: str
    category: str

class MeetingSummaryData(BaseModel):
    summary_text: str

class CalendarRequest(BaseModel):
    title: str
    date: str
    time: str
    attendees: List[str]

class TodoRequest(BaseModel):
    title: str
    content: Optional[str] = None
    due_date: Optional[str] = None

# 환경 변수 및 상수 설정
LOGIC_APP_URL_MAIL = os.getenv("LOGIC_APP_URL_MAIL")
TEAM_MEMBERS = [
    email.strip()
    for email in os.getenv("TEAM_MEMBER_EMAILS", "").split(",")
    if email.strip()
]

# ==========================================
# 3. API 엔드포인트
# ==========================================
@app.get("/")
def read_root():
    return {"status": "Backend is running", "mode": APP_MODE}


@app.get("/health/live")
def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready():
    llm_provider = get_llm_provider()
    productivity_provider = get_productivity_provider()
    vector_search_provider = get_vector_search_provider()
    return {
        "status": "ready",
        "mode": APP_MODE,
        "llm_provider": llm_provider.provider_name,
        "llm_model": llm_provider.model_name,
        "productivity_provider": productivity_provider.provider_name,
        "vector_search_provider": vector_search_provider.provider_name,
        "azure_providers_loaded": APP_MODE == "azure",
    }


@app.post(
    "/api/v1/meetings/analyze",
    response_model=MeetingAnalysisResponse,
)
def analyze_meeting_v1(request: MeetingAnalysisRequest):
    provider = get_llm_provider()
    try:
        analysis = provider.analyze_meeting(request.transcript)
    except LLMProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return MeetingAnalysisResponse(
        provider=provider.provider_name,
        model=provider.model_name,
        data=analysis,
    )


@app.post(
    "/api/v1/knowledge/chunks",
    response_model=ChunkIndexResponse,
    status_code=201,
)
def index_knowledge_chunks(request: ChunkIndexRequest):
    provider = get_vector_search_provider()
    indexed_count = provider.index_chunks(request.chunks)
    return ChunkIndexResponse(
        indexed_count=indexed_count,
        provider=provider.provider_name,
    )


@app.post(
    "/api/v1/knowledge/search",
    response_model=KnowledgeSearchResponse,
)
def search_knowledge(request: KnowledgeSearchRequest):
    provider = get_vector_search_provider()
    hits = provider.search(
        request.query,
        category=request.category,
        top_k=request.top_k,
        min_score=request.min_score,
    )
    return KnowledgeSearchResponse(
        provider=provider.provider_name,
        grounded=bool(hits),
        hits=hits,
    )


@app.post(
    "/api/v1/action-plans",
    response_model=ActionPlanResponse,
    status_code=201,
)
def create_action_plan(request: ActionPlanCreate):
    try:
        return get_action_workflow_service().create_plan(request)
    except DuplicateActionIdError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post(
    "/api/v1/action-plans/grounded",
    response_model=ActionPlanResponse,
    status_code=201,
)
def create_grounded_action_plan(request: GroundedActionPlanCreate):
    try:
        return get_action_workflow_service().create_grounded_plan(request)
    except InsufficientEvidenceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except DuplicateActionIdError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get(
    "/api/v1/action-plans/{plan_id}",
    response_model=ActionPlanResponse,
)
def get_action_plan(plan_id: str):
    try:
        return get_action_workflow_service().get_plan(plan_id)
    except ActionPlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/api/v1/action-plans/{plan_id}/approve",
    response_model=ActionPlanResponse,
)
def approve_action_plan(plan_id: str, request: ActionPlanDecision):
    try:
        return get_action_workflow_service().approve_plan(
            plan_id,
            str(request.actor),
        )
    except ActionPlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidStateTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post(
    "/api/v1/action-plans/{plan_id}/reject",
    response_model=ActionPlanResponse,
)
def reject_action_plan(plan_id: str, request: ActionPlanDecision):
    try:
        return get_action_workflow_service().reject_plan(
            plan_id,
            str(request.actor),
        )
    except ActionPlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidStateTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post(
    "/api/v1/action-plans/{plan_id}/execute",
    response_model=ActionPlanResponse,
)
def execute_action_plan(plan_id: str):
    try:
        return get_action_workflow_service().execute_plan(plan_id)
    except ActionPlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidStateTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

# [파일 목록 조회]
@app.get("/files")
def get_uploaded_files():
    try:
        # Azure AI Search에서 모든 문서의 메타데이터 조회 (필요한 필드만)
        results = search_client.search(
            search_text="*",
            select=["id", "title", "category", "created_at", "file_url", "size"],
            top=1000    # 충분한 개수
        )
        
        file_list = []
        seen_files = set()  # 청킹으로 인해 중복된 파일명 제거

        for doc in results:
            # Search 데이터가 가끔 None일 수 있으므로 안전하게 처리
            title = doc.get('title', 'Untitled')
            category = doc.get('category', 'reference')

            # (제목, 카테고리) 쌍으로 중복 검사
            unique_key = (title, category)

            # 청크 단위로 저장되어 있어서 파일명이 중복될 수 있음 -> 중복 제거
            if unique_key not in seen_files:
                seen_files.add(unique_key)
                file_list.append({
                    "id": doc['id'],
                    "name": title,
                    "category": category, # history, style, reference
                    "uploadDate": doc.get('created_at', '').split("T")[0] if doc['created_at'] else "",
                    "url": doc.get('file_url', ''),
                    "size": doc.get('size', "Unknown")
                })
        
        return {"files": file_list}

    except Exception as e:
        print(f"Error fetching files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# [대시보드 데이터 조회]
@app.get("/dashboard-data")
def get_dashboard_data():
    # 실제 운영 환경에선 DB나 Azure AI Search에서 집계하여 가져와야 함.
    # 현재는 프론트엔드 연동을 위해 더미 데이터를 반환.
    return {
        "status": "success",
        "meetings": [
            {
                "id": 1,
                "title": "2024 신제품 마케팅 전략 회의",
                "date": "2024-03-15",
                "summary": "신제품 출시를 위한 SNS 광고 채널 선정 및 인플루언서 협업 방안에 대해 논의함. 예산 및 일정 확정 필요."
            },
            {
                "id": 2,
                "title": "IT 인프라 고도화 기술 검토",
                "date": "2024-03-12",
                "summary": "클라우드 네이티브 아키텍처 도입을 위한 기술 스택 검토. 쿠버네티스 도입 및 보안 강화 방안 논의."
            }
        ],
        "open_issues": [
            {"title": "마케팅 예산 최종 승인 누락", "owner": "홍길동", "lastMentioned": "2024-03-15"},
            {"title": "서버 보안 패치 일정 확정", "owner": "이몽룡", "lastMentioned": "2024-03-12"}
        ],
        "suggested_agenda": [
            "인플루언서 리스트업 및 계약 조건 검토",
            "보안 패치 적용 시나리오 및 복구 플랜 수립"
        ]
    }

ALLOWED_EXTENSIONS = {
    "history": {".pdf", ".docx"},       # 회의록: PDF, Word
    "style": {".docx"},                 # 템플릿: Word Only (수정용)
    "reference": {".pdf", ".docx", ".txt"} # 참고 자료: 텍스트 기반 문서
}

# [파일 업로드]
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...), 
    category: str = Form(...) # 'ieum'(history), 'custom'(style), 'external'(reference)
):
    try:
        # 1. 카테고리 매핑 (Frontend 섹션 -> Backend 카테고리)
        category_map = {
            "ieum": "history",
            "custom": "style",
            "external": "reference",
            "history": "history",
            "style": "style",
            "reference": "reference"
        }
        target_category = category_map.get(category, "reference")

        # 2. 파일 확장자 검사
        file_ext = os.path.splitext(file.filename)[1].lower()
        allowed_list = ALLOWED_EXTENSIONS.get(target_category, set())
        if file_ext not in allowed_list:
            error_msg = f"'{target_category}' 카테고리는 {file_ext} 형식을 지원하지 않습니다. (지원: {', '.join(allowed_list)})"
            raise HTTPException(status_code=400, detail=error_msg)

        # 3. 임시 파일 저장
        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, file.filename)
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"파일 저장 실패: {str(e)}")

        # 4. RAG 파이프라인 실행
        container_name = target_category    # 컨테이너 이름도 카테고리와 동일하게 사용
        upload_file_to_rag(file_path, target_category, container_name)
        
        # 5. 임시 파일 삭제
        os.remove(file_path)
        
        return {"filename": file.filename, "status": "success"}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# [채팅 / 질문하기]
@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    try:
        # LLM Agent 호출 (RAG 검색 및 일정 등록 도구 활용)
        answer = process_chat_request(request.message, category=request.category)
        return {"response": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# [회의 심층 분석]
@app.post("/analyze-meeting")
async def analyze_meeting(request: MeetingSummaryData):
    if not request.summary_text.strip():
        raise HTTPException(status_code=400, detail="텍스트가 비어있습니다.")

    provider = get_llm_provider()
    try:
        analysis = provider.analyze_meeting(request.summary_text)
    except LLMProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # 기존 React Result 페이지와의 호환성을 유지하는 응답 형태다.
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
                    "deadline": (
                        item.due_date.isoformat() if item.due_date else None
                    ),
                }
                for item in analysis.action_items
            ],
            "openIssues": analysis.open_issues,
        },
    }

# [자동화 액션 실행]
@app.post("/execute-action")
async def execute_action(request: MeetingSummaryData):
    print("🚀 자동화 액션(메일 발송) 시작...")
    try:
        # 이메일 리스트를 세미콜론(;)으로 연결
        all_recipients = ";".join(TEAM_MEMBERS)
        
        # HTML 가독성을 위한 간단한 변환 (프론트엔드에서 이미 HTML을 보낼 수도 있음)
        formatted_content = request.summary_text
        if "<h" not in formatted_content:
            formatted_content = formatted_content.replace("\n", "<br>")

        if not LOGIC_APP_URL_MAIL:
            print("⚠️ LOGIC_APP_URL_MAIL 설정이 없습니다. 시뮬레이션 모드로 진행합니다.")
            return {"status": "success", "message": "시뮬레이션: 메일 발송 완료 (URL 미설정)"}

        # Logic App 호출
        payload = {
            "email": all_recipients,
            "subject": "[이음 AI] 회의 결과 리포트",
            "body": formatted_content
        }
        
        response = requests.post(LOGIC_APP_URL_MAIL, json=payload)
        if response.status_code >= 400:
            print(f"❌ Logic App 호출 실패: {response.text}")
            raise Exception("메일 발송 서버 응답 오류")

        return {"status": "success", "sent_count": len(TEAM_MEMBERS)}
    except Exception as e:
        print(f"❌ 액션 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# [Microsoft Outlook 연동]
@app.post("/approve-calendar")
async def approve_calendar(item: CalendarRequest):
    print(f"📆 일정 등록 요청: {item.title} ({item.date} {item.time})")
    try:
        # ISO 8601 형식으로 변환 (outlook_service가 기대하는 형식)
        start_str = f"{item.date}T{item.time}:00"
        # 간단한 검증: datetime 객체로 변환 시도
        datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S")
        
        # 종료 시간 계산 (기본 1시간)
        start_dt = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S")
        end_dt = start_dt + timedelta(hours=1)
        end_str = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

        event_body = {
            "subject": item.title,
            "body": {
                "contentType": "Text", 
                "content": f"참석자: {', '.join(item.attendees)}"
            },
            "start": {
                "dateTime": start_str, 
                "timeZone": "Korea Standard Time"
            },
            "end": {
                "dateTime": end_str, 
                "timeZone": "Korea Standard Time"
            }, 
        }
        
        success, msg = outlook_service.send_event_to_logic_app(event_body)
        if not success:
            raise Exception(msg)
            
        return {"status": "success", "message": "일정이 등록되었습니다."}
    except Exception as e:
        print(f"❌ 일정 등록 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/create-outlook-task")
async def create_outlook_task(request: TodoRequest):
    print(f"📝 할 일 등록 요청: {request.title} (기한: {request.due_date})")
    try:
        success, msg = outlook_service.create_todo_task(
            request.title, 
            request.content, 
            request.due_date
        )
        if not success:
            raise Exception(msg)
            
        return {"status": "success", "message": "할 일이 등록되었습니다."}
    except Exception as e:
        print(f"❌ 할 일 등록 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# [파일 삭제]
@app.delete("/delete")
def delete_endpoint(request: DeleteRequest):
    try:
        category_map = {
            "ieum": "history",
            "custom": "style",
            "external": "reference",
            "history": "history",
            "style": "style",
            "reference": "reference"
        }
        container_name = category_map.get(request.category, "reference")
        
        delete_file_and_index(request.filename, container_name)
        return {"status": "deleted", "filename": request.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# [커스텀 회의록 파일 생성]
@app.post("/generate-minutes")
async def generate_minutes(data: MeetingSummaryData):
    try:
        # 1. 작업용 임시 폴더 생성
        temp_dir = "temp_processing"
        os.makedirs(temp_dir, exist_ok=True)
        
        # 기본 템플릿 경로 (프로젝트 루트에 default_template.docx 필수!)
        default_template_name = "default_template.docx"
        local_template_path = os.path.join(temp_dir, "current_template.docx")
        
        # 2. 템플릿 결정 로직 (Azure Blob 'style' 컨테이너 확인)
        used_template_source = "Default"
        try:
            container_client = blob_service_client.get_container_client("style")
            
            # 컨테이너가 존재하면 파일 목록 확인
            if container_client.exists():
                blobs_list = list(container_client.list_blobs())
                if blobs_list:
                    # 가장 최근 파일 가져오기 (이름순 정렬 후 마지막 것 사용)
                    # 실제 운영에선 created_on 속성으로 정렬 추천
                    latest_blob = sorted(blobs_list, key=lambda b: b.name)[-1]
                    
                    print(f"📥 커스텀 템플릿 다운로드: {latest_blob.name}")
                    with open(local_template_path, "wb") as f:
                        f.write(container_client.download_blob(latest_blob.name).readall())
                    used_template_source = "Custom (Azure Blob)"
                else:
                    raise Exception("스타일 컨테이너가 비어있음")
            else:
                raise Exception("스타일 컨테이너 없음")
                
        except Exception as e:
            print(f"커스텀 템플릿 사용 불가 ({e}) -> 기본 템플릿 사용")
            if os.path.exists(default_template_name):
                shutil.copy(default_template_name, local_template_path)
            else:
                raise HTTPException(status_code=500, detail="서버에 기본 템플릿(default_template.docx)이 없습니다.")

        print(f"✅ 템플릿 준비 완료: {used_template_source}")

        # 3. 문서 생성 프로세스 (RAG Logic)
        
        # A. 템플릿 좌표 읽기
        coords_text = extract_text_with_coordinates(local_template_path)
        
        # B. LLM에게 매핑 요청
        llm_result = get_coordinates_json_from_llm(coords_text, data.summary_text)
        
        # C. 문서 내용 교체 및 저장
        output_filename = f"meeting_result_{uuid.uuid4().hex[:8]}.docx"
        output_path = os.path.join(temp_dir, output_filename)
        
        update_docx_by_coordinates(local_template_path, output_path, llm_result["updates"])
        
        # 4. 파일 반환
        return FileResponse(
            path=output_path,
            filename=f"이음AI_회의록_{uuid.uuid4().hex[:4]}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except Exception as e:
        print(f"❌ 문서 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 메인 실행
# ==========================================
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
        raise HTTPException(status_code=500, detail=str(e))
