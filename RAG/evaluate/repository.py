from __future__ import annotations

import json
from pathlib import Path

from evaluate.models import (
    EvaluationDataset,
    EvaluationRun,
    EvaluationTask,
    SampleEvaluationResult,
)


class FileEvaluationRepository:
    def __init__(self, *, base_path: Path | str):
        self.base_path = Path(base_path)
        self.datasets_dir = self.base_path / "datasets"
        self.runs_dir = self.base_path / "runs"
        self.tasks_dir = self.base_path / "tasks"
        self.artifacts_dir = self.base_path / "artifacts"

        for directory in (
            self.base_path,
            self.datasets_dir,
            self.runs_dir,
            self.tasks_dir,
            self.artifacts_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def save_dataset(self, dataset: EvaluationDataset) -> None:
        self._write_json(
            self.datasets_dir / f"{dataset.dataset_id}.json",
            dataset.model_dump(mode="json"),
        )

    def get_dataset(self, dataset_id: str) -> EvaluationDataset:
        payload = self._read_json(self.datasets_dir / f"{dataset_id}.json")
        return EvaluationDataset.model_validate(payload)

    def list_datasets(self) -> list[EvaluationDataset]:
        datasets = [
            EvaluationDataset.model_validate(self._read_json(path))
            for path in self.datasets_dir.glob("*.json")
        ]
        return sorted(datasets, key=lambda item: item.created_at, reverse=True)

    def save_run(
        self,
        run: EvaluationRun,
        *,
        sample_results: list[SampleEvaluationResult] | None = None,
    ) -> None:
        self._write_json(
            self.runs_dir / f"{run.run_id}.json",
            run.model_dump(mode="json"),
        )

        if sample_results is not None:
            sample_payload = [item.model_dump(mode="json") for item in sample_results]
            artifact_dir = self.artifacts_dir / run.run_id
            artifact_dir.mkdir(parents=True, exist_ok=True)
            self._write_json(artifact_dir / "samples.json", sample_payload)

    def get_run(self, run_id: str) -> EvaluationRun:
        payload = self._read_json(self.runs_dir / f"{run_id}.json")
        return EvaluationRun.model_validate(payload)

    def get_run_samples(self, run_id: str) -> list[SampleEvaluationResult]:
        payload = self._read_json(self.artifacts_dir / run_id / "samples.json")
        return [SampleEvaluationResult.model_validate(item) for item in payload]

    def list_runs(self) -> list[EvaluationRun]:
        runs = [
            EvaluationRun.model_validate(self._read_json(path))
            for path in self.runs_dir.glob("*.json")
        ]
        return sorted(runs, key=lambda item: item.created_at, reverse=True)

    def save_task(self, task: EvaluationTask) -> None:
        self._write_json(
            self.tasks_dir / f"{task.task_id}.json",
            task.model_dump(mode="json"),
        )

    def get_task(self, task_id: str) -> EvaluationTask:
        payload = self._read_json(self.tasks_dir / f"{task_id}.json")
        return EvaluationTask.model_validate(payload)

    def list_tasks(self) -> list[EvaluationTask]:
        tasks = [
            EvaluationTask.model_validate(self._read_json(path))
            for path in self.tasks_dir.glob("*.json")
        ]
        return sorted(tasks, key=lambda item: item.created_at, reverse=True)

    @staticmethod
    def _read_json(path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
