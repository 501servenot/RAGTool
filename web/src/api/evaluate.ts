export interface EvaluationTask {
  task_id: string
  task_type: 'generate_dataset' | 'run_evaluation'
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  message: string
  resource_id: string | null
  result_ref: Record<string, unknown> | null
  created_at: string
  updated_at: string
  error: string | null
}

export interface EvaluationDatasetSummary {
  dataset_id: string
  name: string
  source_document_ids: string[]
  generator_model: string
  status: string
  created_at: string
  updated_at: string
  sample_count: number
  version: number
  error: string | null
}

export interface EvaluationSample {
  sample_id: string
  question: string
  reference_answer: string
  reference_contexts: string[]
  source_document_id: string
  source_chunk_ids: string[]
  metadata: Record<string, unknown>
}

export interface EvaluationDatasetDetail extends EvaluationDatasetSummary {
  samples: EvaluationSample[]
}

export interface EvaluationRun {
  run_id: string
  dataset_id: string
  dataset_version: number
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  created_at: string
  updated_at: string
  completed_at: string | null
  config_snapshot: Record<string, unknown>
  metrics_summary: Record<string, number | null>
  sample_count: number
  successful_sample_count: number
  error: string | null
}

export interface SampleEvaluationResult {
  sample_id: string
  question: string
  answer: string
  reference_answer: string
  retrieved_contexts: string[]
  reference_contexts: string[]
  metric_scores: Record<string, number | null>
  error: string | null
}

export interface GenerateDatasetPayload {
  name: string
  source_document_ids: string[]
  sample_count: number
  generator_model?: string
}

export interface CreateEvaluationRunPayload {
  dataset_id: string
  metrics?: string[]
  config_overrides?: Record<string, unknown>
}

async function parseJsonOrThrow<T>(res: Response, message: string): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${message} (${res.status}): ${text || res.statusText}`)
  }

  return (await res.json()) as T
}

export async function createEvaluationDatasetTask(
  payload: GenerateDatasetPayload,
): Promise<EvaluationTask> {
  const res = await fetch('/api/v1/evaluate/datasets/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  return parseJsonOrThrow<EvaluationTask>(res, '创建评估数据集任务失败')
}

export async function listEvaluationDatasets(): Promise<EvaluationDatasetSummary[]> {
  const res = await fetch('/api/v1/evaluate/datasets')
  return parseJsonOrThrow<EvaluationDatasetSummary[]>(res, '获取评估数据集失败')
}

export async function getEvaluationDataset(datasetId: string): Promise<EvaluationDatasetDetail> {
  const res = await fetch(`/api/v1/evaluate/datasets/${datasetId}`)
  return parseJsonOrThrow<EvaluationDatasetDetail>(res, '获取评估数据集详情失败')
}

export async function createEvaluationRunTask(
  payload: CreateEvaluationRunPayload,
): Promise<EvaluationTask> {
  const res = await fetch('/api/v1/evaluate/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  return parseJsonOrThrow<EvaluationTask>(res, '创建评估任务失败')
}

export async function getEvaluationTask(taskId: string): Promise<EvaluationTask> {
  const res = await fetch(`/api/v1/evaluate/tasks/${taskId}`)
  return parseJsonOrThrow<EvaluationTask>(res, '获取评估任务状态失败')
}

export async function getEvaluationRun(runId: string): Promise<EvaluationRun> {
  const res = await fetch(`/api/v1/evaluate/runs/${runId}`)
  return parseJsonOrThrow<EvaluationRun>(res, '获取评估结果失败')
}

export async function getEvaluationRunSamples(runId: string): Promise<SampleEvaluationResult[]> {
  const res = await fetch(`/api/v1/evaluate/runs/${runId}/samples`)
  return parseJsonOrThrow<SampleEvaluationResult[]>(res, '获取评估样本结果失败')
}
