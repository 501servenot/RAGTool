from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="用户输入的提问")
    session_id: str = Field(..., min_length=1, description="会话唯一标识")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="模型返回的完整回答")


class ChatHistoryMessage(BaseModel):
    role: str = Field(..., description="消息角色，user 或 ai")
    content: str = Field(..., description="消息内容")


class ChatSessionSummary(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    title: str = Field(..., description="会话标题")
    updated_at: str = Field(..., description="会话最近更新时间")


class DeleteChatSessionResponse(BaseModel):
    session_id: str = Field(..., description="已删除的会话 ID")
    message: str = Field(..., description="删除结果")
