import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI
import json

load_dotenv()

# ==========================================
# 환경 변수 불러오기
# ==========================================
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
EMBEDDING_DEPLOYMENT_NAME = os.getenv("EMBEDDING_DEPLOYMENT_NAME")

# 클라이언트 초기화
search_client = SearchClient(AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_INDEX_NAME, AzureKeyCredential(AZURE_SEARCH_API_KEY))
openai_client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT
)

# ==========================================
# 1. 질문을 벡터로 변환
# ==========================================
def generate_embedding(text):
    response = openai_client.embeddings.create(input=text, model=EMBEDDING_DEPLOYMENT_NAME)
    return response.data[0].embedding

# ==========================================
# 2. Azure AI Search 검색 (Retrieve)
# ==========================================
def search_documents(query, category=None, top_k=3):
    """
    category:
      - "all" 또는 None: style을 제외한 모든 문서 검색 (history + reference)
      - "history", "reference": 해당 카테고리에서만 검색
    """
    try:
        # 1. 질문 벡터화
        vector = generate_embedding(query)
        vector_query = VectorizedQuery(vector=vector, k_nearest_neighbors=top_k, fields="content_vector")

        # 2. 필터 구성 (OData Syntax)
        filter_str = "category ne 'style'"
        if category and category.lower() != "all":
            filter_str = f"category eq '{category}'"

        # 3. 검색 실행 (Hybrid Search)
        results = search_client.search(
            search_text=query,             # 키워드 검색용
            vector_queries=[vector_query], # 벡터 검색용
            filter=filter_str,             # 카테고리 필터
            select=["title", "content", "created_at", "file_url", "category"],
            top=top_k
        )

        # 4. 결과 정리
        retrieved_docs = []
        for result in results:
            category_label = result['category'].upper() if result.get('category') else "UNKNOWN"
            # 생성 날짜를 읽기 쉬운 포맷으로 변환 (YYYY-MM-DD)
            created_at = result.get('created_at', '')
            date_str = created_at[:10] if created_at else "날짜 불명"
            
            source_tag = f"[{category_label}] {result['title']} (작성일: {date_str})"
            retrieved_docs.append(f"Source: {source_tag}\nContent: {result['content']}\n")
            
        return retrieved_docs
    
    except Exception as e:
        print(f"❌ 검색 실패: {e}")
        return []

# ==========================================
# 3. 답변 생성 (Generate)
# ==========================================
def generate_answer(query, context_docs):
    if not context_docs:
        return "관련된 정보를 찾을 수 없습니다."

    context_text = "\n\n".join(context_docs)
    
    system_prompt = """
    너는 스마트한 회의 어시스턴트야.
    아래 제공된 [Context]에 있는 내용을 바탕으로 질문에 답변해줘.
    
    [답변 가이드]
    1. 문서에 내용이 있다면 상세하고 친절하게 답변해.
    2. '지난 회의', '최근 회의' 등의 언급이 있으면 [Context]의 '작성일'을 참고해서 가장 적절한 정보를 찾아줘.
    3. 만약 [Context]에 질문과 관련된 내용이 전혀 없다면, '죄송하지만 관련 내용을 문서에서 찾을 수 없습니다.'라고 정중히 답변해.
    4. 답변 끝에는 반드시 참고한 문서의 [제목]과 (작성일)을 인용해줘.
    """
    
    user_prompt = f"""
    [Context]
    {context_text}

    [Question]
    {query}
    """

    response = openai_client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    return response.choices[0].message.content

# ==========================================
# 4. 회의 분석 (Analyze Meeting)
# ==========================================
def analyze_meeting_script(transcript):
    """
    회의 스크립트를 분석하여 요약, 결정사항, 할 일 등을 구조화된 JSON으로 반환
    """
    prompt = f"""
    당신은 회의 분석 전문가입니다. 아래 [회의 스크립트]를 읽고 분석 결과를 JSON 형식으로 반환하세요.
    반드시 다음 키를 가진 JSON 객체만 출력하세요. 다른 텍스트는 포함하지 마세요.

    JSON Keys:
    - summary: 회의 전체의 핵심 내용을 3-4문장으로 요약
    - decisions: 회의에서 합의된 주요 결정사항 목록 (문자열 배열)
    - actionItems: [ {{"task": "할 일", "assignee": "담당자", "deadline": "YYYY-MM-DD" }} ] 형식의 배열
    - openIssues: 아직 결론나지 않은 미해결 안건 목록 (문자열 배열)
    - followUpMeeting: {{ "title": "회의명", "date": "YYYY-MM-DD", "time": "HH:MM", "attendees": [] }} 오브젝트
    - insights: {{ "meetingType": "회의유형", "sentiment": "분위기(긍정/부정/중립)", "keyTopics": [], "risks": [ {{ "level": "high/medium/low", "description": "위험 요소 내용" }} ], "recommendations": [] }}

    [회의 스크립트]
    {transcript}
    """

    response = openai_client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT_NAME,
        messages=[
            {"role": "system", "content": "너는 구조화된 데이터를 생성하는 유능한 비서야. 반드시 JSON 형식으로만 응답해."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)
    return result

# ==========================================
# 메인 함수 (외부 호출용)
# ==========================================
def ask_bot(user_query, target_category="history"):
# ... (기존 코드 유지)
    print(f"🔍 검색 중... (Category: {target_category})")
    
    # 1. 검색
    docs = search_documents(user_query, category=target_category)
    
    # 2. 답변 생성
    answer = generate_answer(user_query, docs)
    
    return answer

# ==========================================
# 실행 테스트
# ==========================================
if __name__ == "__main__":
    # 테스트 질문
    q = "그 여행사 이름이 뭐였지?"
    
    # history 카테고리에서 검색
    response = ask_bot(q, target_category="history")
    
    print("\n🤖 AI 답변:")
    print(response)