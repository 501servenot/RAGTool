from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Awaitable, Callable
from uuid import uuid4

from pydantic import BaseModel, Field

from evaluate.models import EvaluationDataset, EvaluationSample


SampleBuilder = Callable[..., Awaitable[dict[str, Any]]]


class GeneratedEvaluationSample(BaseModel):
    question: str = Field(..., description="基于文档片段生成的评估问题")
    reference_answer: str = Field(..., description="问题对应的参考答案")
    reference_contexts: list[str] = Field(
        default_factory=list, description="支撑参考答案的上下文片段列表"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="样本附加元数据")


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
        if not hasattr(self.chat_model, "with_structured_output"):
            raise ValueError("当前评估集生成模型不支持结构化输出")

        prompt = (
            "你是 RAG 评估数据集生成器。"
            "请只返回一条结构化评估样本，字段包含 question、reference_answer、reference_contexts、metadata。"
            "question 要清晰具体，reference_answer 要忠于文档片段，"
            "reference_contexts 只保留最关键的原文片段。\n"
            f"文件名: {document.get('filename', '')}\n"
            f"文档ID: {document.get('document_id', '')}\n"
            f"片段内容:\n{chunk.get('text', '')}\n"
        )
        runnable = self.chat_model.with_structured_output(
            GeneratedEvaluationSample,
            method="function_calling",
            include_raw=True,
        )
        parsed = await self._invoke_structured_model(runnable, prompt)
        return {
            "question": str(parsed["question"]).strip(),
            "reference_answer": str(parsed["reference_answer"]).strip(),
            "reference_contexts": [
                str(item).strip() for item in parsed.get("reference_contexts", [])
            ],
            "metadata": parsed.get("metadata", {}),
        }

    @staticmethod
    async def _invoke_structured_model(runnable, prompt: str) -> dict[str, Any]:
        if hasattr(runnable, "ainvoke"):
            response = await runnable.ainvoke(prompt)
        else:
            response = await asyncio.to_thread(runnable.invoke, prompt)

        return EvaluationDatasetGenerator._coerce_structured_response(response)

    @staticmethod
    def _coerce_structured_response(response) -> dict[str, Any]:
        required_keys = {"question", "reference_answer", "reference_contexts", "metadata"}

        if isinstance(response, BaseModel):
            return response.model_dump(mode="json")

        if isinstance(response, dict) and required_keys.issubset(response.keys()):
            return response

        if isinstance(response, dict):
            parsed = response.get("parsed")
            if parsed is not None:
                return EvaluationDatasetGenerator._coerce_structured_response(parsed)

            raw = response.get("raw")
            if raw is not None:
                return EvaluationDatasetGenerator._coerce_structured_response(raw)

            parsing_error = response.get("parsing_error")
            if parsing_error is not None:
                raise ValueError(f"结构化输出解析失败: {parsing_error}")

        tool_calls = getattr(response, "tool_calls", None)
        if isinstance(tool_calls, list) and tool_calls:
            for tool_call in tool_calls:
                args = tool_call.get("args")
                if isinstance(args, dict):
                    return args
                if isinstance(args, str):
                    return json.loads(args)

        additional_kwargs = getattr(response, "additional_kwargs", None)
        if isinstance(additional_kwargs, dict):
            raw_tool_calls = additional_kwargs.get("tool_calls")
            if isinstance(raw_tool_calls, list) and raw_tool_calls:
                function = raw_tool_calls[0].get("function", {})
                arguments = function.get("arguments")
                if isinstance(arguments, dict):
                    return arguments
                if isinstance(arguments, str):
                    return json.loads(arguments)

        content = getattr(response, "content", None)
        if isinstance(content, str) and content.strip():
            return EvaluationDatasetGenerator._load_json_from_text(content)

        raise ValueError(
            f"结构化输出结果格式不受支持: {type(response).__name__}"
        )

    @staticmethod
    def _load_json_from_text(raw: str) -> dict[str, Any]:
        content = raw.strip()
        if content.startswith("```"):
            lines = [line for line in content.splitlines() if not line.startswith("```")]
            content = "\n".join(lines).strip()
        return json.loads(content)
