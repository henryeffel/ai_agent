import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

# ==========================================
# 환경 변수 불러오기
# ==========================================
BLOB_CONNECTION_STRING = os.getenv("BLOB_CONNECTION_STRING")
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")

blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
search_client = SearchClient(AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_INDEX_NAME, AzureKeyCredential(AZURE_SEARCH_API_KEY))

def delete_file_and_index(filename, container_name="history"):
    print(f"🗑️ 삭제 시작: {filename}")
    
    # 1. Azure Blob Storage에서 파일 삭제
    try:
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(filename)
        
        if blob_client.exists():
            blob_client.delete_blob()
            print(f"   [1/2] Blob 파일 삭제 완료")
        else:
            print(f"   [1/2] Blob에 파일이 없습니다 (Skip)")
            
    except Exception as e:
        print(f"❌ Blob 삭제 중 오류: {e}")

    # 2. Azure AI Search에서 문서 삭제
    # 하나의 파일을 여러 청크로 쪼개서 넣었으므로 'file_url'이 해당 파일을 포함하는 모든 문서를 찾아서 지워야 함
    try:
        # Blob URL 추정 (업로드 시 생성 규칙 따름)
        # 예: https://mystorage.../history/filename.docx
        # 정확한 URL 매칭을 위해선 Search로 먼저 file_url을 조회하는 게 가장 안전
        
        # 전략: title이 filename과 일치하는 모든 문서를 찾아서 ID를 가져옴
        results = search_client.search(
            search_text="*",
            filter=f"title eq '{filename}'",
            select=["id", "title"]
        )
        
        ids_to_delete = []
        for doc in results:
            ids_to_delete.append({"id": doc["id"]})
            
        if ids_to_delete:
            search_client.delete_documents(documents=ids_to_delete)
            print(f"   [2/2] 인덱스 문서 {len(ids_to_delete)}개 삭제 완료")
        else:
            print(f"   [2/2] 인덱스에 관련 문서가 없습니다.")
            
    except Exception as e:
        print(f"❌ 인덱스 삭제 중 오류: {e}")

    print("✅ 삭제 프로세스 종료")

# ==========================================
# 실행 테스트
# ==========================================
if __name__ == "__main__":
    # 업로드했던 테스트 파일 삭제
    delete_file_and_index("Margies Travel Company Info_ko.pdf", container_name="history")