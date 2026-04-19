from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


DatasetStatus = Literal["pending", "running", "completed", "failed"]
RunStatus = Literal["pending", "running", "completed", "failed", "cancelled"]
TaskStatus = Literal["pending", "running", "completed", "failed", "cancelled"]
TaskType = Literal["generate_dataset", "run_evaluation"]


class EvaluationSample(BaseModel):
    sample_id: str = Field(..., description="样本唯一标识")
    question: str = Field(..., description="评估问题")
    reference_answer: str = Field(..., description="参考答案")
    reference_contexts: list[str] = Field(
        default_factory=list, description="参考上下文列表"
    )
    source_document_id: str = Field(..., description="样本来源文档 ID")
    source_chunk_ids: list[str] = Field(
        default_factory=list, description="样本来源 chunk ID 列表"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="附加元数据")


class EvaluationDataset(BaseModel):
    dataset_id: str = Field(..., description="数据集唯一标识")
    name: str = Field(..., description="数据集名称")
    source_document_ids: list[str] = Field(
        default_factory=list, description="来源文档 ID 列表"
    )
    generator_model: str = Field(..., description="用于生成数据集的模型")
    status: DatasetStatus = Field(..., description="数据集状态")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    sample_count: int = Field(..., description="样本数量")
    version: int = Field(..., description="数据集版本")
    samples: list[EvaluationSample] = Field(
        default_factory=list, description="数据集样本列表"
    )
    error: str | None = Field(default=None, description="生成失败时的错误信息")


class SampleEvaluationResult(BaseModel):
    sample_id: str = Field(..., description="样本唯一标识")
    question: str = Field(..., description="评估问题")
    answer: str = Field(..., description="RAG 输出答案")
    reference_answer: str = Field(..., description="参考答案")
    retrieved_contexts: list[str] = Field(
        default_factory=list, description="检索到的上下文"
    )
    reference_contexts: list[str] = Field(
        default_factory=list, description="参考上下文"
    )
    metric_scores: dict[str, float | None] = Field(
        default_factory=dict, description="样本级指标得分"
    )
    error: str | None = Field(default=None, description="样本评估错误")


class EvaluationRun(BaseModel):
    run_id: str = Field(..., description="评估运行唯一标识")
    dataset_id: str = Field(..., description="所属数据集 ID")
    dataset_version: int = Field(..., description="评估时使用的数据集版本")
    status: RunStatus = Field(..., description="评估运行状态")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    completed_at: str | None = Field(default=None, description="完成时间")
    config_snapshot: dict[str, Any] = Field(
        default_factory=dict, description="运行时配置快照"
    )
    metrics_summary: dict[str, float | None] = Field(
        default_factory=dict, description="聚合指标摘要"
    )
    sample_count: int = Field(..., description="总样本数")
    successful_sample_count: int = Field(..., description="成功样本数")
    error: str | None = Field(default=None, description="运行级错误")


class EvaluationTask(BaseModel):
    task_id: str = Field(..., description="任务唯一标识")
    task_type: TaskType = Field(..., description="任务类型")
    status: TaskStatus = Field(..., description="任务状态")
    progress: float = Field(..., ge=0.0, le=1.0, description="任务进度")
    message: str = Field(..., description="当前任务描述")
    resource_id: str | None = Field(default=None, description="关联资源 ID")
    result_ref: dict[str, Any] | None = Field(
        default=None, description="完成后返回的结果引用"
    )
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    error: str | None = Field(default=None, description="任务错误信息")
