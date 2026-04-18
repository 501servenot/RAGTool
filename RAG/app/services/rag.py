import asyncio
import logging
from dataclasses import dataclass
from operator import itemgetter
from time import perf_counter
from typing import AsyncIterator

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.embeddings.dashscope import DashScopeEmbeddings
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

from app.core.config import get_settings
from app.memory.historymessage import FileChatMessageHistory
from app.services.query_rewrite import QueryRewriteResult, QueryRewriteService
from app.services.rerank import RerankService
from app.services.vector_store import VectorStoreService


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetrievalQualityAssessment:
    label: str
    should_rewrite: bool
    reason: str
    top1_score: float | None
    top3_avg_score: float | None
    doc_count: int


class RAGservice(object):
    def __init__(
        self,
        *,
        vector_service=None,
        chat_model=None,
        query_rewrite_service=None,
        rerank_service=None,
    ):
        settings = get_settings()
        self.settings = settings

        self.vector_service = vector_service or VectorStoreService(
            embedding=DashScopeEmbeddings(model=settings.embedding_model_name)
        )

        self.prompt_template = ChatPromptTemplate(
            [
                (
                    "system",
                    (
                        "以我提供的参考资料为主，用专业的知识回答用户的问题。"
                        "如果不知道的话就回答我暂时不清楚该问题的答案，不要瞎编。"
                        "优先围绕标准化问题作答，如果与原始问题有细微差异，以原始问题真实意图为准。"
                        "参考资料:{context}"
                    ),
                ),
                MessagesPlaceholder(variable_name="history"),
                (
                    "user",
                    (
                        "用户原始问题：{original_input}\n"
                        "标准化问题：{rewritten_input}\n"
                        "请基于参考资料回答。"
                    ),
                ),
            ]
        )

        self.chat_model = chat_model or ChatTongyi(model=settings.chat_model_name)
        self.query_rewrite_service = query_rewrite_service or QueryRewriteService()
        self.rerank_service = rerank_service or RerankService()

        self.chain = self.__get_chain()
        self.chain_with_history = self.__get_chain_with_history()

    def __get_chain(self):
        chain = (
            {
                "original_input": itemgetter("original_input"),
                "rewritten_input": itemgetter("rewritten_input"),
                "history": itemgetter("history"),
                "context": itemgetter("context"),
            }
            | self.prompt_template
            | self.chat_model
            | StrOutputParser()
        )

        return chain

    def _get_message_history(self, session_id: str) -> BaseChatMessageHistory:
        settings = get_settings()
        return FileChatMessageHistory(
            session_id=session_id,
            storage_path=settings.chat_history_directory,
        )

    def __get_chain_with_history(self):
        return RunnableWithMessageHistory(
            self.chain,
            get_session_history=self._get_message_history,
            input_messages_key="original_input",
            history_messages_key="history",
        )

    @staticmethod
    def _format_documents(docs: list[Document]) -> str:
        if not docs:
            return "没有相关文档"
        formatted_str = ""
        for doc in docs:
            formatted_str += f"文档内容：{doc.page_content}\n文档元内容：{doc.metadata}\n\n"
        return formatted_str

    @staticmethod
    def _short_query(query: str, *, limit: int = 80) -> str:
        compact_query = " ".join(query.split())
        if len(compact_query) <= limit:
            return compact_query
        return f"{compact_query[:limit]}..."

    @staticmethod
    def _doc_debug_labels(docs: list[Document]) -> list[str]:
        labels = []
        for doc in docs:
            metadata = doc.metadata or {}
            source = metadata.get("source", "unknown")
            chunk_index = metadata.get("chunk_index", "?")
            retrieval_rank = metadata.get("retrieval_rank")
            rerank_rank = metadata.get("rerank_rank")
            labels.append(
                f"{source}#chunk{chunk_index}"
                f"(retrieval={retrieval_rank},rerank={rerank_rank})"
            )
        return labels

    @staticmethod
    def _annotate_retrieval_rank(docs: list[Document]) -> list[Document]:
        for rank, doc in enumerate(docs, start=1):
            metadata = dict(doc.metadata or {})
            metadata["retrieval_rank"] = rank
            doc.metadata = metadata
        return docs

    def _limit_context_documents(self, docs: list[Document]) -> list[Document]:
        if self.settings.rerank_top_n <= 0:
            return docs
        return docs[: min(self.settings.rerank_top_n, len(docs))]

    def _expand_context_documents(self, docs: list[Document]) -> list[Document]:
        expanded_docs = self.vector_service.expand_with_neighbors(
            docs,
            neighbor_window=self.settings.retrieval_neighbor_chunks,
        )
        logger.info(
            "context expanded anchors=%s expanded=%s neighbor_window=%s order=%s",
            len(docs),
            len(expanded_docs),
            self.settings.retrieval_neighbor_chunks,
            self._doc_debug_labels(expanded_docs),
        )
        return expanded_docs

    @staticmethod
    def _coerce_score(value) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None

    def _extract_rerank_scores(self, docs: list[Document]) -> list[float]:
        scores: list[float] = []
        for doc in docs:
            score = self._coerce_score((doc.metadata or {}).get("rerank_score"))
            if score is not None:
                scores.append(score)
        return scores

    def _assess_retrieval_quality(
        self, docs: list[Document]
    ) -> RetrievalQualityAssessment:
        if not docs:
            return RetrievalQualityAssessment(
                label="empty",
                should_rewrite=True,
                reason="no_documents",
                top1_score=None,
                top3_avg_score=None,
                doc_count=0,
            )

        scores = self._extract_rerank_scores(docs)
        min_docs = max(getattr(self.settings, "rewrite_min_reranked_docs", 3), 1)

        if not scores:
            should_rewrite = len(docs) < min_docs
            return RetrievalQualityAssessment(
                label="medium" if not should_rewrite else "low",
                should_rewrite=should_rewrite,
                reason="missing_rerank_scores"
                if not should_rewrite
                else "insufficient_docs_without_scores",
                top1_score=None,
                top3_avg_score=None,
                doc_count=len(docs),
            )

        top1_score = scores[0]
        top3_scores = scores[: min(3, len(scores))]
        top3_avg_score = sum(top3_scores) / len(top3_scores)
        high_top1 = getattr(self.settings, "rewrite_quality_top1_threshold", 0.7)
        high_top3 = getattr(
            self.settings, "rewrite_quality_top3_avg_threshold", 0.55
        )
        low_top1 = getattr(self.settings, "rewrite_low_top1_threshold", 0.45)
        low_top3 = getattr(self.settings, "rewrite_low_top3_avg_threshold", 0.35)

        if len(docs) >= min_docs and top1_score >= high_top1 and top3_avg_score >= high_top3:
            return RetrievalQualityAssessment(
                label="high",
                should_rewrite=False,
                reason="high_quality_retrieval",
                top1_score=top1_score,
                top3_avg_score=top3_avg_score,
                doc_count=len(docs),
            )

        if len(docs) < 2 or top1_score < low_top1 or top3_avg_score < low_top3:
            return RetrievalQualityAssessment(
                label="low",
                should_rewrite=True,
                reason="low_quality_retrieval",
                top1_score=top1_score,
                top3_avg_score=top3_avg_score,
                doc_count=len(docs),
            )

        return RetrievalQualityAssessment(
            label="medium",
            should_rewrite=True,
            reason="medium_quality_retrieval",
            top1_score=top1_score,
            top3_avg_score=top3_avg_score,
            doc_count=len(docs),
        )

    @staticmethod
    def _assessment_rank(assessment: RetrievalQualityAssessment) -> int:
        rank_map = {"empty": 0, "low": 1, "medium": 2, "high": 3}
        return rank_map.get(assessment.label, 0)

    def _choose_better_query(
        self,
        *,
        original_query: str,
        original_docs: list[Document],
        rewritten_query: str,
        rewritten_docs: list[Document],
    ) -> tuple[str, list[Document]]:
        original_assessment = self._assess_retrieval_quality(original_docs)
        rewritten_assessment = self._assess_retrieval_quality(rewritten_docs)
        logger.info(
            (
                "rewrite comparison original_query=%s original_quality=%s original_top1=%s "
                "original_top3_avg=%s rewritten_query=%s rewritten_quality=%s "
                "rewritten_top1=%s rewritten_top3_avg=%s"
            ),
            self._short_query(original_query),
            original_assessment.label,
            original_assessment.top1_score,
            original_assessment.top3_avg_score,
            self._short_query(rewritten_query),
            rewritten_assessment.label,
            rewritten_assessment.top1_score,
            rewritten_assessment.top3_avg_score,
        )

        original_rank = self._assessment_rank(original_assessment)
        rewritten_rank = self._assessment_rank(rewritten_assessment)
        if rewritten_rank > original_rank:
            return rewritten_query, rewritten_docs
        if rewritten_rank < original_rank:
            return original_query, original_docs

        compare_margin = getattr(self.settings, "rewrite_compare_margin", 0.08)
        original_top1 = original_assessment.top1_score or 0.0
        rewritten_top1 = rewritten_assessment.top1_score or 0.0
        original_top3_avg = original_assessment.top3_avg_score or 0.0
        rewritten_top3_avg = rewritten_assessment.top3_avg_score or 0.0
        if (
            rewritten_top1 >= original_top1 + compare_margin
            or rewritten_top3_avg >= original_top3_avg + compare_margin
        ):
            return rewritten_query, rewritten_docs
        return original_query, original_docs

    @staticmethod
    def _build_skipped_rewrite_result(query: str, reason: str) -> QueryRewriteResult:
        return QueryRewriteResult(
            original_query=query,
            rewritten_query=query,
            rewrite_reason=reason,
            used_history=False,
            fallback_used=False,
        )

    async def _retrieve_and_rerank(self, query: str) -> list[Document]:
        started_at = perf_counter()
        docs = await asyncio.to_thread(
            self.vector_service.retrieve,
            query,
            top_k=self.settings.retrieve_top_k,
        )
        docs = self._annotate_retrieval_rank(list(docs))
        retrieval_elapsed_ms = (perf_counter() - started_at) * 1000
        logger.info(
            "retrieval completed query=%s candidates=%s elapsed_ms=%.2f order=%s",
            self._short_query(query),
            len(docs),
            retrieval_elapsed_ms,
            self._doc_debug_labels(docs),
        )

        if not docs:
            return []

        if not self.settings.rerank_enabled:
            limited_docs = self._limit_context_documents(docs)
            logger.info(
                "rerank skipped reason=disabled returned=%s",
                len(limited_docs),
            )
            return self._expand_context_documents(limited_docs)

        if len(docs) < self.settings.rerank_min_docs:
            limited_docs = self._limit_context_documents(docs)
            logger.info(
                "rerank skipped reason=insufficient_candidates candidates=%s min_docs=%s returned=%s",
                len(docs),
                self.settings.rerank_min_docs,
                len(limited_docs),
            )
            return self._expand_context_documents(limited_docs)

        order_before = self._doc_debug_labels(docs)
        rerank_started_at = perf_counter()
        reranked_docs = await self.rerank_service.rerank(query, docs)
        rerank_elapsed_ms = (perf_counter() - rerank_started_at) * 1000
        logger.info(
            "rerank completed query=%s returned=%s elapsed_ms=%.2f order_before=%s order_after=%s",
            self._short_query(query),
            len(reranked_docs),
            rerank_elapsed_ms,
            order_before,
            self._doc_debug_labels(reranked_docs),
        )
        return self._expand_context_documents(reranked_docs)

    async def _prepare_chain_inputs(self, prompt: str, session_id: str) -> dict:
        history = self._get_message_history(session_id).messages
        original_docs = await self._retrieve_and_rerank(prompt)
        original_assessment = self._assess_retrieval_quality(original_docs)
        logger.info(
            (
                "rewrite gate query=%s quality=%s should_rewrite=%s reason=%s "
                "top1=%s top3_avg=%s doc_count=%s"
            ),
            self._short_query(prompt),
            original_assessment.label,
            original_assessment.should_rewrite,
            original_assessment.reason,
            original_assessment.top1_score,
            original_assessment.top3_avg_score,
            original_assessment.doc_count,
        )

        if not original_assessment.should_rewrite:
            rewrite_result = self._build_skipped_rewrite_result(
                prompt, "skipped_high_quality"
            )
            selected_query = prompt
            selected_docs = original_docs
        else:
            rewrite_result = await self.query_rewrite_service.rewrite(prompt, history)
            selected_query = prompt
            selected_docs = original_docs
            if rewrite_result.rewritten_query != prompt:
                rewritten_docs = await self._retrieve_and_rerank(
                    rewrite_result.rewritten_query
                )
                selected_query, selected_docs = self._choose_better_query(
                    original_query=prompt,
                    original_docs=original_docs,
                    rewritten_query=rewrite_result.rewritten_query,
                    rewritten_docs=rewritten_docs,
                )

        return {
            "original_input": prompt,
            "rewritten_input": selected_query,
            "rewrite_result": rewrite_result,
            "context": self._format_documents(selected_docs),
        }

    async def invoke(self, prompt: str, session_id: str) -> str:
        chain_inputs = await self._prepare_chain_inputs(prompt, session_id)
        return await self.chain_with_history.ainvoke(
            chain_inputs,
            config={"configurable": {"session_id": session_id}},
        )

    async def astream(self, prompt: str, session_id: str) -> AsyncIterator[str]:
        chain_inputs = await self._prepare_chain_inputs(prompt, session_id)
        async for chunk in self.chain_with_history.astream(
            chain_inputs,
            config={"configurable": {"session_id": session_id}},
        ):
            if chunk:
                yield chunk
