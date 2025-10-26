#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple

import yaml
from pydantic import ValidationError

from procdocs.core.app_context import AppContext
from procdocs.core.constants import DEFAULT_TEXT_ENCODING
from procdocs.core.document.document import Document
from procdocs.core.schema.registry import SchemaRegistry

SUPPORTED_EXTENSIONS = {".yml", ".yaml"}


def _is_supported_yaml_file(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS


def _yaml_files_in_dir(root: Path, recursive: bool) -> list[Path]:
    if not root.is_dir():
        return []
    if recursive:
        # search each extension explicitly; pathlib has no brace expansion
        files = []
        for ext in SUPPORTED_EXTENSIONS:
            files.extend(root.rglob(f"*{ext}"))
        return [p for p in files if p.is_file()]
    # non-recursive
    return [p for p in root.glob("*") if _is_supported_yaml_file(p)]


def find_all_files(paths: Iterable[str | Path], recursive: bool = False) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if _is_supported_yaml_file(p):
            files.append(p)
        else:
            files.extend(_yaml_files_in_dir(p, recursive))
    # stable, de-duplicated order
    return sorted(set(files))


def _registry_for_run(args, ctx: AppContext) -> SchemaRegistry:
    """
    Prefer CLI-provided roots for this run; otherwise, use the preloaded registry from context.
    When overriding, we build a temporary registry so we don't mutate global state.
    """
    if getattr(args, "schema_root", None):
        roots = [Path(r) for r in args.schema_root]
        reg = SchemaRegistry(roots)
        reg.load(clear=True)
        return reg
    return ctx.schemas


def validate_document(file_path: Path, registry: SchemaRegistry) -> Tuple[bool, str, List[str]]:
    """
    Returns: (is_valid, summary_message, error_list)
    """
    ok, msg, errs = _quick_yaml_checks(file_path)
    if not ok:
        return False, msg, errs

    # Full parse + structure validation
    try:
        doc = Document.from_file(file_path)
    except ValidationError as e:
        return False, f"{file_path}: Invalid document structure", _pydantic_errors(e)

    # Schema validation
    errors = doc.validate(registry=registry)
    if errors:
        return False, f"{file_path}: Validation Failed", errors

    return True, f"{file_path}: Validation Passed", []


def validate(args, ctx: AppContext) -> int:
    registry = _registry_for_run(args, ctx)

    files = find_all_files(args.files, recursive=args.recursive)
    if not files:
        print("No YAML files found.")
        return 1

    success = 0
    for fp in files:
        ok, msg, errs = validate_document(fp, registry)
        print(f"\n{msg}")
        if not ok:
            for e in errs:
                print(f"  - {e}")
        if ok:
            success += 1

    total = len(files)
    print(f"\nValidation complete: {success}/{total} passed.")
    return 0 if success == total else 1


def register(subparser):
    parser = subparser.add_parser("validate", help="Validate YAML documents against their schemas.")
    parser.add_argument("files", nargs="+", help="Files or directories to validate.")
    parser.add_argument("--recursive", "-r", action="store_true", help="Recursively scan directories.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all results, not only errors.")
    parser.add_argument(
        "--schema-root",
        action="append",
        default=None,
        help="Override schema roots just for this run (can be used multiple times).",
    )
    parser.set_defaults(func=validate)


def _quick_yaml_checks(file_path: Path) -> Tuple[bool, str, List[str]]:
    """Fast YAML load and presence of metadata.document_type."""
    try:
        raw = yaml.safe_load(file_path.read_text(encoding=DEFAULT_TEXT_ENCODING)) or {}
    except Exception as e:
        return False, f"{file_path}: Failed to read YAML ({e})", []
    md = (raw or {}).get("metadata", {})
    doc_type = (md or {}).get("document_type")
    if not doc_type:
        return False, f"{file_path}: Missing metadata.document_type", []
    return True, "", []


def _pydantic_errors(e: ValidationError) -> List[str]:
    """Flatten pydantic errors to 'path: message' strings (keeps existing behavior)."""
    return [
        f"{'.'.join(map(str, err.get('loc', ()))) or '<root>'}: {err.get('msg', 'Validation error')}"
        for err in e.errors()
    ]