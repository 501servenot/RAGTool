import os
from datetime import datetime
from typing import Any

from langchain_chroma import Chroma
from langchain_community.embeddings.dashscope import DashScopeEmbeddings

from app.core.config import get_settings
from app.utils.semantic_chunker import SemanticTextSplitter
from app.utils.md5 import check_md5, remove_md5, save_md5, string_to_md5


class KnowledgeBaseServer(object):
    def __init__(self, *, embedding=None):
        settings = get_settings()
        os.makedirs(settings.persist_directory, exist_ok=True)
        embedding_function = embedding or DashScopeEmbeddings(
            model=settings.embedding_model_name,
        )

        self.chroma = Chroma(
            collection_name=settings.collection_name,
            embedding_function=embedding_function,
            persist_directory=settings.persist_directory,
        )
        self.spliter = SemanticTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=settings.separators,
        )

    def upload_by_str(self, data: str, filename: str) -> str:
        settings = get_settings()

        md5 = string_to_md5(data)
        md5_in_file = check_md5(md5)
        exists_in_store = self._document_exists_by_md5(md5)

        if exists_in_store:
            if not md5_in_file:
                save_md5(md5)
            return "内容已存在"

        if md5_in_file:
            remove_md5(md5)

        if len(data) > settings.max_spliter_char_num:
            knowledge_chunks: list[str] = self.spliter.split_text(data)
        else:
            knowledge_chunks = [data]

        metadata = {
            "document_id": md5,
            "content_md5": md5,
            "source": filename,
            "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "operator": "zhang",
        }

        self.chroma.add_texts(
            texts=knowledge_chunks,
            metadatas=[
                {**metadata, "chunk_index": index}
                for index, _ in enumerate(knowledge_chunks)
            ],
        )

        save_md5(md5)

        return "成功"

    def _get_document_groups(self) -> list[dict]:
        result = self.chroma.get(include=["metadatas", "documents"])
        ids: list[str] = result.get("ids", [])
        metadatas: list[dict | None] = result.get("metadatas", [])
        documents: list[str | None] = result.get("documents", [])

        grouped: dict[str, dict] = {}
        for index, (chunk_id, metadata, document_text) in enumerate(
            zip(ids, metadatas, documents)
        ):
            metadata = metadata or {}
            source = metadata.get("source", "unknown")
            create_time = metadata.get("create_time", "")
            operator = metadata.get("operator", "")
            document_id = metadata.get("document_id") or string_to_md5(
                f"{source}|{create_time}|{operator}"
            )
            content_md5 = metadata.get("content_md5")

            if document_id not in grouped:
                grouped[document_id] = {
                    "document_id": document_id,
                    "filename": source,
                    "chunk_count": 0,
                    "create_time": create_time,
                    "operator": operator,
                    "content_md5": content_md5,
                    "chunk_ids": [],
                    "chunks": [],
                }

            grouped[document_id]["chunk_count"] += 1
            grouped[document_id]["chunk_ids"].append(chunk_id)
            grouped[document_id]["chunks"].append(
                {
                    "index": metadata.get("chunk_index", index),
                    "text": document_text or "",
                }
            )
            if not grouped[document_id]["content_md5"] and content_md5:
                grouped[document_id]["content_md5"] = content_md5

        return sorted(
            grouped.values(),
            key=lambda item: (item["create_time"], item["filename"]),
            reverse=True,
        )

    def get_summary(self) -> dict:
        documents = self._get_document_groups()
        return {
            "document_count": len(documents),
            "chunk_count": sum(item["chunk_count"] for item in documents),
            "documents": [
                {
                    "document_id": item["document_id"],
                    "filename": item["filename"],
                    "chunk_count": item["chunk_count"],
                    "create_time": item["create_time"],
                    "operator": item["operator"],
                }
                for item in documents
            ],
        }

    @staticmethod
    def _merge_chunk_texts(chunks: list[dict[str, Any]]) -> str:
        ordered_chunks = sorted(chunks, key=lambda item: item["index"])
        merged = ""

        for chunk in ordered_chunks:
            text = chunk["text"]
            if not merged:
                merged = text
                continue

            max_overlap = min(len(merged), len(text))
            overlap_size = 0
            for size in range(max_overlap, 0, -1):
                if merged[-size:] == text[:size]:
                    overlap_size = size
                    break

            merged += text[overlap_size:]

        return merged

    def _resolve_document_md5(self, document: dict) -> str | None:
        if document.get("content_md5"):
            return document["content_md5"]

        merged_text = self._merge_chunk_texts(document.get("chunks", []))
        if not merged_text:
            return None

        return string_to_md5(merged_text)

    def _document_exists_by_md5(self, content_md5: str) -> bool:
        documents = self._get_document_groups()
        for document in documents:
            if self._resolve_document_md5(document) == content_md5:
                return True
        return False

    def delete_document(self, document_id: str) -> dict | None:
        documents = self._get_document_groups()
        target = next(
            (item for item in documents if item["document_id"] == document_id), None
        )
        if target is None:
            return None

        resolved_md5 = self._resolve_document_md5(target)
        self.chroma.delete(ids=target["chunk_ids"])

        if resolved_md5 and not self._document_exists_by_md5(resolved_md5):
            remove_md5(resolved_md5)

        return {
            "document_id": target["document_id"],
            "filename": target["filename"],
            "deleted_chunk_count": target["chunk_count"],
            "message": "删除成功",
        }
