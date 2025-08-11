#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple

import yaml
from pydantic import ValidationError

from procdocs.core.config import load_config  # expects a config with .schema_roots or similar
from procdocs.core.constants import DEFAULT_TEXT_ENCODING
from procdocs.core.document.document import Document
from procdocs.core.registry import SchemaRegistry

SUPPORTED_EXTENSIONS = {".yml", ".yaml"}


def find_all_files(paths: Iterable[str | Path], recursive: bool = False) -> List[Path]:
    files: List[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(p)
        elif p.is_dir():
            it = p.rglob("*") if recursive else p.glob("*")
            files.extend(q for q in it if q.is_file() and q.suffix.lower() in SUPPORTED_EXTENSIONS)
    # stable order for output
    return sorted(set(files))


def _build_registry(cli_roots: Iterable[str | Path] | None) -> SchemaRegistry:
    # Prefer CLI-provided roots, else fall back to config
    if cli_roots:
        roots = [Path(r) for r in cli_roots]
    else:
        cfg = load_config()  # your existing loader
        # support either attr or dict style
        roots = [Path(p) for p in getattr(cfg, "schema_roots", getattr(cfg, "schema_paths", []))]
    reg = SchemaRegistry(roots)
    reg.load()
    return reg


def validate_document(file_path: Path, registry: SchemaRegistry) -> Tuple[bool, str, List[str]]:
    """
    Returns: (is_valid, summary_message, error_list)
    """
    # Fast check for metadata.document_type presence to improve UX on obviously broken files
    try:
        raw = yaml.safe_load(file_path.read_text(encoding=DEFAULT_TEXT_ENCODING)) or {}
    except Exception as e:
        return False, f"{file_path}: Failed to read YAML ({e})", []

    md = (raw or {}).get("metadata", {})
    doc_type = (md or {}).get("document_type")
    if not doc_type:
        return False, f"{file_path}: Missing metadata.document_type", []

    # Full parse + validation
    try:
        doc = Document.from_file(file_path)
    except ValidationError as e:
        # Pydantic error while parsing the document itself (e.g., wrong metadata shape)
        # Keep it simple; print first few messages
        msgs = [f"{'.'.join(map(str, err.get('loc', ()) )) or '<root>'}: {err.get('msg','Validation error')}" for err in e.errors()]
        return False, f"{file_path}: Invalid document structure", msgs

    errors = doc.validate(registry=registry)
    if errors:
        return False, f"{file_path}: Validation failed", errors

    return True, f"{file_path}: OK", []


def main(args):
    registry = _build_registry(getattr(args, "schema_root", None))

    files = find_all_files(args.files, recursive=args.recursive)
    if not files:
        print("No YAML files found.")
        return 1

    success = 0
    for fp in files:
        ok, msg, errs = validate_document(fp, registry)
        if args.verbose or not ok:
            print(msg)
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
        help="Override schema roots (can be passed multiple times). If omitted, uses config schema_roots.",
    )
    parser.set_defaults(func=main)
