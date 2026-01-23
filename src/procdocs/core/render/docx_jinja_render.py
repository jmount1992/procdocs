#!/usr/bin/env python3
"""
Purpose:
    Renders ProcDocs documents into .docx using a Jinja2-style template embedded
    in a Word document (via docxtpl). This is the MVP rendering backend.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class RenderError(RuntimeError):
    """Raised when a render operation fails (template missing, render exception, etc.)."""


@dataclass(frozen=True)
class RenderResult:
    out_path: Path
    template_path: Path


class DocxJinjaRenderer:
    """
    Render a .docx template using docxtpl with a plain-Python context.
    """

    def render(self, *, template_path: Path, context: Mapping[str, Any], out_path: Path) -> RenderResult:
        template_path = Path(template_path)
        out_path = Path(out_path)

        if not template_path.exists():
            raise RenderError(f"Template file {str(template_path)!r} does not exist")
        if template_path.suffix.lower() != ".docx":
            raise RenderError(f"Template {template_path.name!r} must be a .docx file")

        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # docxtpl is an optional dependency for now; keep failure message friendly.
            from docxtpl import DocxTemplate  # type: ignore
        except Exception as e:
            raise RenderError(
                "docxtpl is not installed (required for .docx Jinja templating). "
                "Install it with: pip install docxtpl"
            ) from e

        try:
            doc = DocxTemplate(str(template_path))
            doc.render(dict(context))
            doc.save(str(out_path))
            return RenderResult(out_path=out_path, template_path=template_path)
        except Exception as e:
            raise RenderError(f"Failed to render template {template_path.name!r}: {e}") from e
