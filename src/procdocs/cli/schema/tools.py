#!/usr/bin/env python3

import json
from pathlib import Path

from procdocs.core.config import load_config
from procdocs.core.schema.schema import DocumentSchema
from procdocs.core.utils import find_schema_path


def list_schemas(args) -> int:
    """List all available document schemas from configured paths."""
    config = load_config()
    schema_paths = config.get("schema_paths", [])
    found = []

    for path in schema_paths:
        found.extend((Path(path) / f).resolve() 
                     for f in Path(path).glob("*.json"))

    if not found:
        print("No schemas found in configured paths.")
        return 1

    print("Available Document Schemas:")
    for f in sorted(found):
        print(f"  - {f.stem}")
    return 0


def validate_schema(args) -> int:
    """Validate that a schema file is syntactically and structurally correct."""
    config = load_config()
    schema_paths = config.get("schema_paths", [])
    schema_file = find_schema_path(args.schema, schema_paths)

    if schema_file is None:
        print(f"Schema '{args.schema}' not found in configured paths or as a file path.")
        return 1

    try:
        schema = DocumentSchema.from_file(schema_file, strict=False)
        results = schema.validate(strict=False)
        if len(results.errors) == 0:
            print(f"Valid schema: {schema_file}")
            return 0
        print("Schema validation failed. Schema errors:")
        for error in results.errors:
            print(f"  + {error}")
        return 1
    except Exception as e:
        print(f"Error loading schema: {e}")
        return 1


def show_schema(args) -> int:
    """Pretty-print the schema JSON."""
    config = load_config()
    schema_paths = config.get("schema_paths", [])
    schema_file = find_schema_path(args.schema, schema_paths)

    if schema_file is None:
        print(f"Schema '{args.schema}' not found in configured paths or as a file path.")
        return 1

    with open(schema_file, "r", encoding="utf-8") as f:
        content = json.load(f)

    print(json.dumps(content, indent=2))
    return 0
