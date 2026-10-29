"""Run with: .venv/Scripts/python.exe -m unittest discover -s tests -v"""
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "RAG"))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from app.api.deps import get_kb_service
from app.api.v1.endpoints.upload import router
from app.utils.file_reader import _parse_pdf, extract_text_from_pdf


def sample_pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(300, 300)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                             NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 30 250 Td (Sample equation x = 1) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    result = BytesIO()
    writer.write(result)
    return result.getvalue()


class UploadParserTests(unittest.TestCase):
    def setUp(self):
        _parse_pdf.cache_clear()
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/v1")
        self.kb = Mock()
        self.kb.upload_by_str.return_value = "成功"
        self.dependency = Mock(return_value=self.kb)
        self.app.dependency_overrides[get_kb_service] = lambda: self.dependency()
        self.client = TestClient(self.app)
        self.pdf = sample_pdf()

    def tearDown(self):
        self.client.close()
        _parse_pdf.cache_clear()

    def post(self, path="preview", parser=None, filename="sample.pdf", content=None):
        data = {} if parser is None else {"parser": parser}
        return self.client.post("/api/v1/upload" + ("/preview" if path else ""), data=data,
                                files={"file": (filename, self.pdf if content is None else content)})

    def test_default_pypdf_preview_is_original_text_and_never_resolves_kb(self):
        result = self.post()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["parser"], "pypdf")
        self.assertEqual(result.json()["text"], extract_text_from_pdf(BytesIO(self.pdf)))
        self.assertIn("x = 1", result.json()["text"])
        self.dependency.assert_not_called()

    def test_docling_preview_upload_reuses_identical_result(self):
        with patch("app.utils.docling_reader.extract_with_docling", return_value="# Result\n\nx = 1") as parse:
            preview = self.post(parser="docling").json()
            uploaded = self.post(path="", parser="docling")
            self.assertEqual(uploaded.status_code, 200)
            self.assertEqual(uploaded.json()["parser"], "docling")
            self.assertEqual(preview["format"], "markdown")
            parse.assert_called_once_with(self.pdf)
            self.kb.upload_by_str.assert_called_once_with(preview["text"], "sample.pdf")
            other = self.post(parser="pypdf").json()
            self.assertNotEqual(other["text"], preview["text"])

    def test_text_files_do_not_use_pdf_parser(self):
        with patch("app.utils.docling_reader.extract_with_docling") as parse:
            result = self.post(parser="docling", filename="note.md", content="# 标题".encode()).json()
            self.assertEqual(result["parser"], "text")
            self.assertEqual(result["text"], "# 标题")
            parse.assert_not_called()

    def test_invalid_parser_file_and_encoding_are_client_errors(self):
        self.assertEqual(self.post(parser="invalid").status_code, 422)
        self.assertEqual(self.post(content=b"broken PDF").status_code, 400)
        self.assertEqual(self.post(filename="bad.txt", content=b"\xff").status_code, 400)
        self.assertEqual(self.post(filename="bad.exe", content=b"binary").status_code, 400)
        self.kb.upload_by_str.assert_not_called()

    def test_empty_preview_allowed_but_empty_upload_rejected(self):
        self.assertEqual(self.post(filename="empty.txt", content=b"").json()["characters"], 0)
        self.assertEqual(self.post(path="", filename="empty.txt", content=b"").status_code, 400)
        self.kb.upload_by_str.assert_not_called()

    def test_missing_docling_does_not_fallback_silently(self):
        with patch("app.utils.docling_reader.subprocess.run", return_value=SimpleNamespace(returncode=42)):
            result = self.post(parser="docling")
            self.assertEqual(result.status_code, 503)
            self.assertIn("安装 Docling", result.json()["detail"])
        self.assertEqual(self.post().status_code, 200)


if __name__ == "__main__":
    unittest.main()
