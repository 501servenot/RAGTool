from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.core.config import get_settings


class VectorStoreService(object):
    def __init__(self, embedding):
        settings = get_settings()
        self.embedding = embedding
        self.vector_store = Chroma(
            collection_name=settings.collection_name,
            embedding_function=self.embedding,
            persist_directory=settings.persist_directory,
        )

    def get_retriever(self, top_k: int | None = None):
        settings = get_settings()
        search_k = settings.retrieve_top_k if top_k is None else top_k
        return self.vector_store.as_retriever(
            search_kwargs={"k": search_k}
        )

    def retrieve(self, query: str, *, top_k: int | None = None):
        retriever = self.get_retriever(top_k=top_k)
        return retriever.invoke(query)

    def expand_with_neighbors(
        self,
        docs: list[Document],
        *,
        neighbor_window: int | None = None,
    ) -> list[Document]:
        settings = get_settings()
        window = (
            settings.retrieval_neighbor_chunks
            if neighbor_window is None
            else max(neighbor_window, 0)
        )
        if window <= 0 or not docs:
            return docs

        expanded_docs: list[Document] = []
        seen_keys: set[tuple[str, int]] = set()
        document_cache: dict[str, list[Document]] = {}

        for anchor_doc in docs:
            metadata = anchor_doc.metadata or {}
            document_id = metadata.get("document_id")
            chunk_index = self._normalize_chunk_index(metadata.get("chunk_index"))

            if not document_id or chunk_index is None:
                self._append_doc(
                    expanded_docs=expanded_docs,
                    seen_keys=seen_keys,
                    doc=self._mark_doc(anchor_doc, relation="hit", distance=0),
                )
                continue

            if document_id not in document_cache:
                document_cache[document_id] = self._get_document_chunks(document_id)

            ordered_docs = document_cache[document_id]
            chunk_position = self._find_chunk_position(ordered_docs, chunk_index)
            if chunk_position is None:
                self._append_doc(
                    expanded_docs=expanded_docs,
                    seen_keys=seen_keys,
                    doc=self._mark_doc(anchor_doc, relation="hit", distance=0),
                )
                continue

            start = max(0, chunk_position - window)
            end = min(len(ordered_docs), chunk_position + window + 1)
            for idx in range(start, end):
                related_doc = anchor_doc if idx == chunk_position else ordered_docs[idx]
                distance = idx - chunk_position
                relation = "hit" if distance == 0 else "neighbor"
                self._append_doc(
                    expanded_docs=expanded_docs,
                    seen_keys=seen_keys,
                    doc=self._mark_doc(
                        related_doc,
                        relation=relation,
                        distance=distance,
                        anchor_chunk_index=chunk_index,
                    ),
                )

        return expanded_docs

    def _get_document_chunks(self, document_id: str) -> list[Document]:
        result = self.vector_store.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"],
        )
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])

        ordered_docs = []
        for text, metadata in zip(documents, metadatas):
            metadata = dict(metadata or {})
            ordered_docs.append(
                Document(
                    page_content=text or "",
                    metadata=metadata,
                )
            )

        ordered_docs.sort(key=lambda doc: doc.metadata.get("chunk_index", 0))
        return ordered_docs

    @staticmethod
    def _find_chunk_position(docs: list[Document], chunk_index: int) -> int | None:
        for idx, doc in enumerate(docs):
            current_chunk_index = VectorStoreService._normalize_chunk_index(
                doc.metadata.get("chunk_index")
            )
            if current_chunk_index == chunk_index:
                return idx
        return None

    @staticmethod
    def _normalize_chunk_index(chunk_index) -> int | None:
        if isinstance(chunk_index, int):
            return chunk_index
        if isinstance(chunk_index, str) and chunk_index.isdigit():
            return int(chunk_index)
        return None

    @staticmethod
    def _mark_doc(
        doc: Document,
        *,
        relation: str,
        distance: int,
        anchor_chunk_index: int | None = None,
    ) -> Document:
        metadata = dict(doc.metadata or {})
        metadata["context_relation"] = relation
        metadata["context_distance"] = distance
        if anchor_chunk_index is not None:
            metadata["anchor_chunk_index"] = anchor_chunk_index
        return Document(page_content=doc.page_content, metadata=metadata)

    @staticmethod
    def _append_doc(
        *,
        expanded_docs: list[Document],
        seen_keys: set[tuple[str, int]],
        doc: Document,
    ) -> None:
        metadata = doc.metadata or {}
        document_id = metadata.get("document_id", "")
        normalized_chunk_index = VectorStoreService._normalize_chunk_index(
            metadata.get("chunk_index")
        )
        chunk_key = normalized_chunk_index if normalized_chunk_index is not None else -1
        key = (str(document_id), chunk_key)
        if key in seen_keys:
            return
        seen_keys.add(key)
        expanded_docs.append(doc)
