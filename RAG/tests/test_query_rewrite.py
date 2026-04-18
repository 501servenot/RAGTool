import sys
import unittest
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from app.services.query_rewrite import QueryRewriteService


class FakeModel:
    def __init__(self, response: str | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls = []

    async def ainvoke(self, messages):
        self.calls.append(messages)
        if self.error is not None:
            raise self.error
        return AIMessage(content=self.response or "")


class QueryRewriteServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_returns_original_query_when_model_returns_empty(self):
        service = QueryRewriteService(
            chat_model=FakeModel(response="   "),
            enabled=True,
            history_turns=2,
            max_query_length=200,
            fallback_to_original=True,
        )

        result = await service.rewrite("这个怎么部署", [])

        self.assertEqual(result.original_query, "这个怎么部署")
        self.assertEqual(result.rewritten_query, "这个怎么部署")
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.rewrite_reason, "empty_rewrite")

    async def test_uses_recent_history_for_ambiguous_query(self):
        model = FakeModel(response="如何部署 RAG 服务")
        service = QueryRewriteService(
            chat_model=model,
            enabled=True,
            history_turns=2,
            max_query_length=200,
            fallback_to_original=True,
        )

        history = [
            HumanMessage(content="我们先讨论前端颜色"),
            AIMessage(content="可以调整成深色主题"),
            HumanMessage(content="现在说 RAG 服务部署"),
            AIMessage(content="可以用 FastAPI 启动"),
            HumanMessage(content="具体命令是什么"),
            AIMessage(content="可以使用 uvicorn app.main:app --reload"),
        ]

        result = await service.rewrite("这个怎么部署", history)

        self.assertEqual(result.rewritten_query, "如何部署 RAG 服务")
        self.assertFalse(result.fallback_used)
        self.assertTrue(result.used_history)
        prompt_text = model.calls[0][-1].content
        self.assertIn("现在说 RAG 服务部署", prompt_text)
        self.assertIn("具体命令是什么", prompt_text)
        self.assertNotIn("我们先讨论前端颜色", prompt_text)

    async def test_uses_history_for_context_dependent_long_query(self):
        model = FakeModel(response="如何更稳妥地部署刚才讨论的 RAG 方案")
        service = QueryRewriteService(
            chat_model=model,
            enabled=True,
            history_turns=2,
            max_query_length=200,
            fallback_to_original=True,
        )

        history = [
            HumanMessage(content="我们刚才讨论的是 RAG 服务部署方案"),
            AIMessage(content="建议用 FastAPI 加反向代理部署"),
        ]

        result = await service.rewrite("按刚才那个方案，生产环境怎么部署更稳妥？", history)

        self.assertTrue(result.used_history)
        prompt_text = model.calls[0][-1].content
        self.assertIn("我们刚才讨论的是 RAG 服务部署方案", prompt_text)

    async def test_returns_original_query_when_model_raises_error(self):
        service = QueryRewriteService(
            chat_model=FakeModel(error=RuntimeError("boom")),
            enabled=True,
            history_turns=2,
            max_query_length=200,
            fallback_to_original=True,
        )

        result = await service.rewrite("这个怎么部署", [])

        self.assertEqual(result.rewritten_query, "这个怎么部署")
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.rewrite_reason, "model_error")

    async def test_skips_rewrite_for_long_query(self):
        service = QueryRewriteService(
            chat_model=FakeModel(response="不会被调用"),
            enabled=True,
            history_turns=2,
            max_query_length=10,
            fallback_to_original=True,
        )

        result = await service.rewrite("这是一个超过长度限制的问题文本", [])

        self.assertEqual(result.rewritten_query, "这是一个超过长度限制的问题文本")
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.rewrite_reason, "query_too_long")

    async def test_returns_original_query_when_rewritten_query_is_too_long(self):
        service = QueryRewriteService(
            chat_model=FakeModel(response="这是一个非常长的改写结果文本"),
            enabled=True,
            history_turns=2,
            max_query_length=10,
            fallback_to_original=True,
        )

        result = await service.rewrite("这个怎么部署", [])

        self.assertEqual(result.rewritten_query, "这个怎么部署")
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.rewrite_reason, "rewritten_query_too_long")
