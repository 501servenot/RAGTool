import { Alert, Button, Card, Modal, Select, Space, Tag, Upload } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import type { UploadFile, UploadProps } from 'antd'

import { getKnowledgeDocuments } from '../../api/knowledge'
import { previewFile, uploadFile } from '../../api/upload'
import type { ParsePreviewResponse, ParserName, UploadResponse } from '../../api/upload'
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
  const [parser, setParser] = useState<ParserName>('pypdf')
  const [previewing, setPreviewing] = useState(false)
  const [preview, setPreview] = useState<ParsePreviewResponse | null>(null)
  const [previewOpen, setPreviewOpen] = useState(false)
  const busy = uploading || previewing
  const isPdf = !file || file.name.toLowerCase().endsWith('.pdf') || file.type === 'application/pdf'
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
    if (previewing) return '文件解析预览中'
    if (knowledgeLoading) return '读取知识库状态中'
    if (uploading) return '文件上传并解析中'
    if (knowledgeReady) return '知识库已可用于聊天'
    return '知识库暂无文档'
  }, [knowledgeLoading, uploading, previewing, knowledgeReady])

  const handlePick: UploadProps['onChange'] = ({ fileList }) => {
    setPreview(null)
    setPreviewOpen(false)
    setUploadError(null)
    setFile((fileList[fileList.length - 1]?.originFileObj as File | undefined) ?? null)
  }

  const handleRemove = () => {
    setPreview(null)
    setPreviewOpen(false)
    setFile(null)
    return true
  }

  const handleUpload = async () => {
    if (!file || busy) return

    setUploading(true)
    setUploadError(null)

    try {
      const resp = await uploadFile(file, parser)
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
      setPreview(null)
      setPreviewOpen(false)
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : String(err))
    } finally {
      setUploading(false)
    }
  }

  const handlePreview = async () => {
    if (!file || busy) return
    if (preview) {
      setPreviewOpen(true)
      return
    }
    setPreviewing(true)
    setUploadError(null)
    try {
      const result = await previewFile(file, parser)
      setPreview(result)
      setPreviewOpen(true)
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : String(err))
    } finally {
      setPreviewing(false)
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
              disabled={busy}
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

            <div className="parser-field">
              <label htmlFor="pdf-parser" className="field-label">PDF 解析器</label>
              <Select<ParserName>
                id="pdf-parser"
                value={parser}
                disabled={busy || !isPdf}
                onChange={(value) => {
                  setParser(value)
                  setPreview(null)
                  setPreviewOpen(false)
                  setUploadError(null)
                }}
                options={[
                  { value: 'pypdf', label: 'pypdf · 快速提取文字' },
                  { value: 'docling', label: 'Docling · 版面与表格解析' },
                ]}
              />
              <span className="page-antd-card-description">
                {!isPdf ? 'TXT、Markdown 直接读取文本。' : parser === 'docling'
                  ? '处理时间较长，首次使用需下载模型；复杂公式请对照原文核查。'
                  : '适合带文字层的 PDF。'}
              </span>
            </div>
            <Space wrap>
              <Button disabled={!file || busy} loading={previewing} onClick={handlePreview}>
                {previewing ? '解析中...' : '预览解析结果'}
              </Button>
              <Button type="primary" disabled={!file || busy} loading={uploading} onClick={handleUpload}>
                {uploading ? '入库中...' : '上传到知识库'}
              </Button>
            </Space>

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
                          {u.size_kb.toFixed(2)} KB · {u.parser} · {u.uploadedAt}
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
      <Modal
        title="解析结果预览"
        open={previewOpen}
        onCancel={() => setPreviewOpen(false)}
        footer={<Button onClick={() => setPreviewOpen(false)}>关闭</Button>}
        width={960}
      >
        {preview && <>
          <p>{preview.filename} · {preview.parser} · {preview.characters.toLocaleString()} 字符</p>
          <p className="page-antd-card-description">
            以下是将用于入库的{preview.format === 'markdown' ? ' Markdown 文本' : '文本'}，预览不会写入知识库。
          </p>
          {preview.text.trim()
            ? <pre className="parse-preview-text">{preview.text}</pre>
            : <Alert type="warning" showIcon message="未提取到文字，可尝试其他解析器或检查原文件。" />}
        </>}
      </Modal>
    </div>
  )
}
