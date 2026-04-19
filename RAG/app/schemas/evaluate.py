from typing import Any

from pydantic import BaseModel, Field

from evaluate.models import EvaluationDataset, EvaluationRun, EvaluationTask, SampleEvaluationResult


class DatasetGenerateRequest(BaseModel):
    name: str = Field(..., min_length=1, description="数据集名称")
    source_document_ids: list[str] = Field(
        default_factory=list, description="参与生成的知识库文档 ID 列表"
    )
    sample_count: int = Field(..., ge=1, description="目标样本数")
    generator_model: str | None = Field(
        default=None, description="覆盖默认的数据集生成模型"
    )


class EvaluationRunRequest(BaseModel):
    dataset_id: str = Field(..., min_length=1, description="待评估的数据集 ID")
    metrics: list[str] | None = Field(
        default=None, description="本次运行启用的 ragas 指标列表"
    )
    config_overrides: dict[str, Any] = Field(
        default_factory=dict, description="本次运行的配置覆盖项"
    )


class EvaluationDatasetSummary(BaseModel):
    dataset_id: str
    name: str
    source_document_ids: list[str]
    generator_model: str
    status: str
    created_at: str
    updated_at: str
    sample_count: int
    version: int
    error: str | None = None

    @classmethod
    def from_domain(cls, dataset: EvaluationDataset) -> "EvaluationDatasetSummary":
        return cls(**dataset.model_dump(exclude={"samples"}))


class EvaluationTaskResponse(EvaluationTask):
    pass


class EvaluationDatasetResponse(EvaluationDataset):
    pass


class EvaluationRunResponse(EvaluationRun):
    pass


class SampleEvaluationResultResponse(SampleEvaluationResult):
    pass
