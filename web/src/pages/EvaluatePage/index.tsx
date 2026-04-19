import {
  Alert,
  Button,
  Card,
  Checkbox,
  Descriptions,
  Empty,
  Input,
  InputNumber,
  Progress,
  Select,
  Space,
  Table,
  Tag,
} from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { TableColumnsType } from 'antd'

import {
  createEvaluationDatasetTask,
  createEvaluationRunTask,
  getEvaluationDataset,
  getEvaluationRun,
  getEvaluationRunSamples,
  getEvaluationTask,
  listEvaluationDatasets,
} from '../../api/evaluate'
import type {
  CreateEvaluationRunPayload,
  EvaluationDatasetDetail,
  EvaluationDatasetSummary,
  EvaluationRun,
  EvaluationTask,
  GenerateDatasetPayload,
  SampleEvaluationResult,
} from '../../api/evaluate'
import { getKnowledgeDocuments } from '../../api/knowledge'
import type { KnowledgeDocument } from '../../api/knowledge'
import MetricCards from './components/MetricCards'
import SampleResultsTable from './components/SampleResultsTable'
import './index.css'

const ACTIVE_TASK_STORAGE_KEY = 'rag_evaluate_task_id'
const ACTIVE_RUN_STORAGE_KEY = 'rag_evaluate_run_id'
const ACTIVE_DATASET_STORAGE_KEY = 'rag_evaluate_dataset_id'
const METRIC_OPTIONS = [
  { label: 'Faithfulness', value: 'faithfulness' },
  { label: '回答相关性', value: 'answer_relevancy' },
  { label: '召回准确率', value: 'context_precision' },
  { label: '上下文召回率', value: 'context_recall' },
] as const

type TaskTone = 'default' | 'success' | 'warning' | 'danger'

interface RunConfigDraft {
  metrics: string[]
  retrieve_top_k: number | null
  retrieval_neighbor_chunks: number | null
  rerank_enabled: boolean
  rewrite_enabled: boolean
}

const INITIAL_RUN_CONFIG: RunConfigDraft = {
  metrics: METRIC_OPTIONS.map((item) => item.value),
  retrieve_top_k: null,
  retrieval_neighbor_chunks: null,
  rerank_enabled: true,
  rewrite_enabled: true,
}

function getStoredValue(key: string) {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(key)
}

function setStoredValue(key: string, value: string | null) {
  if (typeof window === 'undefined') return
  if (value == null) {
    window.localStorage.removeItem(key)
    return
  }
  window.localStorage.setItem(key, value)
}

function extractResultId(task: EvaluationTask | null, key: string) {
  if (!task?.result_ref) return null
  const value = task.result_ref[key]
  return typeof value === 'string' ? value : null
}

function getTaskTone(status: EvaluationTask['status']): TaskTone {
  switch (status) {
    case 'completed':
      return 'success'
    case 'failed':
    case 'cancelled':
      return 'danger'
    case 'running':
      return 'default'
    default:
      return 'warning'
  }
}

function getTaskTagColor(tone: TaskTone) {
  switch (tone) {
    case 'success':
      return 'success'
    case 'danger':
      return 'error'
    case 'warning':
      return 'warning'
    default:
      return 'processing'
  }
}

function buildRunPayload(datasetId: string, draft: RunConfigDraft): CreateEvaluationRunPayload {
  const configOverrides: Record<string, unknown> = {
    rerank_enabled: draft.rerank_enabled,
    rewrite_enabled: draft.rewrite_enabled,
  }
  if (draft.retrieve_top_k != null) {
    configOverrides.retrieve_top_k = draft.retrieve_top_k
  }
  if (draft.retrieval_neighbor_chunks != null) {
    configOverrides.retrieval_neighbor_chunks = draft.retrieval_neighbor_chunks
  }

  return {
    dataset_id: datasetId,
    metrics: draft.metrics,
    config_overrides: configOverrides,
  }
}

function formatDateTime(value?: string | null) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

export default function EvaluatePage() {
  const [knowledgeDocuments, setKnowledgeDocuments] = useState<KnowledgeDocument[]>([])
  const [datasets, setDatasets] = useState<EvaluationDatasetSummary[]>([])
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(
    () => getStoredValue(ACTIVE_DATASET_STORAGE_KEY),
  )
  const [selectedDataset, setSelectedDataset] = useState<EvaluationDatasetDetail | null>(null)
  const [activeTask, setActiveTask] = useState<EvaluationTask | null>(null)
  const [taskHistory, setTaskHistory] = useState<EvaluationTask[]>([])
  const [currentRun, setCurrentRun] = useState<EvaluationRun | null>(null)
  const [sampleResults, setSampleResults] = useState<SampleEvaluationResult[]>([])
  const [datasetName, setDatasetName] = useState('知识库评估集')
  const [datasetSourceIds, setDatasetSourceIds] = useState<string[]>([])
  const [datasetSampleCount, setDatasetSampleCount] = useState(5)
  const [datasetGeneratorModel, setDatasetGeneratorModel] = useState('')
  const [runConfig, setRunConfig] = useState<RunConfigDraft>(INITIAL_RUN_CONFIG)
  const [bootLoading, setBootLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [datasetDetailLoading, setDatasetDetailLoading] = useState(false)
  const [runLoading, setRunLoading] = useState(false)
  const [samplesLoading, setSamplesLoading] = useState(false)
  const [submittingDataset, setSubmittingDataset] = useState(false)
  const [submittingRun, setSubmittingRun] = useState(false)
  const [pageError, setPageError] = useState<string | null>(null)

  const upsertTaskHistory = useCallback((task: EvaluationTask) => {
    setTaskHistory((prev) => {
      const next = [task, ...prev.filter((item) => item.task_id !== task.task_id)]
      return next.slice(0, 6)
    })
  }, [])

  const loadKnowledgeState = useCallback(async () => {
    const summary = await getKnowledgeDocuments()
    setKnowledgeDocuments(summary.documents)
    if (summary.documents.length > 0 && datasetSourceIds.length === 0) {
      setDatasetSourceIds(summary.documents.map((item) => item.document_id))
    }
    return summary.documents
  }, [datasetSourceIds.length])

  const loadDatasets = useCallback(async () => {
    const response = await listEvaluationDatasets()
    setDatasets(response)
    return response
  }, [])

  const loadDatasetDetail = useCallback(async (datasetId: string) => {
    setDatasetDetailLoading(true)
    try {
      const detail = await getEvaluationDataset(datasetId)
      setSelectedDataset(detail)
      setPageError(null)
      return detail
    } finally {
      setDatasetDetailLoading(false)
    }
  }, [])

  const loadRunArtifacts = useCallback(async (runId: string) => {
    setRunLoading(true)
    setSamplesLoading(true)
    try {
      const [run, samples] = await Promise.all([
        getEvaluationRun(runId),
        getEvaluationRunSamples(runId),
      ])
      setCurrentRun(run)
      setSampleResults(samples)
      setPageError(null)
      return run
    } finally {
      setRunLoading(false)
      setSamplesLoading(false)
    }
  }, [])

  const refreshTask = useCallback(
    async (taskId: string) => {
      const nextTask = await getEvaluationTask(taskId)
      setActiveTask(nextTask)
      upsertTaskHistory(nextTask)
      return nextTask
    },
    [upsertTaskHistory],
  )

  const handleTaskSettled = useCallback(
    async (task: EvaluationTask) => {
      if (task.status !== 'completed') {
        if (task.error) setPageError(task.error)
        return
      }

      const datasetId = extractResultId(task, 'dataset_id')
      const runId = extractResultId(task, 'run_id')

      if (datasetId) {
        setSelectedDatasetId(datasetId)
        setStoredValue(ACTIVE_DATASET_STORAGE_KEY, datasetId)
        await loadDatasets()
        await loadDatasetDetail(datasetId)
      }

      if (runId) {
        setStoredValue(ACTIVE_RUN_STORAGE_KEY, runId)
        await loadRunArtifacts(runId)
      }
    },
    [loadDatasetDetail, loadDatasets, loadRunArtifacts],
  )

  const bootstrap = useCallback(async () => {
    setBootLoading(true)
    try {
      const [documents, datasetList] = await Promise.all([loadKnowledgeState(), loadDatasets()])
      const storedTaskId = getStoredValue(ACTIVE_TASK_STORAGE_KEY)
      const storedRunId = getStoredValue(ACTIVE_RUN_STORAGE_KEY)
      const initialDatasetId =
        getStoredValue(ACTIVE_DATASET_STORAGE_KEY) ?? datasetList[0]?.dataset_id ?? null

      if (documents.length > 0 && datasetSourceIds.length === 0) {
        setDatasetSourceIds(documents.map((item) => item.document_id))
      }

      if (storedTaskId) {
        const task = await getEvaluationTask(storedTaskId).catch(() => null)
        if (task) {
          setActiveTask(task)
          upsertTaskHistory(task)
        }
      }

      if (storedRunId) {
        await loadRunArtifacts(storedRunId).catch(() => undefined)
      }

      if (initialDatasetId) {
        setSelectedDatasetId(initialDatasetId)
        await loadDatasetDetail(initialDatasetId).catch(() => undefined)
      } else {
        setSelectedDataset(null)
      }

      setPageError(null)
    } catch (error) {
      setPageError(error instanceof Error ? error.message : String(error))
    } finally {
      setBootLoading(false)
    }
  }, [
    datasetSourceIds.length,
    loadDatasetDetail,
    loadDatasets,
    loadKnowledgeState,
    loadRunArtifacts,
    upsertTaskHistory,
  ])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void bootstrap()
    }, 0)

    return () => {
      window.clearTimeout(timer)
    }
  }, [bootstrap])

  useEffect(() => {
    if (!selectedDatasetId) {
      setStoredValue(ACTIVE_DATASET_STORAGE_KEY, null)
      return
    }
    setStoredValue(ACTIVE_DATASET_STORAGE_KEY, selectedDatasetId)
  }, [selectedDatasetId])

  useEffect(() => {
    setStoredValue(ACTIVE_TASK_STORAGE_KEY, activeTask?.task_id ?? null)
  }, [activeTask?.task_id])

  useEffect(() => {
    if (!activeTask || ['completed', 'failed', 'cancelled'].includes(activeTask.status)) {
      return
    }

    const timer = window.setInterval(() => {
      void refreshTask(activeTask.task_id)
        .then((nextTask) => {
          if (['completed', 'failed', 'cancelled'].includes(nextTask.status)) {
            return handleTaskSettled(nextTask)
          }
          return undefined
        })
        .catch((error) => {
          setPageError(error instanceof Error ? error.message : String(error))
        })
    }, 2000)

    return () => {
      window.clearInterval(timer)
    }
  }, [activeTask, handleTaskSettled, refreshTask])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await bootstrap()
    } finally {
      setRefreshing(false)
    }
  }

  const handleCreateDataset = async () => {
    const payload: GenerateDatasetPayload = {
      name: datasetName.trim() || '知识库评估集',
      source_document_ids: datasetSourceIds,
      sample_count: datasetSampleCount,
    }
    if (datasetGeneratorModel.trim()) {
      payload.generator_model = datasetGeneratorModel.trim()
    }

    setSubmittingDataset(true)
    setPageError(null)
    try {
      const task = await createEvaluationDatasetTask(payload)
      setActiveTask(task)
      upsertTaskHistory(task)
    } catch (error) {
      setPageError(error instanceof Error ? error.message : String(error))
    } finally {
      setSubmittingDataset(false)
    }
  }

  const handleCreateRun = async () => {
    if (!selectedDatasetId) {
      setPageError('请先选择一个数据集')
      return
    }

    setSubmittingRun(true)
    setPageError(null)
    try {
      const task = await createEvaluationRunTask(buildRunPayload(selectedDatasetId, runConfig))
      setActiveTask(task)
      upsertTaskHistory(task)
    } catch (error) {
      setPageError(error instanceof Error ? error.message : String(error))
    } finally {
      setSubmittingRun(false)
    }
  }

  const taskTone = activeTask ? getTaskTone(activeTask.status) : 'warning'
  const selectedDatasetSamplePreview = selectedDataset?.samples.slice(0, 4) ?? []
  const datasetColumns = useMemo<TableColumnsType<EvaluationDatasetSummary>>(
    () => [
      {
        title: '数据集',
        dataIndex: 'name',
        key: 'name',
        render: (_, record) => (
          <div className="table-file">
            <strong>{record.name}</strong>
            <span>{record.dataset_id}</span>
          </div>
        ),
      },
      {
        title: '样本数',
        dataIndex: 'sample_count',
        key: 'sample_count',
        width: 100,
        render: (value: number) => <Tag>{value}</Tag>,
      },
      {
        title: '版本',
        dataIndex: 'version',
        key: 'version',
        width: 88,
      },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        width: 110,
        render: (value: string) => (
          <Tag color={value === 'completed' ? 'success' : value === 'failed' ? 'error' : 'processing'}>
            {value}
          </Tag>
        ),
      },
      {
        title: '操作',
        key: 'action',
        width: 110,
        render: (_, record) => (
          <Button
            type={record.dataset_id === selectedDatasetId ? 'primary' : 'default'}
            onClick={() => {
              setSelectedDatasetId(record.dataset_id)
              void loadDatasetDetail(record.dataset_id)
            }}
          >
            查看
          </Button>
        ),
      },
    ],
    [loadDatasetDetail, selectedDatasetId],
  )

  const runStatusTag = currentRun ? (
    <Tag color={getTaskTagColor(getTaskTone(currentRun.status))}>{currentRun.status}</Tag>
  ) : null

  return (
    <div className="page page-antd">
      <header className="page-header">
        <div>
          <h2 className="page-title">评估中心</h2>
        </div>
        <Space wrap>
          {activeTask ? (
            <Tag color={getTaskTagColor(taskTone)}>
              {activeTask.status === 'running' ? '评估任务执行中' : `任务状态：${activeTask.status}`}
            </Tag>
          ) : (
            <Tag>空闲</Tag>
          )}
          <Button onClick={() => void handleRefresh()} disabled={refreshing || bootLoading}>
            {refreshing ? '刷新中...' : '刷新'}
          </Button>
        </Space>
      </header>

      {pageError && <Alert type="error" showIcon message={pageError} />}

      <div className="evaluate-action-grid">
        <Card className="panel antd-panel-card" styles={{ body: { padding: 0 } }}>
          <div className="page-antd-card-header">
            <div className="page-antd-card-title">生成评估数据集</div>
            <div className="page-antd-card-description">
              选择知识库文档，构建可复用的问答评估样本。
            </div>
          </div>
          <div className="panel-content page-antd-card-body">
            <label className="field-label" htmlFor="dataset-name">
              数据集名称
            </label>
            <Input
              id="dataset-name"
              value={datasetName}
              onChange={(event) => setDatasetName(event.target.value)}
              placeholder="例如：知识库首轮评估"
            />

            <label className="field-label">来源文档</label>
            <Select
              mode="multiple"
              value={datasetSourceIds}
              onChange={setDatasetSourceIds}
              options={knowledgeDocuments.map((doc) => ({
                label: `${doc.filename} (${doc.chunk_count} 切片)`,
                value: doc.document_id,
              }))}
              placeholder="选择要生成评估数据集的文档"
            />

            <div className="evaluate-inline-fields">
              <div>
                <label className="field-label">样本数量</label>
                <InputNumber
                  min={1}
                  max={50}
                  value={datasetSampleCount}
                  onChange={(value) => setDatasetSampleCount(value ?? 5)}
                  className="evaluate-number-input"
                />
              </div>
              <div>
                <label className="field-label">生成模型（可选）</label>
                <Input
                  value={datasetGeneratorModel}
                  onChange={(event) => setDatasetGeneratorModel(event.target.value)}
                  placeholder="默认复用后端配置"
                />
              </div>
            </div>

            <Button
              type="primary"
              onClick={() => void handleCreateDataset()}
              disabled={submittingDataset || datasetSourceIds.length === 0 || bootLoading}
            >
              {submittingDataset ? '创建中...' : '创建数据集任务'}
            </Button>
          </div>
        </Card>

        <Card className="panel antd-panel-card" styles={{ body: { padding: 0 } }}>
          <div className="page-antd-card-header">
            <div className="page-antd-card-title">发起评估运行</div>
            <div className="page-antd-card-description">
              选择已有数据集，执行 ragas 评估并查看关键参数表现。
            </div>
          </div>
          <div className="panel-content page-antd-card-body">
            <label className="field-label">评估数据集</label>
            <Select
              value={selectedDatasetId ?? undefined}
              onChange={(value) => {
                setSelectedDatasetId(value)
                void loadDatasetDetail(value)
              }}
              options={datasets.map((dataset) => ({
                label: `${dataset.name} (${dataset.sample_count} 样本)`,
                value: dataset.dataset_id,
              }))}
              placeholder="选择一个数据集"
            />

            <label className="field-label">评估指标</label>
            <Select
              mode="multiple"
              value={runConfig.metrics}
              onChange={(metrics) => setRunConfig((prev) => ({ ...prev, metrics }))}
              options={[...METRIC_OPTIONS]}
            />

            <div className="evaluate-inline-fields evaluate-inline-fields--compact">
              <div>
                <label className="field-label">Top K</label>
                <InputNumber
                  min={1}
                  value={runConfig.retrieve_top_k}
                  onChange={(value) =>
                    setRunConfig((prev) => ({ ...prev, retrieve_top_k: value }))
                  }
                  placeholder="默认"
                  className="evaluate-number-input"
                />
              </div>
              <div>
                <label className="field-label">邻接 Chunk</label>
                <InputNumber
                  min={0}
                  value={runConfig.retrieval_neighbor_chunks}
                  onChange={(value) =>
                    setRunConfig((prev) => ({
                      ...prev,
                      retrieval_neighbor_chunks: value,
                    }))
                  }
                  placeholder="默认"
                  className="evaluate-number-input"
                />
              </div>
            </div>

            <div className="evaluate-check-grid">
              <Checkbox
                checked={runConfig.rerank_enabled}
                onChange={(event) =>
                  setRunConfig((prev) => ({
                    ...prev,
                    rerank_enabled: event.target.checked,
                  }))
                }
              >
                启用 Rerank
              </Checkbox>
              <Checkbox
                checked={runConfig.rewrite_enabled}
                onChange={(event) =>
                  setRunConfig((prev) => ({
                    ...prev,
                    rewrite_enabled: event.target.checked,
                  }))
                }
              >
                启用 Query Rewrite
              </Checkbox>
            </div>

            <Button
              type="primary"
              onClick={() => void handleCreateRun()}
              disabled={submittingRun || !selectedDatasetId || bootLoading}
            >
              {submittingRun ? '提交中...' : '创建评估任务'}
            </Button>
          </div>
        </Card>
      </div>

      <Card className="panel antd-panel-card" styles={{ body: { padding: 0 } }}>
        <div className="page-antd-card-header">
          <div className="page-antd-card-title">任务状态</div>
          <div className="page-antd-card-description">轮询展示当前任务进度，并保留最近触发的任务记录。</div>
        </div>
        <div className="panel-content page-antd-card-body">
          {activeTask ? (
            <div className="evaluate-task-panel">
              <div className="evaluate-task-main">
                <div>
                  <div className="evaluate-task-title-row">
                    <strong>{activeTask.message}</strong>
                    <Tag color={getTaskTagColor(taskTone)}>{activeTask.status}</Tag>
                  </div>
                  <div className="page-antd-card-description">
                    任务类型：{activeTask.task_type} · 资源：{activeTask.resource_id ?? '-'}
                  </div>
                </div>
                <Progress percent={Math.round(activeTask.progress * 100)} status={activeTask.status === 'failed' ? 'exception' : undefined} />
              </div>

              {taskHistory.length > 0 && (
                <ul className="simple-list">
                  {taskHistory.map((task) => (
                    <li key={task.task_id} className="simple-list__item">
                      <div>
                        <strong>{task.message}</strong>
                        <span>
                          {task.task_type} · {formatDateTime(task.updated_at)}
                        </span>
                      </div>
                      <Tag color={getTaskTagColor(getTaskTone(task.status))}>{task.status}</Tag>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <div className="empty-box">
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无评估任务" />
            </div>
          )}
        </div>
      </Card>

      <MetricCards metrics={currentRun?.metrics_summary ?? {}} />

      <div className="evaluate-content-grid">
        <Card className="panel antd-panel-card" styles={{ body: { padding: 0 } }}>
          <div className="page-antd-card-header">
            <div className="page-antd-card-title">评估数据集</div>
            <div className="page-antd-card-description">查看已生成的数据集并浏览样本预览。</div>
          </div>
          <div className="panel-content page-antd-card-body">
            {bootLoading ? (
              <div className="empty-box">加载中...</div>
            ) : datasets.length === 0 ? (
              <div className="empty-box">
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有评估数据集" />
              </div>
            ) : (
              <Table
                className="page-knowledge-table evaluate-table-flat"
                columns={datasetColumns}
                dataSource={datasets}
                pagination={false}
                rowKey="dataset_id"
                scroll={{ x: 720 }}
              />
            )}

            <div className="evaluate-preview-card">
              <div className="page-antd-card-title">当前数据集预览</div>
              <div className="page-antd-card-description">
                {selectedDataset ? `${selectedDataset.name} · ${selectedDataset.sample_count} 个样本` : '请选择一个数据集'}
              </div>

              {selectedDataset && selectedDatasetSamplePreview.length > 0 ? (
                <ul className="simple-list">
                  {selectedDatasetSamplePreview.map((sample) => (
                    <li key={sample.sample_id} className="simple-list__item">
                      <div>
                        <strong>{sample.question}</strong>
                        <span>{sample.source_document_id}</span>
                      </div>
                      <Tag>{sample.source_chunk_ids.length} chunks</Tag>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="empty-box evaluate-preview-empty">
                  {datasetDetailLoading ? '加载数据集详情中...' : '暂无样本可预览'}
                </div>
              )}
            </div>
          </div>
        </Card>

        <Card className="panel antd-panel-card" styles={{ body: { padding: 0 } }}>
          <div className="page-antd-card-header">
            <div className="page-antd-card-title">评估结果明细</div>
            <div className="page-antd-card-description">展示运行摘要、关键配置，以及逐样本得分明细。</div>
          </div>
          <div className="panel-content page-antd-card-body">
            {currentRun ? (
              <>
                <Descriptions
                  className="evaluate-run-descriptions"
                  column={2}
                  items={[
                    { key: 'run_id', label: 'Run ID', children: currentRun.run_id },
                    { key: 'status', label: '状态', children: runStatusTag },
                    { key: 'dataset_id', label: '数据集', children: currentRun.dataset_id },
                    {
                      key: 'sample_count',
                      label: '样本',
                      children: `${currentRun.successful_sample_count}/${currentRun.sample_count}`,
                    },
                    {
                      key: 'updated_at',
                      label: '更新时间',
                      children: formatDateTime(currentRun.updated_at),
                    },
                    {
                      key: 'completed_at',
                      label: '完成时间',
                      children: formatDateTime(currentRun.completed_at),
                    },
                  ]}
                />

                <div className="evaluate-config-tags">
                  {Object.entries(currentRun.config_snapshot).length === 0 ? (
                    <Tag>默认配置</Tag>
                  ) : (
                    Object.entries(currentRun.config_snapshot).map(([key, value]) => (
                      <Tag key={key}>{`${key}: ${String(value)}`}</Tag>
                    ))
                  )}
                </div>

                <SampleResultsTable results={sampleResults} loading={runLoading || samplesLoading} />
              </>
            ) : (
              <div className="empty-box">
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="完成评估后会在这里展示指标和样本结果" />
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}
