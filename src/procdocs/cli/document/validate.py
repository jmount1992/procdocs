#!/usr/bin/env python3

from pathlib import Path
import yaml

from procdocs.core.config import load_config
from procdocs.core.utils import find_schema_path
from procdocs.core.schema.document_schema import DocumentSchema
from procdocs.core.document.document import Document

SUPPORTED_EXTENSIONS = {'.yml', '.yaml'}


def find_all_files(paths, recursive=False):
    files = []
    for path in paths:
        p = Path(path)
        if p.is_file() and p.suffix in SUPPORTED_EXTENSIONS:
            files.append(p)
        elif p.is_dir():
            iterator = p.rglob("*") if recursive else p.glob("*")
            files.extend(f for f in iterator if f.suffix in SUPPORTED_EXTENSIONS)
    return files


def validate_document(file_path, schema_paths):
    with open(file_path, "r") as f:
        doc = yaml.safe_load(f)

    if not doc or "metadata" not in doc or "document_type" not in doc["metadata"]:
        return False, f"Missing metadata.document_type in {file_path}"

    schema_name = doc["metadata"]["document_type"]
    schema_file = find_schema_path(schema_name, schema_paths)
    if not schema_file:
        return False, f"No schema found for document_type '{schema_name}'"

    schema = DocumentSchema.from_file(schema_file)
    document = Document.from_file(file_path, schema)
    errors = document.validate()
    if errors:
        return False, f"Validation errors in {file_path}", errors
    return True, f"{file_path} is valid", []


def main(args):
    config = load_config()
    schema_paths = config.get("schema_paths", [])
    files = find_all_files(args.files, recursive=args.recursive)
    if not files:
        print("No YAML files found.")
        return 1

    success_count = 0
    for file in files:
        valid, message, errors = validate_document(file, schema_paths)
        if args.verbose or not valid:
            print(f"{message}. Errors")
            for error in errors:
                print(f"  + {error}")
        if valid:
            success_count += 1

    print(f"\nValidation complete: {success_count}/{len(files)} passed.")
    return 0 if success_count == len(files) else 1


def register(subparser):
    parser = subparser.add_parser("validate", help="Validate a YAML document against its schema.")
    parser.add_argument("files", nargs="+", help="Files or directories to validate.")
    parser.add_argument("--recursive", "-r", action="store_true", help="Recursively scan directories.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all results, not only errors.")
    parser.set_defaults(func=main)
