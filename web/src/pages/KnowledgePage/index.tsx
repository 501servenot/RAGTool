import { useCallback, useEffect, useState } from 'react'

import {
  deleteKnowledgeDocument,
  getKnowledgeDocuments,
} from '../../api/knowledge'
import type { KnowledgeBaseSummaryResponse } from '../../api/knowledge'
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../../components/ui/alert-dialog'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'

const INITIAL_DATA: KnowledgeBaseSummaryResponse = {
  document_count: 0,
  chunk_count: 0,
  documents: [],
}

interface PendingDeleteDocument {
  documentId: string
  filename: string
}

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

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h2 className="page-title">知识库</h2>
          <p className="page-description">查看当前知识库中的文档，并支持删除。</p>
        </div>
        <Button variant="secondary" onClick={() => void loadData()} disabled={loading}>
          刷新
        </Button>
      </header>

      <div className="knowledge-summary">
        <Card className="panel">
          <CardHeader>
            <CardTitle>文档数量</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="stat-value">{data.document_count}</div>
          </CardContent>
        </Card>
        <Card className="panel">
          <CardHeader>
            <CardTitle>切片数量</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="stat-value">{data.chunk_count}</div>
          </CardContent>
        </Card>
      </div>

      <Card className="panel">
        <CardHeader>
          <CardTitle>文档列表</CardTitle>
          <CardDescription>按文件维度展示当前知识库内容。</CardDescription>
        </CardHeader>
        <CardContent className="panel-content">
          {error && <div className="ui-alert ui-alert--error">{error}</div>}

          {loading ? (
            <div className="empty-box">加载中...</div>
          ) : data.documents.length === 0 ? (
            <div className="empty-box">当前知识库没有文档</div>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>文件名</th>
                    <th>切片数</th>
                    <th>创建时间</th>
                    <th>操作人</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {data.documents.map((doc) => (
                    <tr key={doc.document_id}>
                      <td>
                        <div className="table-file">
                          <strong>{doc.filename}</strong>
                          <span>{doc.document_id}</span>
                        </div>
                      </td>
                      <td>
                        <Badge variant="outline">{doc.chunk_count}</Badge>
                      </td>
                      <td>{doc.create_time || '-'}</td>
                      <td>{doc.operator || '-'}</td>
                      <td>
                        <Button
                          variant="secondary"
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
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <AlertDialog
        open={pendingDelete !== null}
        onOpenChange={(open) => {
          if (!open && !deletingId) {
            setPendingDelete(null)
          }
        }}
      >
        <AlertDialogContent
          onPointerDownOutside={() => {
            if (!deletingId) {
              setPendingDelete(null)
            }
          }}
        >
          <AlertDialogHeader>
            <AlertDialogTitle>删除知识库文档</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingDelete
                ? `确认删除“${pendingDelete.filename}”吗？删除后对应切片会从知识库中移除。`
                : '确认删除该文档吗？'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setPendingDelete(null)}
              disabled={Boolean(deletingId)}
            >
              取消
            </Button>
            <Button
              type="button"
              className="session-delete-confirm"
              onClick={() => pendingDelete && void handleDelete(pendingDelete.documentId)}
              disabled={Boolean(deletingId)}
            >
              {deletingId ? '删除中...' : '确认删除'}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
