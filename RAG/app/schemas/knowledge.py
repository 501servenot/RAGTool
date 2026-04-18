from pydantic import BaseModel, Field


class KnowledgeDocumentItem(BaseModel):
    document_id: str = Field(..., description="文档唯一标识")
    filename: str = Field(..., description="文档文件名")
    chunk_count: int = Field(..., description="该文档在向量库中的切片数量")
    create_time: str = Field(..., description="创建时间")
    operator: str = Field(..., description="操作人")


class KnowledgeBaseSummaryResponse(BaseModel):
    document_count: int = Field(..., description="当前知识库中的文档数量")
    chunk_count: int = Field(..., description="当前知识库中的总切片数量")
    documents: list[KnowledgeDocumentItem] = Field(
        default_factory=list, description="知识库文档列表"
    )


class DeleteKnowledgeDocumentResponse(BaseModel):
    document_id: str = Field(..., description="被删除的文档唯一标识")
    filename: str = Field(..., description="被删除的文件名")
    deleted_chunk_count: int = Field(..., description="被删除的向量切片数量")
    message: str = Field(..., description="删除结果")
