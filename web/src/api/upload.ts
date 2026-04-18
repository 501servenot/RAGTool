export interface UploadResponse {
  filename: string
  size_kb: number
  content_type: string
  message: string
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)

  const res = await fetch('/api/v1/upload', {
    method: 'POST',
    body: form,
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`上传失败 (${res.status}): ${text || res.statusText}`)
  }

  return (await res.json()) as UploadResponse
}
