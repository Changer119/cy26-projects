"""知识库文档加载 + 切片。"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

_CHUNK_SIZE = 300  # 每个片段的目标字符数（按段落聚合，避免切碎语义）
_SUPPORTED_SUFFIXES = {".md", ".txt"}


class KnowledgeChunk(BaseModel):
    """一篇文档切片后的一个片段，携带来源文件名。"""

    source: str
    text: str


def load_documents(data_dir: Path) -> list[KnowledgeChunk]:
    """读取 data_dir 下所有 .md/.txt 文档并切片成 KnowledgeChunk 列表。"""
    chunks: list[KnowledgeChunk] = []
    if not data_dir.exists():
        return chunks

    for file_path in sorted(data_dir.iterdir()):
        if file_path.suffix.lower() not in _SUPPORTED_SUFFIXES:
            continue
        text = file_path.read_text(encoding="utf-8")
        chunks.extend(_split_into_chunks(source=file_path.name, text=text))
    return chunks


def _split_into_chunks(source: str, text: str) -> list[KnowledgeChunk]:
    """按空行分段，再把相邻段落合并到接近 _CHUNK_SIZE 的片段中。"""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[KnowledgeChunk] = []
    buffer = ""
    for paragraph in paragraphs:
        candidate = f"{buffer}\n\n{paragraph}" if buffer else paragraph
        if len(candidate) > _CHUNK_SIZE and buffer:
            chunks.append(KnowledgeChunk(source=source, text=buffer))
            buffer = paragraph
        else:
            buffer = candidate
    if buffer:
        chunks.append(KnowledgeChunk(source=source, text=buffer))
    return chunks
