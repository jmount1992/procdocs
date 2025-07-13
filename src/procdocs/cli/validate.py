#!/usr/bin/env python3

import os
import argparse
from pathlib import Path


# from procdocs.core.loader import load_yaml_file, load_json_file
from procdocs.core.document_schema import DocumentSchema


SUPPORTED_EXTENSIONS = {'.yml', '.yaml', '.json'}


def find_all_files(paths, recursive=False):
    all_files = []
    for path in paths:
        path = Path(path)
        if path.is_file() and path.suffix in SUPPORTED_EXTENSIONS:
            all_files.append(path)
        elif path.is_dir():
            if recursive:
                for root, _, files in os.walk(path):
                    for f in files:
                        if Path(f).suffix in SUPPORTED_EXTENSIONS:
                            all_files.append(Path(root) / f)
            else:
                for f in path.glob('*'):
                    if f.suffix in SUPPORTED_EXTENSIONS:
                        all_files.append(f)
    return all_files


def validate_file(file_path):
    suffix = file_path.suffix
    try:
        if suffix == '.json':
            # Validate as meta-schema
            schema = DocumentSchema.from_file(file_path, strict=False)
            schema.validate()
            return True, f"Valid meta-schema: {file_path}"

        elif suffix in {'.yml', '.yaml'}:
            # doc = load_yaml_file(file_path)
            # if 'metadata' not in doc or 'filetype' not in doc['metadata']:
            #     return False, f"✗ Missing metadata.filetype in {file_path}"
            # filetype = doc['metadata']['filetype']
            # schema_path = Path('schemas') / f"{filetype}.json"
            # if not schema_path.exists():
            #     return False, f"✗ No matching schema found for filetype '{filetype}'"
            # schema = MetaSchema.from_dict(load_json_file(schema_path))
            # schema.validate_document(doc)
            return True, f"Valid document (TO BE IMPLEMENTED): {file_path}"

        else:
            return False, f"Unsupported file extension: {file_path}"

    except Exception as e:
        return False, f"Validation error in {file_path}:\n  {e}"


def main(args):
    file_paths = find_all_files(args.files, recursive=args.recursive)
    if not file_paths:
        print("No valid files found.")
        return 1

    success_count = 0
    for file_path in file_paths:
        valid, message = validate_file(file_path)
        if args.verbose or not valid:
            print(message)
        if valid:
            success_count += 1

    print(f"\nValidation complete: {success_count}/{len(file_paths)} passed.")
    return 0 if success_count == len(file_paths) else 1


def register(subparser: argparse._SubParsersAction):
    parser = subparser.add_parser("validate", help="Validate YAML or JSON files against schema.")
    parser.add_argument("files", nargs="+", help="Files or directories to validate.")
    parser.add_argument("--recursive", "-r", action="store_true", help="Recursively scan directories.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show results for all files.")
    parser.set_defaults(func=main)
