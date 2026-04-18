from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    filename: str = Field(..., description="上传的文件名")
    size_kb: float = Field(..., description="文件大小（KB）")
    content_type: str = Field(..., description="文件 MIME 类型")
    message: str = Field(..., description="处理结果：成功 / 内容已存在")
