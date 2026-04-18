import re

from langchain_text_splitters import RecursiveCharacterTextSplitter


class SemanticTextSplitter:
    def __init__(
        self,
        *,
        chunk_size: int,
        chunk_overlap: int,
        separators: list[str],
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.fallback_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            length_function=len,
        )

    def split_text(self, text: str) -> list[str]:
        cleaned_text = self._normalize_text(text)
        if not cleaned_text:
            return []

        semantic_units: list[str] = []
        for block in self._split_blocks(cleaned_text):
            if len(block) <= self.chunk_size:
                semantic_units.append(block)
                continue
            semantic_units.extend(self._split_long_block(block))

        return self._merge_units(semantic_units)

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _split_blocks(self, text: str) -> list[str]:
        lines = text.split("\n")
        blocks: list[str] = []
        current: list[str] = []

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                if current:
                    blocks.append("\n".join(current).strip())
                    current = []
                continue

            if self._is_heading_or_list(line):
                if current:
                    blocks.append("\n".join(current).strip())
                    current = []
                blocks.append(line)
                continue

            current.append(line)

        if current:
            blocks.append("\n".join(current).strip())

        return [block for block in blocks if block]

    @staticmethod
    def _is_heading_or_list(line: str) -> bool:
        patterns = (
            r"^#{1,6}\s+",
            r"^[一二三四五六七八九十]+[、.．]",
            r"^\d+[.)、．]",
            r"^[-*+]\s+",
            r"^第[\d一二三四五六七八九十百]+[章节部分条]",
        )
        return any(re.match(pattern, line) for pattern in patterns)

    def _split_long_block(self, block: str) -> list[str]:
        sentences = self._split_sentences(block)
        if len(sentences) <= 1:
            return [chunk.strip() for chunk in self.fallback_splitter.split_text(block) if chunk.strip()]

        chunks: list[str] = []
        current = ""
        for sentence in sentences:
            if len(sentence) > self.chunk_size:
                if current:
                    chunks.append(current.strip())
                    current = ""
                chunks.extend(
                    [
                        chunk.strip()
                        for chunk in self.fallback_splitter.split_text(sentence)
                        if chunk.strip()
                    ]
                )
                continue

            candidate = sentence if not current else f"{current}{sentence}"
            if len(candidate) <= self.chunk_size:
                current = candidate
                continue

            if current:
                chunks.append(current.strip())
            current = sentence

        if current:
            chunks.append(current.strip())

        return chunks

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        parts = re.split(r"(?<=[。！？!?；;])|(?<=\.)\s+(?=[A-Z0-9\"'])", text)
        sentences = [part.strip() for part in parts if part and part.strip()]
        return [sentence if sentence.endswith("\n") else sentence for sentence in sentences]

    def _merge_units(self, units: list[str]) -> list[str]:
        chunks: list[str] = []
        current_units: list[str] = []

        for unit in units:
            candidate = self._join_units(current_units + [unit])
            if current_units and len(candidate) > self.chunk_size:
                chunk_text = self._join_units(current_units)
                if chunk_text:
                    chunks.append(chunk_text)
                current_units = self._build_overlap_units(current_units)
                overlap_candidate = self._join_units(current_units + [unit])
                if current_units and len(overlap_candidate) > self.chunk_size:
                    current_units = []
                current_units.append(unit)
                continue

            current_units.append(unit)

        final_chunk = self._join_units(current_units)
        if final_chunk:
            chunks.append(final_chunk)

        return chunks

    @staticmethod
    def _join_units(units: list[str]) -> str:
        if not units:
            return ""
        return "\n\n".join(unit.strip() for unit in units if unit.strip()).strip()

    def _build_overlap_units(self, units: list[str]) -> list[str]:
        if self.chunk_overlap <= 0:
            return []

        overlap_units: list[str] = []
        overlap_length = 0
        for unit in reversed(units):
            unit = unit.strip()
            if not unit:
                continue
            overlap_units.insert(0, unit)
            overlap_length += len(unit)
            if overlap_length >= self.chunk_overlap:
                break
        return overlap_units
