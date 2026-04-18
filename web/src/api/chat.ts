export async function streamChat(
  prompt: string,
  sessionId: string,
  onToken: (token: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, session_id: sessionId }),
    signal,
  })

  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => '')
    throw new Error(`对话请求失败 (${res.status}): ${text || res.statusText}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const events = buffer.split('\n\n')
    buffer = events.pop() ?? ''

    for (const evt of events) {
      const line = evt.replace(/^data:\s*/, '').trim()
      if (!line) continue
      if (line === '[DONE]') return
      try {
        const payload = JSON.parse(line) as { token?: string; error?: string }
        if (payload.error) throw new Error(payload.error)
        if (payload.token) onToken(payload.token)
      } catch (err) {
        if (err instanceof SyntaxError) continue
        throw err
      }
    }
  }
}
