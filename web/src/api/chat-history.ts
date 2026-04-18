export interface ChatSessionSummary {
  session_id: string
  title: string
  updated_at: string
}

export interface ChatHistoryMessage {
  role: 'user' | 'ai'
  content: string
}

export interface DeleteChatSessionResponse {
  session_id: string
  message: string
}

export async function getChatSessions(): Promise<ChatSessionSummary[]> {
  const res = await fetch('/api/v1/chat/sessions')

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`获取历史会话失败 (${res.status}): ${text || res.statusText}`)
  }

  return (await res.json()) as ChatSessionSummary[]
}

export async function getChatSessionMessages(
  sessionId: string,
): Promise<ChatHistoryMessage[]> {
  const res = await fetch(`/api/v1/chat/sessions/${encodeURIComponent(sessionId)}/messages`)

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`获取会话消息失败 (${res.status}): ${text || res.statusText}`)
  }

  return (await res.json()) as ChatHistoryMessage[]
}

export async function deleteChatSession(
  sessionId: string,
): Promise<DeleteChatSessionResponse> {
  const res = await fetch(`/api/v1/chat/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`删除会话失败 (${res.status}): ${text || res.statusText}`)
  }

  return (await res.json()) as DeleteChatSessionResponse
}
