import { Alert, Button, Card, Tag, Upload } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import type { UploadFile, UploadProps } from 'antd'

import { getKnowledgeDocuments } from '../../api/knowledge'
import { uploadFile } from '../../api/upload'
import type { UploadResponse } from '../../api/upload'
import './index.css'

interface UploadRecord extends UploadResponse {
  id: string
  uploadedAt: string
}

const ACCEPT_EXT = '.txt,.md,.pdf'

function formatTime(d: Date) {
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploads, setUploads] = useState<UploadRecord[]>([])
  const [knowledgeReady, setKnowledgeReady] = useState(false)
  const [knowledgeLoading, setKnowledgeLoading] = useState(true)
  const [knowledgeError, setKnowledgeError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const loadKnowledgeState = async () => {
      try {
        const summary = await getKnowledgeDocuments()
        if (cancelled) return
        setKnowledgeReady(summary.document_count > 0)
        setKnowledgeError(null)
      } catch (err) {
        if (cancelled) return
        setKnowledgeReady(false)
        setKnowledgeError(err instanceof Error ? err.message : String(err))
      } finally {
        if (!cancelled) {
          setKnowledgeLoading(false)
        }
      }
    }

    void loadKnowledgeState()

    return () => {
      cancelled = true
    }
  }, [])

  const latestUpload = uploads[0] ?? null
  const statusText = useMemo(() => {
    if (knowledgeLoading) return '读取知识库状态中'
    if (uploading) return '文件上传并解析中'
    if (knowledgeReady) return '知识库已可用于聊天'
    return '知识库暂无文档'
  }, [knowledgeLoading, uploading, knowledgeReady])

  const handlePick: UploadProps['onChange'] = ({ fileList }) => {
    setUploadError(null)
    setFile((fileList[fileList.length - 1]?.originFileObj as File | undefined) ?? null)
  }

  const handleRemove = () => {
    setFile(null)
    return true
  }

  const handleUpload = async () => {
    if (!file || uploading) return

    setUploading(true)
    setUploadError(null)

    try {
      const resp = await uploadFile(file)
      setUploads((prev) => [
        {
          ...resp,
          id: crypto.randomUUID(),
          uploadedAt: formatTime(new Date()),
        },
        ...prev,
      ])
      setKnowledgeReady(true)
      setKnowledgeError(null)
      setFile(null)
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : String(err))
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="page page-antd">
      <header className="page-header">
        <div>
          <h2 className="page-title">文档上传</h2>
          <p className="page-description">上传知识文档并写入知识库，随后即可在对话页继续提问。</p>
        </div>
        <Tag color={knowledgeReady ? 'success' : 'default'}>{statusText}</Tag>
      </header>

      <div className="upload-page-layout">
        <Card className="panel antd-panel-card" styles={{ body: { padding: 0 } }}>
          <div className="page-antd-card-header">
            <div className="page-antd-card-title">上传到知识库</div>
            <div className="page-antd-card-description">
              支持 txt、md、pdf，上传成功后会立即参与后续检索。
            </div>
          </div>
          <div className="panel-content page-antd-card-body">
            <Upload.Dragger
              accept={ACCEPT_EXT}
              beforeUpload={() => false}
              disabled={uploading}
              maxCount={1}
              multiple={false}
              onChange={handlePick}
              onRemove={handleRemove}
              className="page-upload-dragger"
              fileList={
                file
                  ? ([
                      {
                        uid: file.name,
                        name: file.name,
                        size: file.size,
                      },
                    ] satisfies UploadFile[])
                  : []
              }
            >
              <p className="field-label">选择文件</p>
              <p className="page-antd-card-description">
                {file ? `${file.name} (${(file.size / 1024).toFixed(2)} KB)` : '支持 txt / md / pdf'}
              </p>
            </Upload.Dragger>

            <Button type="primary" disabled={!file || uploading} onClick={handleUpload}>
              {uploading ? '上传中...' : '上传并解析'}
            </Button>

            {uploadError && <Alert type="error" showIcon message={uploadError} />}
            {knowledgeError && <Alert type="error" showIcon message={knowledgeError} />}

            <div className="summary-list">
              <div className="summary-item">
                <span>最近文件</span>
                <strong>{latestUpload?.filename ?? '暂无'}</strong>
              </div>
              <div className="summary-item">
                <span>知识库状态</span>
                <strong>{knowledgeReady ? '可聊天' : knowledgeLoading ? '读取中' : '暂无文档'}</strong>
              </div>
            </div>
          </div>
        </Card>

        <Card className="panel antd-panel-card" styles={{ body: { padding: 0 } }}>
          <div className="page-antd-card-header">
            <div className="page-antd-card-title">最近上传记录</div>
            <div className="page-antd-card-description">显示当前页面会话中的最近上传结果。</div>
          </div>
          <div className="panel-content page-antd-card-body">
            <div className="upload-history">
              {uploads.length === 0 ? (
                <div className="empty-box">暂无上传记录</div>
              ) : (
                <ul className="simple-list">
                  {uploads.map((u) => (
                    <li key={u.id} className="simple-list__item">
                      <div>
                        <strong>{u.filename}</strong>
                        <span>
                          {u.size_kb.toFixed(2)} KB · {u.uploadedAt}
                        </span>
                      </div>
                      <Tag color={u.message === '成功' ? 'success' : 'warning'}>{u.message}</Tag>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
