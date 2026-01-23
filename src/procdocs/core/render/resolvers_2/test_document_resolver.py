# procdocs/rendering/resolvers/test_document_resolver.py
#!/usr/bin/env python3
"""
Purpose:
    Resolves a 'test-document' ProcDocs document by loading and validating
    referenced test documents from contents.includes[].tests[].filepath and
    embedding their contents into the render context.

Notes:
    This is an MVP resolver; later we can generalize "include resolvers" for other doc types.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from procdocs.core.document.document import Document
from procdocs.core.schema.registry import SchemaRegistry


class ResolveError(RuntimeError):
    """Raised when include resolution fails."""


@dataclass(frozen=True)
class ResolvedContext:
    """
    Context passed to templates.
    - doc/contents are aliases to the resolved contents dict.
    - metadata is the document's validated metadata (as a dict).
    """
    context: Dict[str, Any]


def resolve_test_document_for_render(
    *,
    test_document: Document,
    registry: SchemaRegistry,
    base_dir: Optional[Path] = None,
    strict_includes: bool = True,
) -> ResolvedContext:
    """
    Resolve include references in a test-document.

    Args:
        test_document: validated Document of type 'test-document'
        registry: SchemaRegistry used to validate included tests
        base_dir: base directory for relative filepaths; defaults to CWD for now (or pass doc path later if stored)
        strict_includes: if True, missing/invalid included tests raise; else they embed an error marker

    Returns:
        ResolvedContext suitable for docxtpl rendering.
    """
    doc_errors = test_document.validate(registry=registry)
    if doc_errors:
        raise ResolveError("test-document is not valid:\n" + "\n".join(doc_errors))

    contents = dict(test_document.contents or {})
    includes = contents.get("includes") or []
    if not isinstance(includes, list):
        raise ResolveError("contents.includes must be a list")

    base = Path(base_dir) if base_dir is not None else Path.cwd()

    resolved_includes: List[Dict[str, Any]] = []
    for gi, group_obj in enumerate(includes):
        if not isinstance(group_obj, dict):
            raise ResolveError(f"contents.includes[{gi}] must be a dict")

        group_name = group_obj.get("group")
        tests = group_obj.get("tests") or []
        if not isinstance(tests, list):
            raise ResolveError(f"contents.includes[{gi}].tests must be a list")

        resolved_tests: List[Dict[str, Any]] = []
        for ti, t_ref in enumerate(tests):
            if not isinstance(t_ref, dict):
                raise ResolveError(f"contents.includes[{gi}].tests[{ti}] must be a dict with 'filepath'")

            fp = t_ref.get("filepath")
            if not fp or not isinstance(fp, str):
                raise ResolveError(f"contents.includes[{gi}].tests[{ti}].filepath is missing or invalid")

            test_path = (base / fp).resolve()
            if not test_path.exists():
                msg = f"Included test file {str(test_path)!r} does not exist"
                if strict_includes:
                    raise ResolveError(msg)
                resolved_tests.append({"filepath": fp, "error": msg})
                continue

            try:
                test_doc = Document.from_file(test_path)
            except Exception as e:
                msg = f"Failed to load included test {str(test_path)!r}: {e}"
                if strict_includes:
                    raise ResolveError(msg) from e
                resolved_tests.append({"filepath": fp, "error": msg})
                continue

            test_errors = test_doc.validate(registry=registry)
            if test_errors:
                msg = f"Included test {test_path.name!r} is invalid:\n" + "\n".join(test_errors)
                if strict_includes:
                    raise ResolveError(msg)
                resolved_tests.append({"filepath": fp, "error": msg})
                continue

            resolved_tests.append(
                {
                    "filepath": fp,
                    "test": dict(test_doc.contents or {}),
                    "test_metadata": test_doc.metadata.model_dump(),
                }
            )

        resolved_includes.append({"group": group_name, "tests": resolved_tests})

    resolved_contents = dict(contents)
    resolved_contents["includes"] = resolved_includes

    ctx = {
        "metadata": test_document.metadata.model_dump(),
        "contents": resolved_contents,
        "doc": resolved_contents,  # alias
    }
    return ResolvedContext(context=ctx)
