from ieum.ingestion import DocumentMetadata, chunk_document


def test_chunker_preserves_section_and_metadata():
    chunks = chunk_document(
        "# 출장비\n\n국내 출장 교통비는 실비로 정산합니다.\n\n# 승인\n\n십만 원 이상은 팀장 승인이 필요합니다.",
        DocumentMetadata(
            document_id="travel-policy",
            title="출장비 규정",
            category="policy",
            source_url="mock://travel-policy",
            updated_at="2026-08-01T00:00:00+09:00",
        ),
        max_chars=50,
    )

    assert [chunk.section for chunk in chunks] == ["출장비", "승인"]
    assert [chunk.chunk_id for chunk in chunks] == [
        "travel-policy-0000",
        "travel-policy-0001",
    ]
    assert all(chunk.category == "policy" for chunk in chunks)
    assert all(chunk.updated_at is not None for chunk in chunks)


def test_chunker_removes_exact_duplicate_paragraphs():
    chunks = chunk_document(
        "# 공통\n\n회의실 예약은 사내 포털에서 신청합니다.\n\n회의실 예약은 사내 포털에서 신청합니다.",
        DocumentMetadata(document_id="room", title="회의실 규정"),
        max_chars=30,
    )

    assert len(chunks) == 1


def test_chunker_splits_long_content_with_size_limit():
    chunks = chunk_document(
        " ".join(f"{index}번째 고유 문장입니다." for index in range(30)),
        DocumentMetadata(document_id="long", title="긴 문서"),
        max_chars=60,
    )

    assert len(chunks) > 1
    assert all(len(chunk.content) <= 60 for chunk in chunks)
