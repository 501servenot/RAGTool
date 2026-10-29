export type ParserName = 'pypdf' | 'docling'

export interface UploadResponse {
  filename: string
  size_kb: number
  content_type: string
  message: string
  parser: ParserName | 'text'
}

export interface ParsePreviewResponse {
  filename: string
  parser: ParserName | 'text'
  format: 'text' | 'markdown'
  text: string
  characters: number
}

async function sendFile(file: File, parser: ParserName, path: string): Promise<Response> {
  const form = new FormData()
  form.append('file', file)
  form.append('parser', parser)

  const res = await fetch(path, {
    method: 'POST',
    body: form,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : `处理失败 (${res.status})`)
  }

  return res
}

export async function uploadFile(file: File, parser: ParserName = 'pypdf'): Promise<UploadResponse> {
  const res = await sendFile(file, parser, '/api/v1/upload')
  return (await res.json()) as UploadResponse
}

export async function previewFile(file: File, parser: ParserName): Promise<ParsePreviewResponse> {
  const res = await sendFile(file, parser, '/api/v1/upload/preview')
  return (await res.json()) as ParsePreviewResponse
}
