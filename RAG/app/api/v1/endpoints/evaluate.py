from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_dataset_generator,
    get_evaluation_repository,
    get_evaluation_runtime_factory,
    get_evaluation_task_manager,
    get_kb_service,
    get_ragas_runner,
)
from app.core.config import get_settings
from app.schemas.evaluate import (
    DatasetGenerateRequest,
    EvaluationDatasetResponse,
    EvaluationDatasetSummary,
    EvaluationRunRequest,
    EvaluationRunResponse,
    EvaluationTaskResponse,
    SampleEvaluationResultResponse,
)
from app.services.knowledge_base import KnowledgeBaseServer
from evaluate.models import EvaluationDataset, EvaluationRun
from evaluate.dataset_generator import EvaluationDatasetGenerator
from evaluate.ragas_runner import RagasEvaluationRunner
from evaluate.repository import FileEvaluationRepository
from evaluate.runtime_factory import EvaluationRuntimeFactory
from evaluate.task_manager import EvaluationTaskManager


router = APIRouter(tags=["evaluate"])


@router.post(
    "/evaluate/datasets/generate",
    response_model=EvaluationTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="创建评估数据集生成任务",
)
async def create_dataset_generation_task(
    payload: DatasetGenerateRequest,
    repository: FileEvaluationRepository = Depends(get_evaluation_repository),
    task_manager: EvaluationTaskManager = Depends(get_evaluation_task_manager),
    dataset_generator: EvaluationDatasetGenerator = Depends(get_dataset_generator),
    kb: KnowledgeBaseServer = Depends(get_kb_service),
) -> EvaluationTaskResponse:
    settings = get_settings()
    dataset_id = _build_resource_id("dataset")
    pending_dataset = EvaluationDataset(
        dataset_id=dataset_id,
        name=payload.name,
        source_document_ids=payload.source_document_ids,
        generator_model=payload.generator_model
        or settings.evaluation_dataset_model_name
        or settings.chat_model_name,
        status="pending",
        created_at=_now(),
        updated_at=_now(),
        sample_count=0,
        version=1,
        samples=[],
        error=None,
    )
    repository.save_dataset(pending_dataset)

    async def job(report_progress):
        try:
            await report_progress(0.1, "读取知识库文档")
            source_documents = _resolve_source_documents(kb, payload.source_document_ids)
            if not source_documents:
                raise ValueError("未找到可用于生成评估集的知识库文档")

            await report_progress(0.4, "生成评估样本")
            dataset = await dataset_generator.generate(
                name=payload.name,
                source_documents=source_documents,
                source_document_ids=payload.source_document_ids,
                generator_model=pending_dataset.generator_model,
                sample_count=payload.sample_count,
                dataset_id=dataset_id,
            )
            repository.save_dataset(dataset)
            return {"dataset_id": dataset.dataset_id}
        except Exception as exc:
            repository.save_dataset(
                pending_dataset.model_copy(
                    update={
                        "status": "failed",
                        "updated_at": _now(),
                        "error": str(exc),
                    }
                )
            )
            raise

    task = await task_manager.create_task(
        task_type="generate_dataset",
        resource_id=dataset_id,
        message="数据集生成任务已创建",
        job=job,
    )
    return EvaluationTaskResponse(**task.model_dump())


@router.get(
    "/evaluate/datasets",
    response_model=list[EvaluationDatasetSummary],
    summary="查看评估数据集列表",
)
async def list_datasets(
    repository: FileEvaluationRepository = Depends(get_evaluation_repository),
) -> list[EvaluationDatasetSummary]:
    return [EvaluationDatasetSummary.from_domain(item) for item in repository.list_datasets()]


@router.get(
    "/evaluate/datasets/{dataset_id}",
    response_model=EvaluationDatasetResponse,
    summary="查看评估数据集详情",
)
async def get_dataset(
    dataset_id: str,
    repository: FileEvaluationRepository = Depends(get_evaluation_repository),
) -> EvaluationDatasetResponse:
    try:
        dataset = repository.get_dataset(dataset_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="评估数据集不存在") from exc
    return EvaluationDatasetResponse(**dataset.model_dump())


@router.post(
    "/evaluate/runs",
    response_model=EvaluationTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="创建评估运行任务",
)
async def create_evaluation_run_task(
    payload: EvaluationRunRequest,
    repository: FileEvaluationRepository = Depends(get_evaluation_repository),
    task_manager: EvaluationTaskManager = Depends(get_evaluation_task_manager),
    runtime_factory: EvaluationRuntimeFactory = Depends(get_evaluation_runtime_factory),
    ragas_runner: RagasEvaluationRunner = Depends(get_ragas_runner),
) -> EvaluationTaskResponse:
    settings = get_settings()
    try:
        dataset = repository.get_dataset(payload.dataset_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="评估数据集不存在") from exc

    run_id = _build_resource_id("run")
    metrics = payload.metrics or settings.evaluation_default_metrics
    pending_run = EvaluationRun(
        run_id=run_id,
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.version,
        status="pending",
        created_at=_now(),
        updated_at=_now(),
        completed_at=None,
        config_snapshot=payload.config_overrides,
        metrics_summary={},
        sample_count=dataset.sample_count,
        successful_sample_count=0,
        error=None,
    )
    repository.save_run(pending_run, sample_results=[])

    async def job(report_progress):
        try:
            await report_progress(0.1, "加载评估运行时")
            runtime = runtime_factory.create_runtime(
                config_overrides=payload.config_overrides
            )

            records = []
            total = max(len(dataset.samples), 1)
            for index, sample in enumerate(dataset.samples, start=1):
                progress = 0.1 + 0.6 * (index / total)
                await report_progress(progress, f"执行样本 {index}/{len(dataset.samples)}")
                record = await _build_evaluation_record(
                    run_id=run_id,
                    sample=sample.model_dump(mode="json"),
                    rag_service=runtime.rag_service,
                )
                records.append(record)

            await report_progress(0.85, "执行 ragas 指标")
            summary, sample_results = await ragas_runner.evaluate(
                records=records,
                metrics=metrics,
            )
            completed_run = pending_run.model_copy(
                update={
                    "status": "completed",
                    "updated_at": _now(),
                    "completed_at": _now(),
                    "config_snapshot": runtime.config_snapshot,
                    "metrics_summary": summary,
                    "sample_count": len(sample_results),
                    "successful_sample_count": len(
                        [item for item in sample_results if not item.error]
                    ),
                    "error": None,
                }
            )
            repository.save_run(completed_run, sample_results=sample_results)
            return {"run_id": completed_run.run_id}
        except Exception as exc:
            repository.save_run(
                pending_run.model_copy(
                    update={
                        "status": "failed",
                        "updated_at": _now(),
                        "completed_at": _now(),
                        "error": str(exc),
                    }
                ),
                sample_results=[],
            )
            raise

    task = await task_manager.create_task(
        task_type="run_evaluation",
        resource_id=run_id,
        message="评估任务已创建",
        job=job,
    )
    return EvaluationTaskResponse(**task.model_dump())


@router.get(
    "/evaluate/tasks/{task_id}",
    response_model=EvaluationTaskResponse,
    summary="查看评估任务状态",
)
async def get_task(
    task_id: str,
    repository: FileEvaluationRepository = Depends(get_evaluation_repository),
) -> EvaluationTaskResponse:
    try:
        task = repository.get_task(task_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="评估任务不存在") from exc
    return EvaluationTaskResponse(**task.model_dump())


@router.get(
    "/evaluate/runs/{run_id}",
    response_model=EvaluationRunResponse,
    summary="查看评估运行详情",
)
async def get_run(
    run_id: str,
    repository: FileEvaluationRepository = Depends(get_evaluation_repository),
) -> EvaluationRunResponse:
    try:
        run = repository.get_run(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="评估运行不存在") from exc
    return EvaluationRunResponse(**run.model_dump())


@router.get(
    "/evaluate/runs/{run_id}/samples",
    response_model=list[SampleEvaluationResultResponse],
    summary="查看评估样本结果详情",
)
async def get_run_samples(
    run_id: str,
    repository: FileEvaluationRepository = Depends(get_evaluation_repository),
) -> list[SampleEvaluationResultResponse]:
    try:
        samples = repository.get_run_samples(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="评估样本结果不存在") from exc
    return [SampleEvaluationResultResponse(**item.model_dump()) for item in samples]


def _resolve_source_documents(
    kb: KnowledgeBaseServer,
    source_document_ids: list[str],
) -> list[dict]:
    documents = kb._get_document_groups()
    if not source_document_ids:
        return documents
    allowed = set(source_document_ids)
    return [item for item in documents if item.get("document_id") in allowed]


async def _build_evaluation_record(
    *,
    run_id: str,
    sample: dict,
    rag_service,
) -> dict:
    session_id = f"eval-{run_id}-{sample['sample_id']}"
    chain_inputs = await rag_service._prepare_chain_inputs(sample["question"], session_id)
    answer = await rag_service.chain_with_history.ainvoke(
        chain_inputs,
        config={"configurable": {"session_id": session_id}},
    )
    context = chain_inputs.get("context")
    return {
        "sample_id": sample["sample_id"],
        "question": sample["question"],
        "answer": str(answer),
        "reference_answer": sample["reference_answer"],
        "retrieved_contexts": [] if context == "没有相关文档" else [context],
        "reference_contexts": sample.get("reference_contexts", []),
    }


def _build_resource_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def _now() -> str:
    return datetime.utcnow().isoformat()
