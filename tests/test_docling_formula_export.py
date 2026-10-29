"""Run with the optional Docling interpreter; skips when Docling is not installed."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "RAG"))
from app.utils.docling_worker import export_markdown

try:
    from docling_core.types.doc import DoclingDocument, DocItemLabel
except ImportError:
    DoclingDocument = None


@unittest.skipIf(DoclingDocument is None, "Requires optional Docling environment")
class FormulaExportTests(unittest.TestCase):
    def test_native_formula_is_kept_in_reading_order(self):
        doc = DoclingDocument(name="sample")
        doc.add_text(label=DocItemLabel.TEXT, text="before")
        doc.add_text(label=DocItemLabel.FORMULA, text="", orig="y = W9h8 + b9")
        doc.add_text(label=DocItemLabel.TEXT, text="after")
        result = export_markdown(doc)
        self.assertIn("未恢复数学排版", result)
        self.assertIn("y = W9h8 + b9", result)
        self.assertNotIn("formula-not-decoded", result)
        self.assertNotIn("$$", result)
        self.assertLess(result.index("before"), result.index("y ="))
        self.assertLess(result.index("y ="), result.index("after"))

    def test_decoded_latex_is_unchanged(self):
        doc = DoclingDocument(name="sample")
        doc.add_text(label=DocItemLabel.FORMULA, text=r"x^{2}", orig="x2")
        self.assertEqual(export_markdown(doc), doc.export_to_markdown())

    def test_empty_formula_is_not_silently_removed(self):
        doc = DoclingDocument(name="sample")
        doc.add_text(label=DocItemLabel.FORMULA, text="", orig="")
        self.assertIn("公式未能提取", export_markdown(doc))


if __name__ == "__main__":
    unittest.main()
