#!/usr/bin/env python3
"""
Purpose:
    Render a ProcDocs YAML document into a .docx using a Jinja2-style Word template
    (docxtpl). MVP renderer intended for technical users.

Notes:
    - Context always exposes:
        * metadata: document metadata (dict)
        * contents: resolved document contents (dict)
        * doc: alias of contents (dict)
    - Reference resolution is schema-driven:
        any FieldType.REF in the schema will be resolved before rendering.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from procdocs.core.app_context import AppContext
from procdocs.core.document.document import Document
from procdocs.core.render.docx_jinja_render import DocxJinjaRenderer, RenderError
from procdocs.core.render.reference_resolver import ReferenceResolver, ResolveError


def render(args, ctx: AppContext) -> int:
    doc_path = Path(args.document).resolve()
    template_path = Path(args.template).resolve()
    out_path = Path(args.output).resolve()
    dump_context_path = Path(args.dump_context).resolve() if args.dump_context else None

    base_dir = Path(args.base_dir).resolve() if args.base_dir else doc_path.parent
    strict_refs: bool = args.strict_refs

    # --- Load document --- #
    try:
        doc = Document.from_file(doc_path)
    except Exception as e:
        print(f"ERROR: failed to load document {str(doc_path)!r}: {e}")
        return 1

    # --- Validate document --- #
    errors = doc.validate(registry=ctx.schemas)
    if errors:
        print(f"ERROR: document {doc_path.name!r} is invalid:")
        for msg in errors:
            print(f"  - {msg}")
        return 1

    # --- Resolve schema --- #
    try:
        schema = ctx.schemas.require(doc.metadata.document_type)
    except Exception as e:
        print(f"ERROR: schema resolution failed for document_type {doc.metadata.document_type!r}: {e}")
        return 1

    # --- Resolve refs (schema-driven) --- #
    resolver = ReferenceResolver()
    try:
        result = resolver.resolve(
            contents=dict(doc.contents or {}),
            schema=schema,
            registry=ctx.schemas,
            base_dir=base_dir,
            strict=strict_refs,
        )
        resolved_contents = result.contents
        warnings = result.warnings
    except ResolveError as e:
        print(f"ERROR: failed to resolve references in {doc_path.name!r}: {e}")
        return 1

    # --- Build template context --- #
    context: Dict[str, Any] = {
        "metadata": doc.metadata.model_dump(),
        "contents": resolved_contents,
        "doc": resolved_contents,
        "source_path": str(doc_path),
    }
    if warnings:
        context["resolve_warnings"] = warnings

    # Optional: dump context for template iteration
    if dump_context_path:
        try:
            dump_context_path.parent.mkdir(parents=True, exist_ok=True)
            dump_context_path.write_text(
                json.dumps(context, indent=2, sort_keys=True, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"Context dumped to {dump_context_path}")
        except Exception as e:
            print(f"ERROR: failed to dump context to {str(dump_context_path)!r}: {e}")
            return 1

    # --- Render --- #
    renderer = DocxJinjaRenderer()
    try:
        renderer.render(template_path=template_path, context=context, out_path=out_path)
    except RenderError as e:
        print(f"ERROR: render failed: {e}")
        return 1

    print(f"Rendered: {out_path}")
    return 0


def register(subparser):
    parser = subparser.add_parser(
        "render",
        help="Render a ProcDocs YAML document to .docx using a Jinja2-style Word template.",
    )
    parser.add_argument("document", help="Path to the YAML document to render.")
    parser.add_argument("template", help="Path to the .docx template (docxtpl/Jinja2).")
    parser.add_argument("output", help="Path to write the rendered .docx.")

    parser.add_argument(
        "--base-dir",
        default=None,
        help="Base directory for resolving relative ref paths (default: document's folder).",
    )
    parser.add_argument(
        "--dump-context",
        dest="dump_context",
        default=None,
        help="Optional path to write the resolved render context as JSON (for template debugging).",
    )

    strict_group = parser.add_mutually_exclusive_group()
    strict_group.add_argument(
        "--strict-refs",
        dest="strict_refs",
        action="store_true",
        default=True,
        help="Fail rendering if any schema-declared refs cannot be resolved (default).",
    )
    strict_group.add_argument(
        "--no-strict-refs",
        dest="strict_refs",
        action="store_false",
        help="Render even if refs fail; warnings will be exposed via 'resolve_warnings'.",
    )

    parser.set_defaults(func=render)
