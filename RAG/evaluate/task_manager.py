from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
from uuid import uuid4

from evaluate.models import EvaluationTask
from evaluate.repository import FileEvaluationRepository


JobCallback = Callable[[Callable[[float, str], Awaitable[None]]], Awaitable[dict | None]]


class EvaluationTaskManager:
    def __init__(self, *, repository: FileEvaluationRepository):
        self.repository = repository
        self._running_tasks: dict[str, asyncio.Task] = {}

    async def create_task(
        self,
        *,
        task_type: str,
        resource_id: str | None,
        message: str,
        job: JobCallback,
    ) -> EvaluationTask:
        now = self._now()
        task = EvaluationTask(
            task_id=f"task-{uuid4().hex}",
            task_type=task_type,
            status="pending",
            progress=0.0,
            message=message,
            resource_id=resource_id,
            result_ref=None,
            created_at=now,
            updated_at=now,
            error=None,
        )
        self.repository.save_task(task)
        self._running_tasks[task.task_id] = asyncio.create_task(self._run(task, job))
        return task

    async def wait_for_task(self, task_id: str, *, timeout: float | None = None) -> None:
        task = self._running_tasks.get(task_id)
        if task is None:
            raise KeyError(task_id)
        await asyncio.wait_for(task, timeout=timeout)

    async def _run(self, task: EvaluationTask, job: JobCallback) -> None:
        current = self._persist_task(task, status="running", message=task.message)

        async def report_progress(progress: float, message: str) -> None:
            nonlocal current
            current = self._persist_task(
                current,
                progress=progress,
                message=message,
                status="running",
            )

        try:
            result_ref = await job(report_progress)
        except Exception as exc:
            self._persist_task(
                current,
                status="failed",
                message=str(exc),
                error=str(exc),
            )
            return

        self._persist_task(
            current,
            status="completed",
            progress=1.0,
            message="已完成",
            result_ref=result_ref,
            error=None,
        )

    def _persist_task(
        self,
        task: EvaluationTask,
        *,
        status: str,
        message: str,
        progress: float | None = None,
        result_ref: dict | None = None,
        error: str | None = None,
    ) -> EvaluationTask:
        updated = task.model_copy(
            update={
                "status": status,
                "message": message,
                "progress": task.progress if progress is None else progress,
                "updated_at": self._now(),
                "result_ref": result_ref if result_ref is not None else task.result_ref,
                "error": error,
            }
        )
        self.repository.save_task(updated)
        return updated

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat()
