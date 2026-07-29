# pip install azure-core azure-storage-blob azure-search-documents openai pypdf python-docx python-dotenv

from pathlib import Path
from dotenv import load_dotenv
import os

ENV_PATH = Path(__file__).resolve().parent / "BE.env"   # BE.env가 Backend 폴더에 있을 때
print("ENV_PATH =", ENV_PATH, "exists =", ENV_PATH.exists())

load_dotenv(ENV_PATH)

print("BLOB_CONNECTION_STRING =", os.getenv("BLOB_CONNECTION_STRING"))


from pathlib import Path
from dotenv import load_dotenv
import os

# upload_pipeline.py가 있는 폴더(Backend) 안에 .env가 있을 때
load_dotenv(Path(__file__).resolve().parent / ".env")

# 만약 .env가 프로젝트 루트에 있으면 이걸로 바꿔라:
# load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BLOB_CONNECTION_STRING = os.getenv("BLOB_CONNECTION_STRING")
if not BLOB_CONNECTION_STRING:
    raise RuntimeError("BLOB_CONNECTION_STRING is missing. Check .env path and key name.")

import os
from dotenv import load_dotenv
import base64
from datetime import datetime, timezone
from pypdf import PdfReader
from docx import Document
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
from azure.search.documents import SearchClient
from openai import AzureOpenAI

load_dotenv()

# ==========================================
# 환경 변수 불러오기
# ==========================================
BLOB_CONNECTION_STRING = os.getenv("BLOB_CONNECTION_STRING")
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
EMBEDDING_DEPLOYMENT_NAME = os.getenv("EMBEDDING_DEPLOYMENT_NAME")

# ==========================================
# 클라이언트 초기화
# ==========================================
blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
search_client = SearchClient(AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_INDEX_NAME, AzureKeyCredential(AZURE_SEARCH_API_KEY))
openai_client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT
)

# ==========================================
# 1. 텍스트 추출 함수
# ==========================================
def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    
    if ext == ".pdf":
        from pypdf import PdfReader
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        except Exception as e:
            print(f"PDF extract error: {e}")

    elif ext == ".docx":     
        try:
            doc = Document(file_path)
            for element in doc.element.body:
                # 문단(Paragraph)
                if element.tag.endswith('p'):
                    # XML element에서 텍스트 추출을 위해 paragraph 객체로 래핑
                    # (간단히 doc.paragraphs에서 찾는 대신 element text를 직접 가져옴)
                    para_text = "".join([node.text for node in element.iter() if node.text])
                    if para_text.strip():
                        text += para_text + "\n"
                
                # 표(Table) -> Markdown 포맷으로 변환
                elif element.tag.endswith('tbl'):
                    # 표 처리를 위해 Document 객체 내의 해당 테이블 인덱스를 찾거나
                    # 간단히 텍스트만 긁어모은 후 element를 순회하며 셀 데이터를 '|'로 묶기
                    
                    table_text = []
                    # 행(Row) 순회
                    for row in element.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr'):
                        row_cells = []
                        # 열(Cell) 순회
                        for cell in row.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc'):
                            # 셀 내부 텍스트 추출 (셀 안에도 문단이 여러 개일 수 있음)
                            cell_content = "".join([node.text for node in cell.iter() if node.text]).strip()
                            row_cells.append(cell_content)
                        
                        # Markdown 행 생성: | 값1 | 값2 | 값3 |
                        if row_cells:
                            table_text.append("| " + " | ".join(row_cells) + " |")
                    
                    if table_text:
                        text += "\n" + "\n".join(table_text) + "\n\n"
        except Exception as e:
            print(f"DOCX extract error: {e}")
    
    else:
        # .txt 등 기타 파일 지원
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
            
    return text

# ==========================================
# 2. 청킹 (Chunking)
# ==========================================
def chunk_text(text, chunk_size=1000, overlap=100):
    """
    긴 텍스트를 chunk_size 길이로 자르되, 
    문맥 단절을 막기 위해 overlap 만큼 겹치게 자릅니다.
    """
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        # 겹치게 이동 (다음 시작점은 현재 끝점 - overlap)
        start += (chunk_size - overlap)
        
    return chunks

# ==========================================
# 3. 임베딩 생성 (Vectorize)
# ==========================================
def generate_embedding(text):
    response = openai_client.embeddings.create(
        input=text,
        model=EMBEDDING_DEPLOYMENT_NAME
    )
    return response.data[0].embedding

# ==========================================
# 4. ID 인코딩 (Base64)
# ==========================================
def encode_id(raw_id):
    # Azure Search ID는 URL-safe 문자만 허용하므로 Base64 인코딩 필수
    return base64.urlsafe_b64encode(raw_id.encode()).decode()

# ==========================================
# [메인 로직] 파일 업로드 및 인덱싱 파이프라인
# ==========================================
def upload_file_to_rag(file_path, category, container_name="default"):
    """
    file_path: 로컬 파일 경로
    category: 'history', 'reference', 'style' 중 하나
    container_name: Blob 컨테이너 이름 (history, reference, style)
    """
    filename = os.path.basename(file_path)
    print(f"🚀 처리 시작: {filename} (Category: {category})")

    # 1. Blob Storage에 파일 업로드
    try:
        # 컨테이너가 없으면 생성
        container_client = blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            container_client.create_container()
            
        blob_client = container_client.get_blob_client(filename)
        
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
            
        file_url = blob_client.url
        print(f"   [1/4] Blob 업로드 완료: {file_url}")
        
    except Exception as e:
        print(f"❌ Blob 업로드 실패: {e}")
        return
    
    # 2. 파일 용량 계산
    def get_readable_file_size(file_path):
        size_bytes = os.path.getsize(file_path)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024

    file_size_str = get_readable_file_size(file_path)

    # 3. 텍스트 추출 및 청킹
    full_text = extract_text_from_file(file_path)
    chunks = chunk_text(full_text)
    print(f"   [2/4] 텍스트 추출 및 청킹 완료 ({len(chunks)}개 청크)")

    # 4. 임베딩 생성 및 문서 객체 생성
    search_documents = []
    for i, chunk in enumerate(chunks):
        # 각 청크마다 고유 ID 생성 (파일 URL + 청크번호)
        # 예: https://.../file.pdf_0, https://.../file.pdf_1
        chunk_id = f"{file_url}_{i}"
        encoded_id = encode_id(chunk_id)
        
        vector = generate_embedding(chunk)

        # 현재 시간을 UTC 기준 ISO 8601 문자열로 생성 (예: '2025-12-29T05:23:11.123456+00:00' 형태)
        current_time_str = datetime.now(timezone.utc).isoformat()
        
        doc = {
            "id": encoded_id,
            "title": filename,
            "content": chunk,
            "category": category,
            "file_url": file_url,
            "content_vector": vector,
            "created_at": current_time_str,
            "size": file_size_str
        }
        search_documents.append(doc)
        
    print(f"   [3/4] 임베딩 생성 완료")

    # 5. Azure AI Search에 업로드
    try:
        # 배치를 사용하여 한 번에 업로드 (효율성)
        result = search_client.upload_documents(documents=search_documents)
        print(f"   [4/4] 인덱싱 완료! (성공: {len(result)})")
        print(f"✅ 최종 완료: {filename}")
        
    except Exception as e:
        print(f"❌ 인덱싱 실패: {e}")

# ==========================================
# 실행 테스트
# ==========================================
if __name__ == "__main__":
    # 테스트용 파일 경로
    sample_file = "TEST_PDF/Margies Travel Company Info_ko.pdf"
    
    # 예시: 과거 회의록(History) 업로드
    # 파일이 존재하는지 확인 후 실행
    if os.path.exists(sample_file):
        upload_file_to_rag(
            file_path=sample_file, 
            category="history", 
            container_name="history"
        )
    else:
        print(f"⚠️ 테스트 파일이 없습니다: {sample_file}")