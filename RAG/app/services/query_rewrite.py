import re
from dataclasses import dataclass
from typing import Iterable

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import get_settings


AMBIGUOUS_QUERY_PATTERN = re.compile(
    r"(这个|这个问题|这个功能|这个接口|它|它的|上述|上面|前面|这里|那这个|怎么弄|怎么做)$"
)


@dataclass(slots=True)
class QueryRewriteResult:
    original_query: str
    rewritten_query: str
    rewrite_reason: str
    used_history: bool
    fallback_used: bool


class QueryRewriteService:
    def __init__(
        self,
        chat_model=None,
        *,
        enabled: bool | None = None,
        history_turns: int | None = None,
        max_query_length: int | None = None,
        fallback_to_original: bool | None = None,
    ):
        settings = get_settings()
        rewrite_model_name = settings.rewrite_model_name or settings.chat_model_name

        self.chat_model = chat_model or ChatTongyi(model=rewrite_model_name)
        self.enabled = (
            settings.rewrite_enabled if enabled is None else enabled
        )
        self.history_turns = (
            settings.rewrite_history_turns if history_turns is None else history_turns
        )
        self.max_query_length = (
            settings.rewrite_max_query_length
            if max_query_length is None
            else max_query_length
        )
        self.fallback_to_original = (
            settings.rewrite_fallback_to_original
            if fallback_to_original is None
            else fallback_to_original
        )
        self.prompt_template = ChatPromptTemplate(
            [
                (
                    "system",
                    (
                        "你是 RAG 检索优化助手。"
                        "你的任务是把用户问题重写成更清晰、书面化、适合知识库检索和严谨回答的问题。"
                        "不要改变用户真实意图，不要补充无依据的新需求。"
                        "如果原问题已经清晰，请尽量保持原意并最小化改写。"
                        "你只能输出一个改写后的问题，不要输出解释。"
                    ),
                ),
                (
                    "user",
                    (
                        "最近对话历史：\n{history_text}\n\n"
                        "当前用户问题：{query}\n\n"
                        "请输出改写后的问题。"
                    ),
                ),
            ]
        )

    async def rewrite(
        self, query: str, history_messages: Iterable[BaseMessage]
    ) -> QueryRewriteResult:
        query = query.strip()
        history_messages = list(history_messages)

        if not self.enabled:
            return self._result(
                query, query, "rewrite_disabled", used_history=False, fallback_used=False
            )

        if self.max_query_length > 0 and len(query) > self.max_query_length:
            return self._fallback(query, "query_too_long", used_history=False)

        used_history = self._should_use_history(query) and bool(history_messages)
        history_text = (
            self._format_history(history_messages) if used_history else "无可用历史"
        )

        try:
            prompt_messages = self.prompt_template.format_messages(
                history_text=history_text,
                query=query,
            )
            response = await self.chat_model.ainvoke(prompt_messages)
            rewritten_query = self._extract_text(response).strip()
        except Exception:
            if not self.fallback_to_original:
                raise
            return self._fallback(query, "model_error", used_history=used_history)

        if not rewritten_query:
            return self._fallback(query, "empty_rewrite", used_history=used_history)

        if self.max_query_length > 0 and len(rewritten_query) > self.max_query_length:
            return self._fallback(
                query, "rewritten_query_too_long", used_history=used_history
            )

        if rewritten_query == query:
            return self._result(
                query,
                query,
                "query_unchanged",
                used_history=used_history,
                fallback_used=False,
            )

        return self._result(
            query,
            rewritten_query,
            "rewritten",
            used_history=used_history,
            fallback_used=False,
        )

    def _should_use_history(self, query: str) -> bool:
        compact_query = query.strip()
        return len(compact_query) <= 20 or bool(
            AMBIGUOUS_QUERY_PATTERN.search(compact_query)
        )

    def _format_history(self, history_messages: list[BaseMessage]) -> str:
        max_messages = max(self.history_turns, 0) * 2
        recent_messages = history_messages[-max_messages:] if max_messages else []
        formatted_messages = []

        for message in recent_messages:
            role = self._message_role(message)
            formatted_messages.append(f"{role}: {message.content}")

        return "\n".join(formatted_messages) if formatted_messages else "无可用历史"

    @staticmethod
    def _message_role(message: BaseMessage) -> str:
        role_map = {
            "human": "user",
            "ai": "assistant",
            "system": "system",
        }
        return role_map.get(message.type, message.type)

    @staticmethod
    def _extract_text(response) -> str:
        content = getattr(response, "content", response)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and "text" in item:
                    parts.append(str(item["text"]))
            return "".join(parts)
        return str(content)

    def _fallback(
        self, query: str, reason: str, *, used_history: bool
    ) -> QueryRewriteResult:
        if not self.fallback_to_original:
            raise ValueError(f"query rewrite failed: {reason}")
        return self._result(
            query, query, reason, used_history=used_history, fallback_used=True
        )

    @staticmethod
    def _result(
        original_query: str,
        rewritten_query: str,
        rewrite_reason: str,
        *,
        used_history: bool,
        fallback_used: bool,
    ) -> QueryRewriteResult:
        return QueryRewriteResult(
            original_query=original_query,
            rewritten_query=rewritten_query,
            rewrite_reason=rewrite_reason,
            used_history=used_history,
            fallback_used=fallback_used,
        )
