import { Alert, Button, Card, Modal, Statistic, Table, Tag } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import type { TableColumnsType } from 'antd'

import {
  deleteKnowledgeDocument,
  getKnowledgeDocuments,
} from '../../api/knowledge'
import type { KnowledgeBaseSummaryResponse } from '../../api/knowledge'
import './index.css'

const INITIAL_DATA: KnowledgeBaseSummaryResponse = {
  document_count: 0,
  chunk_count: 0,
  documents: [],
}

interface PendingDeleteDocument {
  documentId: string
  filename: string
}
type KnowledgeDocument = KnowledgeBaseSummaryResponse['documents'][number]

export default function KnowledgePage() {
  const [data, setData] = useState<KnowledgeBaseSummaryResponse>(INITIAL_DATA)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = useState<PendingDeleteDocument | null>(null)

  const fetchData = useCallback(async () => {
    try {
      const res = await getKnowledgeDocuments()
      setData(res)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])

  const loadData = useCallback(async () => {
    setLoading(true)
    await fetchData()
  }, [fetchData])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchData()
    }, 0)

    return () => {
      window.clearTimeout(timer)
    }
  }, [fetchData])

  const handleDelete = async (documentId: string) => {
    setDeletingId(documentId)
    setError(null)
    try {
      await deleteKnowledgeDocument(documentId)
      await loadData()
      setPendingDelete(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setDeletingId(null)
    }
  }

  const columns: TableColumnsType<KnowledgeDocument> = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      render: (_, doc) => (
        <div className="table-file">
          <strong>{doc.filename}</strong>
          <span>{doc.document_id}</span>
        </div>
      ),
    },
    {
      title: '切片数',
      dataIndex: 'chunk_count',
      key: 'chunk_count',
      width: 120,
      render: (value: number) => <Tag>{value}</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'create_time',
      key: 'create_time',
      render: (value?: string) => value || '-',
    },
    {
      title: '操作人',
      dataIndex: 'operator',
      key: 'operator',
      render: (value?: string) => value || '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, doc) => (
        <Button
          disabled={deletingId === doc.document_id}
          onClick={() =>
            setPendingDelete({
              documentId: doc.document_id,
              filename: doc.filename,
            })
          }
        >
          {deletingId === doc.document_id ? '删除中...' : '删除'}
        </Button>
      ),
    },
  ]

  return (
    <div className="page page-antd">
      <header className="page-header">
        <div>
          <h2 className="page-title">知识库</h2>
          <p className="page-description">查看当前知识库中的文档，并支持删除。</p>
        </div>
        <Button onClick={() => void loadData()} disabled={loading}>
          刷新
        </Button>
      </header>

      <div className="knowledge-summary">
        <Card className="panel antd-panel-card">
          <Statistic title="文档数量" value={data.document_count} className="page-statistic" />
        </Card>
        <Card className="panel antd-panel-card">
          <Statistic title="切片数量" value={data.chunk_count} className="page-statistic" />
        </Card>
      </div>

      <Card className="panel antd-panel-card" styles={{ body: { padding: 0 } }}>
        <div className="page-antd-card-header">
          <div className="page-antd-card-title">文档列表</div>
          <div className="page-antd-card-description">按文件维度展示当前知识库内容。</div>
        </div>
        <div className="panel-content page-antd-card-body">
          {error && <Alert type="error" showIcon message={error} />}

          {loading ? (
            <div className="empty-box">加载中...</div>
          ) : data.documents.length === 0 ? (
            <div className="empty-box">当前知识库没有文档</div>
          ) : (
            <Table
              className="page-knowledge-table"
              columns={columns}
              dataSource={data.documents}
              pagination={false}
              rowKey="document_id"
              scroll={{ x: 'max-content' }}
            />
          )}
        </div>
      </Card>

      <Modal
        open={pendingDelete !== null}
        title="删除知识库文档"
        okText={deletingId ? '删除中...' : '确认删除'}
        cancelText="取消"
        onCancel={() => {
          if (!deletingId) {
            setPendingDelete(null)
          }
        }}
        onOk={() => pendingDelete && void handleDelete(pendingDelete.documentId)}
        confirmLoading={Boolean(deletingId)}
        okButtonProps={{ danger: true, className: 'session-delete-confirm' }}
        cancelButtonProps={{ disabled: Boolean(deletingId) }}
        maskClosable={!deletingId}
        destroyOnHidden
      >
        <p className="page-antd-modal-text">
          {pendingDelete
            ? `确认删除“${pendingDelete.filename}”吗？删除后对应切片会从知识库中移除。`
            : '确认删除该文档吗？'}
        </p>
      </Modal>
    </div>
  )
}
