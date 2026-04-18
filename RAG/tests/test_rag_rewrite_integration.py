import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableLambda


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from app.services.query_rewrite import QueryRewriteResult
from app.services.rag import RAGservice


class FakeHistory:
    def __init__(self, messages):
        self.messages = messages


class FakeRewriteService:
    def __init__(self, result: QueryRewriteResult):
        self.result = result
        self.calls = []

    async def rewrite(self, query, history):
        self.calls.append((query, history))
        return self.result


class FakeVectorService:
    def __init__(self):
        self.queries = []

    def get_retriever(self):
        return RunnableLambda(self._retrieve)

    def _retrieve(self, query):
        self.queries.append(query)
        return []


class RecordingChatModel:
    def __init__(self):
        self.calls = []
        self.runnable = RunnableLambda(self._respond)

    def _respond(self, prompt_value):
        self.calls.append(prompt_value)
        return AIMessage(content="测试回答")


class RAGRewriteIntegrationTest(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _make_settings():
        return SimpleNamespace(
            rerank_top_n=5,
            retrieval_neighbor_chunks=0,
            rewrite_quality_top1_threshold=0.7,
            rewrite_quality_top3_avg_threshold=0.55,
            rewrite_low_top1_threshold=0.45,
            rewrite_low_top3_avg_threshold=0.35,
            rewrite_min_reranked_docs=3,
            rewrite_compare_margin=0.08,
        )

    @staticmethod
    def _make_docs(scores: list[float]) -> list[Document]:
        docs = []
        for index, score in enumerate(scores, start=1):
            docs.append(
                Document(
                    page_content=f"doc-{index}",
                    metadata={
                        "source": f"doc-{index}.md",
                        "chunk_index": index,
                        "rerank_score": score,
                    },
                )
            )
        return docs

    async def test_prepare_chain_inputs_uses_rewritten_query(self):
        rewrite_result = QueryRewriteResult(
            original_query="这个怎么部署",
            rewritten_query="如何部署 RAG 服务",
            rewrite_reason="history_disambiguation",
            used_history=True,
            fallback_used=False,
        )
        service = RAGservice.__new__(RAGservice)
        service.settings = self._make_settings()
        service.query_rewrite_service = FakeRewriteService(rewrite_result)
        service._get_message_history = lambda session_id: FakeHistory(
            [HumanMessage(content="上一轮我们在聊 RAG 服务部署")]
        )
        service._format_documents = RAGservice._format_documents

        async def fake_retrieve(query):
            if query == "这个怎么部署":
                return self._make_docs([0.35, 0.31, 0.26])
            if query == "如何部署 RAG 服务":
                return self._make_docs([0.84, 0.79, 0.74])
            raise AssertionError(f"unexpected query: {query}")

        service._retrieve_and_rerank = fake_retrieve

        payload = await service._prepare_chain_inputs("这个怎么部署", "session-1")

        self.assertEqual(payload["original_input"], "这个怎么部署")
        self.assertEqual(payload["rewritten_input"], "如何部署 RAG 服务")
        self.assertIs(payload["rewrite_result"], rewrite_result)
        self.assertEqual(service.query_rewrite_service.calls[0][0], "这个怎么部署")
        self.assertEqual(service.query_rewrite_service.calls[0][1][0].content, "上一轮我们在聊 RAG 服务部署")

    async def test_prepare_chain_inputs_skips_rewrite_when_original_retrieval_is_high_quality(self):
        rewrite_result = QueryRewriteResult(
            original_query="这个怎么部署",
            rewritten_query="如何部署 RAG 服务",
            rewrite_reason="rewritten",
            used_history=True,
            fallback_used=False,
        )
        service = RAGservice.__new__(RAGservice)
        service.settings = self._make_settings()
        service.query_rewrite_service = FakeRewriteService(rewrite_result)
        service._get_message_history = lambda session_id: FakeHistory(
            [HumanMessage(content="上一轮我们在聊 RAG 服务部署")]
        )
        service._format_documents = RAGservice._format_documents

        async def fake_retrieve(query):
            self.assertEqual(query, "这个怎么部署")
            return self._make_docs([0.86, 0.78, 0.73])

        service._retrieve_and_rerank = fake_retrieve

        payload = await service._prepare_chain_inputs("这个怎么部署", "session-1")

        self.assertEqual(payload["original_input"], "这个怎么部署")
        self.assertEqual(payload["rewritten_input"], "这个怎么部署")
        self.assertEqual(payload["rewrite_result"].rewrite_reason, "skipped_high_quality")
        self.assertEqual(service.query_rewrite_service.calls, [])

    async def test_prepare_chain_inputs_rewrites_when_original_retrieval_score_is_low(self):
        rewrite_result = QueryRewriteResult(
            original_query="这个怎么部署",
            rewritten_query="如何部署 RAG 服务",
            rewrite_reason="rewritten",
            used_history=True,
            fallback_used=False,
        )
        service = RAGservice.__new__(RAGservice)
        service.settings = self._make_settings()
        service.query_rewrite_service = FakeRewriteService(rewrite_result)
        service._get_message_history = lambda session_id: FakeHistory(
            [HumanMessage(content="上一轮我们在聊 RAG 服务部署")]
        )
        service._format_documents = RAGservice._format_documents

        async def fake_retrieve(query):
            if query == "这个怎么部署":
                return self._make_docs([0.32, 0.28, 0.21])
            if query == "如何部署 RAG 服务":
                return self._make_docs([0.84, 0.80, 0.75])
            raise AssertionError(f"unexpected query: {query}")

        service._retrieve_and_rerank = fake_retrieve

        payload = await service._prepare_chain_inputs("这个怎么部署", "session-1")

        self.assertEqual(payload["rewritten_input"], "如何部署 RAG 服务")
        self.assertIs(payload["rewrite_result"], rewrite_result)
        self.assertEqual(service.query_rewrite_service.calls[0][0], "这个怎么部署")

    async def test_chain_uses_rewritten_query_for_retrieval_and_answer_prompt(self):
        rewrite_result = QueryRewriteResult(
            original_query="这个怎么部署",
            rewritten_query="如何部署 RAG 服务",
            rewrite_reason="rewritten",
            used_history=True,
            fallback_used=False,
        )
        vector_service = FakeVectorService()
        chat_model = RecordingChatModel()

        service = RAGservice(
            vector_service=vector_service,
            chat_model=chat_model.runnable,
            query_rewrite_service=FakeRewriteService(rewrite_result),
        )

        await service.chain.ainvoke(
            {
                "original_input": "这个怎么部署",
                "rewritten_input": "如何部署 RAG 服务",
                "history": [],
                "context": "测试上下文",
            }
        )

        prompt_text = chat_model.calls[0].to_messages()[-1].content
        self.assertIn("用户原始问题：这个怎么部署", prompt_text)
        self.assertIn("标准化问题：如何部署 RAG 服务", prompt_text)
