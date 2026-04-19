import { Button, Drawer, Empty, Table, Tag } from 'antd'
import { useMemo, useState } from 'react'
import type { TableColumnsType } from 'antd'

import type { SampleEvaluationResult } from '../../../api/evaluate'

interface SampleResultsTableProps {
  results: SampleEvaluationResult[]
  loading: boolean
}

function formatMetric(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return '-'
  }
  return value.toFixed(3)
}

function buildPreview(text: string, maxLength: number = 56) {
  if (!text) return '-'
  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength)}...`
}

export default function SampleResultsTable({ results, loading }: SampleResultsTableProps) {
  const [activeSample, setActiveSample] = useState<SampleEvaluationResult | null>(null)

  const columns = useMemo<TableColumnsType<SampleEvaluationResult>>(
    () => [
      {
        title: '问题',
        dataIndex: 'question',
        key: 'question',
        render: (value: string) => <span>{buildPreview(value, 40)}</span>,
      },
      {
        title: 'Faithfulness',
        key: 'faithfulness',
        width: 130,
        render: (_, record) => formatMetric(record.metric_scores.faithfulness),
      },
      {
        title: '回答相关性',
        key: 'answer_relevancy',
        width: 130,
        render: (_, record) => formatMetric(record.metric_scores.answer_relevancy),
      },
      {
        title: '召回准确率',
        key: 'context_precision',
        width: 130,
        render: (_, record) => formatMetric(record.metric_scores.context_precision),
      },
      {
        title: '上下文召回率',
        key: 'context_recall',
        width: 130,
        render: (_, record) => formatMetric(record.metric_scores.context_recall),
      },
      {
        title: '状态',
        key: 'status',
        width: 120,
        render: (_, record) =>
          record.error ? <Tag color="error">失败</Tag> : <Tag color="success">成功</Tag>,
      },
      {
        title: '操作',
        key: 'action',
        width: 120,
        render: (_, record) => <Button onClick={() => setActiveSample(record)}>详情</Button>,
      },
    ],
    [],
  )

  return (
    <>
      {results.length === 0 && !loading ? (
        <div className="empty-box">
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无样本评估结果" />
        </div>
      ) : (
        <Table
          className="page-knowledge-table evaluate-table-flat"
          columns={columns}
          dataSource={results}
          loading={loading}
          pagination={{ pageSize: 6, hideOnSinglePage: true }}
          rowKey="sample_id"
          scroll={{ x: 960 }}
        />
      )}

      <Drawer
        open={activeSample !== null}
        title="样本评估详情"
        width={720}
        onClose={() => setActiveSample(null)}
        destroyOnHidden
      >
        {activeSample && (
          <div className="evaluate-detail-stack">
            <section className="evaluate-detail-section">
              <h4>问题</h4>
              <p>{activeSample.question}</p>
            </section>
            <section className="evaluate-detail-section">
              <h4>模型回答</h4>
              <p>{activeSample.answer}</p>
            </section>
            <section className="evaluate-detail-section">
              <h4>参考答案</h4>
              <p>{activeSample.reference_answer}</p>
            </section>
            <section className="evaluate-detail-section">
              <h4>检索上下文</h4>
              <ul className="evaluate-context-list">
                {activeSample.retrieved_contexts.map((context, index) => (
                  <li key={`${index}-${context.slice(0, 12)}`}>{context}</li>
                ))}
              </ul>
            </section>
            <section className="evaluate-detail-section">
              <h4>参考上下文</h4>
              <ul className="evaluate-context-list">
                {activeSample.reference_contexts.map((context, index) => (
                  <li key={`${index}-${context.slice(0, 12)}`}>{context}</li>
                ))}
              </ul>
            </section>
            {activeSample.error && (
              <section className="evaluate-detail-section">
                <h4>错误信息</h4>
                <p>{activeSample.error}</p>
              </section>
            )}
          </div>
        )}
      </Drawer>
    </>
  )
}
