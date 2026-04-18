export interface KnowledgeDocument {
  document_id: string
  filename: string
  chunk_count: number
  create_time: string
  operator: string
}

export interface KnowledgeBaseSummaryResponse {
  document_count: number
  chunk_count: number
  documents: KnowledgeDocument[]
}

export interface DeleteKnowledgeDocumentResponse {
  document_id: string
  filename: string
  deleted_chunk_count: number
  message: string
}

export async function getKnowledgeDocuments(): Promise<KnowledgeBaseSummaryResponse> {
  const res = await fetch('/api/v1/knowledge-base/documents')

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`获取知识库失败 (${res.status}): ${text || res.statusText}`)
  }

  return (await res.json()) as KnowledgeBaseSummaryResponse
}

export async function deleteKnowledgeDocument(
  documentId: string,
): Promise<DeleteKnowledgeDocumentResponse> {
  const res = await fetch(`/api/v1/knowledge-base/documents/${documentId}`, {
    method: 'DELETE',
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`删除失败 (${res.status}): ${text || res.statusText}`)
  }

  return (await res.json()) as DeleteKnowledgeDocumentResponse
}
