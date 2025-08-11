#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Union

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

try:
    from weasyprint import HTML  # optional
    HAVE_WEASYPRINT = True
except Exception:
    HAVE_WEASYPRINT = False

from pypdf import PdfReader, PdfWriter  # lightweight


@dataclass
class Theme:
    data: Dict[str, Any]


def _build_env(
    templates_roots: Iterable[Path],
    extra_filters: Optional[Dict[str, Any]] = None
) -> Environment:
    loader = FileSystemLoader([str(Path(p).resolve()) for p in templates_roots])
    env = Environment(
        loader=loader,
        autoescape=select_autoescape(enabled_extensions=("html", "xml")),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    if extra_filters:
        env.filters.update(extra_filters)
    return env


def _detect_format(output_path: Path, explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    suf = output_path.suffix.lower()
    if suf in (".html", ".htm"):
        return "html"
    if suf == ".pdf":
        return "pdf"
    return "html"


class RenderEngine:
    """
    Stateless engine object holding a Jinja Environment.
    Prefer using render_document() for a one-shot convenience wrapper.
    """

    def __init__(self, templates_roots: Iterable[Path], filters: Optional[Dict[str, Any]] = None):
        self.env = _build_env(templates_roots, filters)

    def render_html(self, template_path: Path, context: Dict[str, Any]) -> str:
        # Template can be loaded by name relative to any root
        template = self.env.get_template(template_path.name)
        return template.render(**context)

    def html_to_pdf(self, html_str: str, out_pdf: Path, base_url: Optional[str] = None):
        if not HAVE_WEASYPRINT:
            raise RuntimeError("PDF rendering requires weasyprint to be installed")
        HTML(string=html_str, base_url=base_url).write_pdf(target=str(out_pdf))


class PdfAssembler:
    @staticmethod
    def assemble(out_pdf: Path, prepend: Optional[Path] = None, append: Optional[Path] = None):
        if not prepend and not append:
            return
        writer = PdfWriter()

        def _add(pdf_path: Optional[Path]):
            if pdf_path:
                reader = PdfReader(str(pdf_path))
                for page in reader.pages:
                    writer.add_page(page)

        # write to temp then replace, to avoid partial files on error
        tmp = out_pdf.with_suffix(".tmp.pdf")
        _add(prepend)
        _add(out_pdf)
        _add(append)
        with open(tmp, "wb") as f:
            writer.write(f)
        tmp.replace(out_pdf)


def _build_context(doc: Any) -> Dict[str, Any]:
    """
    Normalize context so templates can use:
      - `doc` (the object itself)
      - `metadata` and `contents` for legacy templates
    Works for either a Pydantic Document instance or a raw dict.
    """
    metadata = getattr(doc, "metadata", None)
    contents = getattr(doc, "_contents", None)

    if isinstance(doc, dict):
        # If caller passed raw dict, offer best-effort keys
        metadata = doc.get("metadata")
        contents = doc.get("contents")

    return {
        "doc": doc,
        "metadata": metadata,
        "contents": contents,
    }


def render_document(
    *,
    document: Union[dict, Any],
    template_path: Path,
    output_path: Path,
    templates_roots: Optional[Iterable[Path]] = None,
    format_hint: Optional[str] = None,
    extra_filters: Optional[Dict[str, Any]] = None,
    base_url: Optional[Path] = None,
    prepend_pdf: Optional[Path] = None,
    append_pdf: Optional[Path] = None,
) -> None:
    """
    One-shot convenience API to render a document to HTML or PDF.

    - `document`: Pydantic instance or raw dict.
    - `template_path`: path to a Jinja template file.
    - `output_path`: path where .html or .pdf will be written.
    - `templates_roots`: search roots for Jinja (defaults to template_path.parent).
    - `format_hint`: "html" or "pdf"; if None, auto-detected from output_path suffix.
    - `extra_filters`: optional Jinja filters to register.
    - `base_url`: base path for WeasyPrint to resolve relative assets (defaults to template dir).
    - `prepend_pdf` / `append_pdf`: optional PDF files to stitch around output (PDF only).

    Raises:
      - RuntimeError if PDF requested without WeasyPrint installed.
      - FileNotFoundError for missing template.
      - OSError for I/O failures.
    """
    template_path = Path(template_path).resolve()
    output_path = Path(output_path).resolve()
    templates_roots = list(templates_roots or [template_path.parent.resolve()])

    engine = RenderEngine(templates_roots, filters=extra_filters)
    ctx = _build_context(document)

    html = engine.render_html(template_path, ctx)

    out_format = _detect_format(output_path, format_hint)
    if out_format == "html":
        output_path.write_text(html, encoding="utf-8")
        return

    if out_format == "pdf":
        if not HAVE_WEASYPRINT:
            raise RuntimeError("PDF rendering requires 'weasyprint'. Install it or use HTML output.")
        base = str((base_url or template_path.parent))
        engine.html_to_pdf(html, output_path, base_url=base)
        # optional stitching
        if prepend_pdf or append_pdf:
            PdfAssembler.assemble(output_path, prepend=prepend_pdf, append=append_pdf)
        return

    raise ValueError(f"Unsupported format: {out_format}")
