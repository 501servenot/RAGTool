from typing import Any, Literal

from pydantic import BaseModel, Field


ConfigValue = Any
ProviderKind = Literal["openai_compatible", "dashscope"]
ConfigInputType = Literal[
    "text",
    "password",
    "number",
    "checkbox",
    "json-textarea",
]


class ConfigFieldSchema(BaseModel):
    key: str = Field(..., description="配置字段名")
    label: str = Field(..., description="展示名称")
    description: str = Field(..., description="配置说明")
    group: str = Field(..., description="分组名称")
    input_type: ConfigInputType = Field(..., description="前端输入控件类型")
    advanced: bool = Field(..., description="是否为高级配置")
    sensitive: bool = Field(..., description="是否为敏感字段")
    nullable: bool = Field(..., description="是否允许设置为空")
    value: ConfigValue = Field(..., description="当前配置值")


class ConfigStateResponse(BaseModel):
    fields: list[ConfigFieldSchema] = Field(..., description="配置字段定义和当前值")
    model_configs: dict[str, "EditableModelConfig"] = Field(
        ..., description="结构化模型配置"
    )


class EditableModelConfig(BaseModel):
    provider_kind: ProviderKind = Field(..., description="模型 provider 类型")
    model: str = Field(..., description="模型名称")
    base_url: str = Field("", description="模型接口 URL")
    api_key: str = Field("", description="模型接口密钥")


class ConfigUpdateRequest(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict, description="要更新的配置值")
    model_configs: dict[str, EditableModelConfig] = Field(
        default_factory=dict, description="结构化模型配置"
    )


class ConfigUpdateResponse(BaseModel):
    message: str = Field(..., description="更新结果")
    fields: list[ConfigFieldSchema] = Field(..., description="刷新后的配置字段")
    model_configs: dict[str, EditableModelConfig] = Field(
        ..., description="刷新后的结构化模型配置"
    )
