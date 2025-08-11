# procdocs/core/render/engine.py

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

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


def _build_env(templates_roots: Iterable[Path], extra_filters: Optional[Dict[str, Any]] = None) -> Environment:
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


class RenderEngine:
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

        def _add(pdf_path: Path):
            if pdf_path:
                reader = PdfReader(str(pdf_path))
                for page in reader.pages:
                    writer.add_page(page)

        _add(prepend)
        _add(out_pdf)
        _add(append)

        tmp = out_pdf.with_suffix(".tmp.pdf")
        with open(tmp, "wb") as f:
            writer.write(f)
        tmp.replace(out_pdf)
