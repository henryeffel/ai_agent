from pathlib import Path


def load_text(path: str | Path) -> str:
    source = Path(path)
    if source.suffix.lower() not in {".txt", ".md"}:
        raise ValueError("현재 loader는 UTF-8 .txt와 .md 파일만 지원합니다.")
    return source.read_text(encoding="utf-8")
