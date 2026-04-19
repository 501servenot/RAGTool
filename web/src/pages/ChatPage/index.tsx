import { Alert, Button, Card, Input, Modal, Tag } from 'antd'
import { Trash2 } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'

import { deleteChatSession, getChatSessionMessages, getChatSessions } from '../../api/chat-history'
import { streamChat } from '../../api/chat'
import { getKnowledgeDocuments } from '../../api/knowledge'
import type { ChatHistoryMessage, ChatSessionSummary } from '../../api/chat-history'
import './index.css'

type ChatRole = 'user' | 'ai'
type StatusTone = 'default' | 'success' | 'warning' | 'danger' | 'outline'
const { TextArea } = Input

interface ChatMessage {
  id: string
  role: ChatRole
  content: string
}

const ACTIVE_CHAT_SESSION_STORAGE_KEY = 'rag_chat_session_id'

function formatTime(d: Date) {
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function getStoredSessionId() {
  if (typeof window === 'undefined') {
    return null
  }

  return window.localStorage.getItem(ACTIVE_CHAT_SESSION_STORAGE_KEY)
}

function createSessionId() {
  return crypto.randomUUID()
}

function mapHistoryMessageToChatMessage(message: ChatHistoryMessage): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role: message.role,
    content: message.content,
  }
}

function formatSessionUpdatedAt(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return formatTime(date)
}

function getSystemState(
  canChat: boolean,
  knowledgeLoading: boolean,
  chatting: boolean,
): {
  label: string
  tone: StatusTone
  description: string
} {
  if (knowledgeLoading) {
    return {
      label: '检查中',
      tone: 'outline',
      description: '正在读取当前知识库状态。',
    }
  }

  if (chatting) {
    return {
      label: '回答中',
      tone: 'default',
      description: '系统正在检索知识库并生成回答。',
    }
  }

  if (canChat) {
    return {
      label: '可提问',
      tone: 'success',
      description: '知识库已准备完成。',
    }
  }

  return {
    label: '不可提问',
    tone: 'outline',
    description: '当前知识库为空，请先上传至少一份文档。',
  }
}

function getStatusTagColor(tone: StatusTone) {
  switch (tone) {
    case 'success':
      return 'success'
    case 'warning':
      return 'warning'
    case 'danger':
      return 'error'
    case 'default':
      return 'processing'
    default:
      return 'default'
  }
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [chatting, setChatting] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)
  const [knowledgeReady, setKnowledgeReady] = useState(false)
  const [knowledgeLoading, setKnowledgeLoading] = useState(true)
  const [knowledgeError, setKnowledgeError] = useState<string | null>(null)
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([])
  const [sessionsLoading, setSessionsLoading] = useState(true)
  const [sessionsError, setSessionsError] = useState<string | null>(null)
  const [messagesLoading, setMessagesLoading] = useState(false)
  const [messagesError, setMessagesError] = useState<string | null>(null)
  const [activeSessionId, setActiveSessionId] = useState<string | null>(() => getStoredSessionId())
  const [sessionPendingDelete, setSessionPendingDelete] = useState<ChatSessionSummary | null>(null)
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null)

  const messagesRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  const canChat = knowledgeReady
  const systemState = useMemo(
    () => getSystemState(canChat, knowledgeLoading, chatting),
    [canChat, knowledgeLoading, chatting],
  )

  useEffect(() => {
    messagesRef.current?.scrollTo({
      top: messagesRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [messages])

  useEffect(() => {
    if (!activeSessionId || typeof window === 'undefined') return
    window.localStorage.setItem(ACTIVE_CHAT_SESSION_STORAGE_KEY, activeSessionId)
  }, [activeSessionId])

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

  const loadSessions = async () => {
    try {
      const sessionList = await getChatSessions()
      setSessions(sessionList)
      setSessionsError(null)
      setActiveSessionId((current) => {
        if (current && sessionList.some((session) => session.session_id === current)) {
          return current
        }
        return sessionList[0]?.session_id ?? createSessionId()
      })
    } catch (err) {
      setSessionsError(err instanceof Error ? err.message : String(err))
      setActiveSessionId((current) => current ?? createSessionId())
    } finally {
      setSessionsLoading(false)
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadSessions()
    }, 0)

    return () => {
      window.clearTimeout(timer)
    }
  }, [])

  useEffect(() => {
    if (!activeSessionId) return

    let cancelled = false

    const loadMessages = async () => {
      setMessagesLoading(true)
      try {
        const historyMessages = await getChatSessionMessages(activeSessionId)
        if (cancelled) return
        setMessages(historyMessages.map(mapHistoryMessageToChatMessage))
        setMessagesError(null)
      } catch (err) {
        if (cancelled) return
        setMessages([])
        setMessagesError(err instanceof Error ? err.message : String(err))
      } finally {
        if (!cancelled) {
          setMessagesLoading(false)
        }
      }
    }

    void loadMessages()

    return () => {
      cancelled = true
    }
  }, [activeSessionId])

  const sendPrompt = async () => {
    const prompt = input.trim()
    if (!prompt || chatting || !canChat || !activeSessionId) return

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: prompt,
    }
    const aiMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'ai',
      content: '',
    }

    setMessages((prev) => [...prev, userMsg, aiMsg])
    setInput('')
    setChatting(true)
    setChatError(null)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      await streamChat(
        prompt,
        activeSessionId,
        (token) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === aiMsg.id ? { ...m, content: m.content + token } : m,
            ),
          )
        },
        controller.signal,
      )
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') return
      const message = err instanceof Error ? err.message : String(err)
      setChatError(message)
      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiMsg.id && m.content === ''
            ? { ...m, content: `（出错：${message}）` }
            : m,
        ),
      )
    } finally {
      setChatting(false)
      abortRef.current = null
      await loadSessions()
    }
  }

  const handleSend = (e: FormEvent) => {
    e.preventDefault()
    void sendPrompt()
  }

  const handleStop = () => {
    abortRef.current?.abort()
  }

  const handleComposerKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void sendPrompt()
    }
  }

  const handleCreateSession = () => {
    if (chatting) return
    const sessionId = createSessionId()
    setActiveSessionId(sessionId)
    setMessages([])
    setChatError(null)
    setMessagesError(null)
  }

  const handleDeleteSession = async () => {
    if (!sessionPendingDelete || deletingSessionId) return

    const deletingId = sessionPendingDelete.session_id
    setDeletingSessionId(deletingId)
    setSessionsError(null)

    try {
      await deleteChatSession(deletingId)

      const remainingSessions = sessions.filter((session) => session.session_id !== deletingId)
      setSessions(remainingSessions)

      if (activeSessionId === deletingId) {
        const nextSessionId = remainingSessions[0]?.session_id ?? createSessionId()
        setActiveSessionId(nextSessionId)
        if (remainingSessions.length === 0) {
          setMessages([])
          setChatError(null)
          setMessagesError(null)
        }
      }

      setSessionPendingDelete(null)
    } catch (err) {
      setSessionsError(err instanceof Error ? err.message : String(err))
    } finally {
      setDeletingSessionId(null)
    }
  }

  return (
    <div className="page page-chat page-antd">
      <header className="page-header">
        <div>
          <h2 className="page-title">PlayGround</h2>
        </div>
        <Tag color={getStatusTagColor(systemState.tone)}>{systemState.label}</Tag>
      </header>

      <div className="chat-layout">
        <Card
          className="panel chat-panel-main antd-panel-card chat-panel-main--antd"
          styles={{ body: { padding: 0, display: 'flex', flexDirection: 'column', minHeight: 0, height: '100%' } }}
        >
          <div className="page-antd-card-header">
            <div className="page-antd-card-title">对话窗口</div>
            <div className="page-antd-card-description">
              {canChat
                ? '知识库中已有文档，可以直接提问。'
                : knowledgeLoading
                  ? '正在读取知识库状态。'
                  : '当前知识库为空，请先前往文档上传页面。'}
            </div>
          </div>
          <div className="panel-content panel-content--chat page-antd-card-body chat-panel-main__body">
            <div className="message-list" ref={messagesRef}>
              {messagesLoading ? (
                <div className="empty-box">正在加载会话消息...</div>
              ) : messages.length === 0 ? (
                <div className="empty-box">暂无消息记录</div>
              ) : (
                <div className="message-stack">
                  {messages.map((m) => (
                    <div key={m.id} className={`chat-message chat-message--${m.role}`}>
                      <span className="chat-message__role">
                        {m.role === 'user' ? '你' : 'AI'}
                      </span>
                      <div className="chat-message__bubble">
                        {m.content || (m.role === 'ai' && chatting ? '回答生成中...' : '')}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {chatError && <Alert type="error" showIcon message={chatError} />}
            {messagesError && <Alert type="error" showIcon message={messagesError} />}
            {knowledgeError && <Alert type="error" showIcon message={knowledgeError} />}

            <form className="composer-simple" onSubmit={handleSend}>
              <div className="composer-simple__shell">
                <TextArea
                  className="composer-simple__textarea"
                  placeholder={
                    canChat
                      ? '请输入你的问题'
                      : knowledgeLoading
                        ? '正在读取知识库状态'
                        : '请先上传文档到知识库'
                  }
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={!canChat || chatting}
                  onKeyDown={handleComposerKeyDown}
                  rows={1}
                />
                {chatting ? (
                  <Button
                    htmlType="button"
                    onClick={handleStop}
                    className="composer-simple__submit composer-simple__submit--stop"
                  >
                    停止
                  </Button>
                ) : (
                  <Button
                    htmlType="submit"
                    type="primary"
                    disabled={!canChat || !input.trim()}
                    className="composer-simple__submit"
                  >
                    发送
                  </Button>
                )}
              </div>
            </form>
          </div>
        </Card>

        <Card
          className="panel chat-history-panel antd-panel-card"
          styles={{ body: { padding: 0, display: 'flex', flexDirection: 'column', minHeight: 0, height: '100%' } }}
        >
          <div className="page-antd-card-header">
            <div className="page-antd-card-title">历史会话</div>
            <div className="page-antd-card-description">{systemState.description}</div>
          </div>
          <div className="panel-content page-antd-card-body">
            <Button onClick={handleCreateSession} disabled={chatting}>
              新建会话
            </Button>

            {sessionsError && <Alert type="error" showIcon message={sessionsError} />}

            <div className="upload-history">
              {sessionsLoading ? (
                <div className="empty-box">正在加载历史会话...</div>
              ) : sessions.length === 0 ? (
                <div className="empty-box">暂无历史会话，发送第一条消息后会出现在这里。</div>
              ) : (
                <ul className="simple-list">
                  {sessions.map((session) => (
                    <li key={session.session_id}>
                      <div
                        className={
                          session.session_id === activeSessionId
                            ? 'session-list-item session-list-item--active'
                            : 'session-list-item'
                        }
                      >
                        <button
                          type="button"
                          className="session-list-item__main"
                          onClick={() => setActiveSessionId(session.session_id)}
                          disabled={chatting || deletingSessionId === session.session_id}
                        >
                          <strong>{session.title}</strong>
                          <span>{formatSessionUpdatedAt(session.updated_at)}</span>
                        </button>
                        <Button
                          className="session-list-item__delete"
                          type="text"
                          danger
                          aria-label={`删除会话 ${session.title}`}
                          onClick={() => setSessionPendingDelete(session)}
                          disabled={chatting || deletingSessionId === session.session_id}
                        >
                          <Trash2 size={18} strokeWidth={2.15} aria-hidden="true" />
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </Card>
      </div>

      <Modal
        open={sessionPendingDelete !== null}
        title="删除历史会话"
        okText={deletingSessionId ? '删除中...' : '确认删除'}
        cancelText="取消"
        onCancel={() => {
          if (!deletingSessionId) {
            setSessionPendingDelete(null)
          }
        }}
        onOk={() => void handleDeleteSession()}
        confirmLoading={Boolean(deletingSessionId)}
        okButtonProps={{ danger: true, className: 'session-delete-confirm' }}
        cancelButtonProps={{ disabled: Boolean(deletingSessionId) }}
        maskClosable={!deletingSessionId}
        destroyOnHidden
      >
        <p className="page-antd-modal-text">
          {sessionPendingDelete
            ? `确认删除“${sessionPendingDelete.title}”吗？删除后该会话消息将不可恢复。`
            : '确认删除该会话吗？'}
        </p>
      </Modal>
    </div>
  )
}
