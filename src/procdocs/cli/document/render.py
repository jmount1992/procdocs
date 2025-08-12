#!/usr/bin/env python3

# ------------------------------------------------------------------------------
# PROTOTYPE / LEGACY NOTICE
#
# This module is part of the *prototype document render pipeline*.
# It exists only to support the experimental CLI for rendering documents and
# will likely be replaced in 0.2.0 when the render architecture is implemented.
#
# Until then, treat this file as temporary/legacy code.
# ------------------------------------------------------------------------------

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from procdocs.core.app_context import AppContext
from procdocs.core.yaml_loader import load_yaml_with_includes
from procdocs.core.document.document import Document
from procdocs.core.render.engine import render_document

# Validation is optional; only used if --schema-root is provided
try:
    from procdocs.core.schema.registry import SchemaRegistry  # type: ignore
except Exception:
    SchemaRegistry = None  # type: ignore


def main(args, ctx: AppContext) -> int:
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

        # 3) Optional schema validation
        if args.schema_root:
            if SchemaRegistry is None:
                print("Warning: SchemaRegistry not available; skipping validation.")
            else:
                registry = SchemaRegistry.from_paths(args.schema_root)
                result = doc.validate(registry=registry)
                if hasattr(result, "has_errors") and result.has_errors():
                    print("Validation failed:")
                    for e in getattr(result, "errors", []):
                        print(f"  - {e}")
                    return 1

        # 4) Delegate to render engine
        render_document(
            document=doc,
            template_path=template_path,
            output_path=output_path,
            templates_roots=[template_path.parent],
            format_hint=args.format,  # may be None → engine will auto-detect by suffix
            extra_filters=None,       # wire in if/when you have custom filters
            base_url=template_path.parent,
            prepend_pdf=None,         # wire these via CLI flags in future if needed
            append_pdf=None,
        )

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
