from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Awaitable, Callable
from uuid import uuid4

from evaluate.models import EvaluationDataset, EvaluationSample


SampleBuilder = Callable[..., Awaitable[dict[str, Any]]]


class EvaluationDatasetGenerator:
    def __init__(
        self,
        *,
        chat_model=None,
        sample_builder: SampleBuilder | None = None,
        id_factory: Callable[[str], str] | None = None,
        now_factory: Callable[[], str] | None = None,
    ):
        self.chat_model = chat_model
        self.sample_builder = sample_builder or self._build_sample_with_model
        self.id_factory = id_factory or (lambda prefix: f"{prefix}-{uuid4().hex}")
        self.now_factory = now_factory or (lambda: datetime.utcnow().isoformat())

    async def generate(
        self,
        *,
        name: str,
        source_documents: list[dict[str, Any]],
        source_document_ids: list[str],
        generator_model: str,
        sample_count: int,
        dataset_id: str | None = None,
    ) -> EvaluationDataset:
        candidates = self._collect_candidate_chunks(source_documents, source_document_ids)
        selected_candidates = candidates[:sample_count]

        samples: list[EvaluationSample] = []
        for candidate in selected_candidates:
            built = await self.sample_builder(
                document=candidate["document"],
                chunk=candidate["chunk"],
            )
            sample = EvaluationSample(
                sample_id=self.id_factory("sample"),
                question=built["question"],
                reference_answer=built["reference_answer"],
                reference_contexts=built.get("reference_contexts", []),
                source_document_id=candidate["document"]["document_id"],
                source_chunk_ids=[
                    f"{candidate['document']['document_id']}#{candidate['chunk']['index']}"
                ],
                metadata=built.get("metadata", {}),
            )
            samples.append(sample)

        now = self.now_factory()
        return EvaluationDataset(
            dataset_id=dataset_id or self.id_factory("dataset"),
            name=name,
            source_document_ids=source_document_ids,
            generator_model=generator_model,
            status="completed",
            created_at=now,
            updated_at=now,
            sample_count=len(samples),
            version=1,
            samples=samples,
            error=None,
        )

    @staticmethod
    def _collect_candidate_chunks(
        source_documents: list[dict[str, Any]],
        source_document_ids: list[str],
    ) -> list[dict[str, Any]]:
        allowed = set(source_document_ids)
        candidates: list[dict[str, Any]] = []
        for document in source_documents:
            document_id = document.get("document_id")
            if allowed and document_id not in allowed:
                continue
            for chunk in document.get("chunks", []):
                if not chunk.get("text"):
                    continue
                candidates.append({"document": document, "chunk": chunk})
        return candidates

    async def _build_sample_with_model(
        self, *, document: dict[str, Any], chunk: dict[str, Any]
    ) -> dict[str, Any]:
        if self.chat_model is None:
            raise ValueError("未配置用于数据集生成的聊天模型")

        prompt = (
            "你是 RAG 评估数据集生成器。请基于给定文档片段，输出一条评估样本 JSON。"
            '字段必须包含 question、reference_answer、reference_contexts、metadata。'
            "不要输出 markdown 代码块。\n"
            f"文件名: {document.get('filename', '')}\n"
            f"文档ID: {document.get('document_id', '')}\n"
            f"片段内容:\n{chunk.get('text', '')}\n"
        )
        content = await self._invoke_model(prompt)
        parsed = self._load_json(content)
        return {
            "question": str(parsed["question"]).strip(),
            "reference_answer": str(parsed["reference_answer"]).strip(),
            "reference_contexts": [
                str(item).strip() for item in parsed.get("reference_contexts", [])
            ],
            "metadata": parsed.get("metadata", {}),
        }

    async def _invoke_model(self, prompt: str) -> str:
        if hasattr(self.chat_model, "ainvoke"):
            response = await self.chat_model.ainvoke(prompt)
        else:
            response = await asyncio.to_thread(self.chat_model.invoke, prompt)

        if hasattr(response, "content"):
            return str(response.content)
        return str(response)

    @staticmethod
    def _load_json(raw: str) -> dict[str, Any]:
        content = raw.strip()
        if content.startswith("```"):
            lines = [line for line in content.splitlines() if not line.startswith("```")]
            content = "\n".join(lines).strip()
        return json.loads(content)
