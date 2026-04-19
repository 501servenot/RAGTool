import { Card, Statistic } from 'antd'

type MetricSummary = Record<string, number | null>

const METRIC_ITEMS = [
  { key: 'faithfulness', label: 'Faithfulness', suffix: '' },
  { key: 'answer_relevancy', label: '回答相关性', suffix: '' },
  { key: 'context_precision', label: '召回准确率', suffix: '' },
  { key: 'context_recall', label: '上下文召回率', suffix: '' },
  { key: 'success_rate', label: '成功率', suffix: '%' },
] as const

function formatMetricValue(metricKey: string, value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return '-'
  }

  if (metricKey === 'success_rate') {
    return (value * 100).toFixed(1)
  }

  return value.toFixed(3)
}

interface MetricCardsProps {
  metrics: MetricSummary
}

export default function MetricCards({ metrics }: MetricCardsProps) {
  return (
    <div className="evaluate-metric-grid">
      {METRIC_ITEMS.map((item) => (
        <Card key={item.key} className="panel antd-panel-card">
          <Statistic
            title={item.label}
            value={formatMetricValue(item.key, metrics[item.key])}
            suffix={item.suffix || undefined}
            className="page-statistic"
          />
        </Card>
      ))}
    </div>
  )
}
