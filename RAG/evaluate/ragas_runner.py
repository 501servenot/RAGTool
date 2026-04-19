from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from evaluate.models import SampleEvaluationResult


Evaluator = Callable[[list[dict[str, Any]], list[str]], Awaitable[list[dict[str, Any]]]]


class RagasEvaluationRunner:
    def __init__(
        self,
        *,
        evaluator: Evaluator | None = None,
        chat_model=None,
        embedding_model=None,
    ):
        self.evaluator = evaluator or self._default_evaluator
        self.chat_model = chat_model
        self.embedding_model = embedding_model

    async def evaluate(
        self,
        *,
        records: list[dict[str, Any]],
        metrics: list[str],
    ) -> tuple[dict[str, float | None], list[SampleEvaluationResult]]:
        raw_results = await self.evaluator(records, metrics)
        sample_results: list[SampleEvaluationResult] = []
        for record, raw in zip(records, raw_results):
            sample_results.append(
                SampleEvaluationResult(
                    sample_id=record["sample_id"],
                    question=record["question"],
                    answer=record["answer"],
                    reference_answer=record["reference_answer"],
                    retrieved_contexts=record.get("retrieved_contexts", []),
                    reference_contexts=record.get("reference_contexts", []),
                    metric_scores=raw.get("metric_scores", {}),
                    error=raw.get("error"),
                )
            )

        summary = self._aggregate_summary(sample_results, metrics)
        return summary, sample_results

    @staticmethod
    def _aggregate_summary(
        sample_results: list[SampleEvaluationResult],
        metrics: list[str],
    ) -> dict[str, float | None]:
        summary: dict[str, float | None] = {}
        for metric in metrics:
            values = [
                score
                for result in sample_results
                if (score := result.metric_scores.get(metric)) is not None
            ]
            summary[metric] = round(sum(values) / len(values), 4) if values else None

        total = len(sample_results)
        success = len([item for item in sample_results if not item.error])
        summary["success_rate"] = round(success / total, 4) if total else None
        return summary

    async def _default_evaluator(
        self,
        records: list[dict[str, Any]],
        metrics: list[str],
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(
            self._run_ragas_sync,
            records,
            metrics,
            self.chat_model,
            self.embedding_model,
        )

    @staticmethod
    def _run_ragas_sync(
        records: list[dict[str, Any]],
        metrics: list[str],
        chat_model=None,
        embedding_model=None,
    ) -> list[dict[str, Any]]:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper

        metric_objects = [RagasEvaluationRunner._resolve_metric(name) for name in metrics]
        dataset = Dataset.from_dict(
            {
                "question": [item["question"] for item in records],
                "answer": [item["answer"] for item in records],
                "contexts": [item.get("retrieved_contexts", []) for item in records],
                "reference": [item["reference_answer"] for item in records],
                "reference_contexts": [
                    item.get("reference_contexts", []) for item in records
                ],
                "sample_id": [item["sample_id"] for item in records],
            }
        )

        llm = LangchainLLMWrapper(chat_model) if chat_model is not None else None
        embeddings = (
            LangchainEmbeddingsWrapper(embedding_model)
            if embedding_model is not None
            else None
        )
        result = evaluate(
            dataset=dataset,
            metrics=metric_objects,
            llm=llm,
            embeddings=embeddings,
            show_progress=False,
            allow_nest_asyncio=False,
        )
        score_rows = RagasEvaluationRunner._extract_score_rows(result, len(records))

        raw_results: list[dict[str, Any]] = []
        for record, row in zip(records, score_rows):
            raw_results.append(
                {
                    "sample_id": record["sample_id"],
                    "metric_scores": {
                        metric: RagasEvaluationRunner._coerce_float(row.get(metric))
                        for metric in metrics
                    },
                    "error": row.get("error"),
                }
            )
        return raw_results

    @staticmethod
    def _extract_score_rows(result, expected_size: int) -> list[dict[str, Any]]:
        if hasattr(result, "scores") and isinstance(result.scores, list):
            return result.scores

        if hasattr(result, "to_pandas"):
            dataframe = result.to_pandas()
            rows = dataframe.to_dict(orient="records")
            if rows:
                return rows

        return [{} for _ in range(expected_size)]

    @staticmethod
    def _resolve_metric(name: str):
        from ragas.metrics import (
            AnswerRelevancy,
            ContextPrecision,
            ContextRecall,
            Faithfulness,
        )

        metric_map = {
            "faithfulness": Faithfulness(),
            "answer_relevancy": AnswerRelevancy(),
            "context_precision": ContextPrecision(),
            "context_recall": ContextRecall(),
        }
        if name not in metric_map:
            raise ValueError(f"不支持的 ragas 指标: {name}")
        return metric_map[name]

    @staticmethod
    def _coerce_float(value) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
