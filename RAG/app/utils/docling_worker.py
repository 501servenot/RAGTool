"""CLI helper, callable from either the backend or an optional Docling environment."""
from pathlib import Path
import sys


def export_markdown(document):
    """Keep native formula characters when formula-to-LaTeX enrichment yields no text."""
    from docling_core.types.doc import FormulaItem
    from docling_core.transforms.serializer.common import create_ser_result
    from docling_core.transforms.serializer.markdown import MarkdownDocSerializer, MarkdownTextSerializer

    class FormulaTextFallback(MarkdownTextSerializer):
        def serialize(self, *, item, **kwargs):
            if isinstance(item, FormulaItem) and not item.text.strip():
                pages = sorted({p.page_no for p in item.prov})
                source = "PDF 第 " + "、".join(map(str, pages)) + " 页；" if pages else ""
                original = item.orig.strip()
                text = (f"【公式原始文字：{source}未恢复数学排版】\n\n{original}"
                        if original else f"【公式未能提取：{source}请查看原文】")
                return create_ser_result(text=text, span_source=item)
            return super().serialize(item=item, **kwargs)

    return MarkdownDocSerializer(doc=document, text_serializer=FormulaTextFallback()).serialize().text


def main():
    try:
        from docling.datamodel.base_models import InputFormat, ConversionStatus
        from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
    except ImportError:
        return 42

    options = PdfPipelineOptions()
    options.accelerator_options = AcceleratorOptions(num_threads=4)
    options.do_formula_enrichment = True
    options.do_code_enrichment = False
    options.do_picture_description = False
    options.enable_remote_services = False
    converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
    result = converter.convert(Path(sys.argv[1]), raises_on_error=False)
    if result.status != ConversionStatus.SUCCESS:
        raise RuntimeError(f"Incomplete PDF conversion: {result.status}")
    Path(sys.argv[2]).write_text(export_markdown(result.document), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
