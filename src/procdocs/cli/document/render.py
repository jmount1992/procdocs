#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Optional
from pydantic import ValidationError

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

# PDF is optional; if not installed, HTML still works
try:
    from weasyprint import HTML  # type: ignore
    HAVE_WEASYPRINT = True
except Exception:
    HAVE_WEASYPRINT = False

from procdocs.core.yaml_loader import load_yaml_with_includes
from procdocs.core.document.document import Document

# Validation is optional; only used if --schema-root is provided
try:
    from procdocs.core.schema.registry import SchemaRegistry  # type: ignore
except Exception:
    SchemaRegistry = None  # type: ignore


def _detect_format(output_path: Path, explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    suf = output_path.suffix.lower()
    if suf in (".html", ".htm"):
        return "html"
    if suf == ".pdf":
        return "pdf"
    return "html"


def main(args) -> int:
    try:
        doc_path = Path(args.doc_path).resolve()
        template_path = Path(args.template_path).resolve()
        output_path = Path(args.output_path).resolve()

        # 1) Load YAML (+ includes)
        allowed_roots = [doc_path.parent]
        if args.includes_root:
            allowed_roots.append(Path(args.includes_root).resolve())
        raw = load_yaml_with_includes(doc_path, allowed_roots)

        # 2) Build Document (Pydantic v2)
        try:
            doc = Document.model_validate(raw)  # Pydantic v2
        except ValidationError as ve:
            print("Validation failed (Pydantic field errors):")
            for err in ve.errors():
                loc = ".".join(str(p) for p in err.get("loc", []))
                print(f"  - {loc}: {err.get('msg')}")
            return 1

        # 3) Optional validation if schema roots supplied
        if args.schema_root:
            if SchemaRegistry is None:
                print("Warning: SchemaRegistry not available; skipping validation.")
            else:
                registry = SchemaRegistry.from_paths(args.schema_root)
                result = doc.validate(registry=registry)
                # Accept either raising or returning a result container
                if hasattr(result, "has_errors") and result.has_errors():
                    print("Validation failed:")
                    for e in getattr(result, "errors", []):
                        print(f"  - {e}")
                    return 1

        # 4) Render via Jinja2
        env = Environment(
            loader=FileSystemLoader([str(template_path.parent)]),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=select_autoescape(enabled_extensions=("html", "xml")),
        )
        template = env.get_template(template_path.name)

        # Keep context minimal; also expose legacy keys if your older templates need them
        html = template.render(
            doc=doc,
            metadata=getattr(doc, "metadata", None),
            contents=getattr(doc, "_contents", None),
        )

        # 5) Output
        out_format = _detect_format(output_path, args.format)
        if out_format == "html":
            output_path.write_text(html, encoding="utf-8")
        elif out_format == "pdf":
            if not HAVE_WEASYPRINT:
                print("Error: PDF rendering requires 'weasyprint'. Install it or use --format html.")
                return 1
            # base_url lets relative assets (CSS/images) in the template resolve
            HTML(string=html, base_url=str(template_path.parent)).write_pdf(str(output_path))
        else:
            print(f"Unsupported format: {out_format}")
            return 1

        print(f"Rendered {doc_path.name} → {output_path}")
        return 0

    except Exception as e:
        print(f"Error rendering document:\n  {e}")
        return 1


def register(subparser):
    parser = subparser.add_parser(
        "render",
        help="Render a YAML document with a Jinja2 template to HTML or PDF."
    )
    parser.add_argument("doc_path", help="Path to the YAML document instance.")
    parser.add_argument("template_path", help="Path to the Jinja2 HTML template.")
    parser.add_argument("output_path", help="Output file (.html or .pdf).")
    parser.add_argument("--includes-root", help="Extra root allowed for !include/!includeglob.")
    parser.add_argument("--schema-root", nargs="*", help="Optional schema root(s) to validate against.")
    parser.add_argument("--format", choices=["html", "pdf"], help="Override output format.")
    parser.set_defaults(func=main)
