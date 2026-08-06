import re

from ieum.ingestion.metadata import DocumentMetadata
from ieum.schemas.knowledge import DocumentChunkInput


HEADING_PATTERN = re.compile(r"^(?:#{1,6}\s+|\[(?P<bracket>[^]]+)\]\s*$)")


def chunk_document(
    text: str,
    metadata: DocumentMetadata,
    *,
    max_chars: int = 800,
    min_chars: int = 10,
) -> list[DocumentChunkInput]:
    if max_chars < min_chars:
        raise ValueError("max_chars는 min_chars 이상이어야 합니다.")
    sections = _split_sections(text, metadata.title)
    candidates: list[tuple[str, str]] = []
    for section, paragraphs in sections:
        current: list[str] = []
        current_length = 0
        for paragraph in paragraphs:
            for part in _split_long_paragraph(paragraph, max_chars):
                added = len(part) + (2 if current else 0)
                if current and current_length + added > max_chars:
                    candidates.append((section, "\n\n".join(current)))
                    current = []
                    current_length = 0
                current.append(part)
                current_length += len(part) + (2 if len(current) > 1 else 0)
        if current:
            candidates.append((section, "\n\n".join(current)))

    chunks = []
    seen = set()
    for section, content in candidates:
        normalized = _normalize(content)
        if len(normalized) < min_chars or normalized in seen:
            continue
        seen.add(normalized)
        index = len(chunks)
        chunks.append(
            DocumentChunkInput(
                chunk_id=f"{metadata.document_id}-{index:04d}",
                document_id=metadata.document_id,
                title=metadata.title,
                content=content.strip(),
                category=metadata.category,
                chunk_index=index,
                section=section,
                source_url=metadata.source_url,
                created_at=metadata.created_at,
                updated_at=metadata.updated_at,
            )
        )
    return chunks


def _split_sections(text: str, default_section: str):
    sections = []
    section = default_section
    paragraphs = []
    for block in re.split(r"\n\s*\n", text.strip()):
        block = block.strip()
        if not block:
            continue
        first_line = block.splitlines()[0].strip()
        if HEADING_PATTERN.match(first_line):
            if paragraphs:
                sections.append((section, paragraphs))
            section = first_line.lstrip("#").strip().strip("[]")
            remainder = "\n".join(block.splitlines()[1:]).strip()
            paragraphs = [remainder] if remainder else []
        else:
            paragraphs.append(block)
    if paragraphs:
        sections.append((section, paragraphs))
    return sections


def _split_long_paragraph(paragraph: str, max_chars: int):
    if len(paragraph) <= max_chars:
        return [paragraph]
    sentences = re.split(r"(?<=[.!?。])\s+", paragraph)
    parts = []
    current = ""
    for sentence in sentences:
        if len(sentence) > max_chars:
            if current:
                parts.append(current)
                current = ""
            parts.extend(
                sentence[index : index + max_chars]
                for index in range(0, len(sentence), max_chars)
            )
        elif current and len(current) + 1 + len(sentence) > max_chars:
            parts.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        parts.append(current)
    return parts


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()
