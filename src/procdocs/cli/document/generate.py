#!/usr/bin/env python3

from procdocs.core.schema.schema import DocumentSchema
from procdocs.core.config import load_config
from procdocs.core.utils import find_schema_path
from procdocs.tooling.generate_yaml_template import generate_yaml_template


def main(args):
    config = load_config()
    schema_paths = config.get("schema_paths", [])
    schema_path = find_schema_path(args.schema, schema_paths)
    if not schema_path:
        print(f"Schema '{args.schema}' not found in configured paths.")
        return 1

    try:
        meta_schema = DocumentSchema.from_file(schema_path)
        generate_yaml_template(meta_schema, args.output_path)
        print(f"Template generated at {args.output_path}")
        return 0
    except Exception as e:
        print(f"Error generating template:\n  {e}")
        return 1


def register(subparser):
    parser = subparser.add_parser("generate", help="Generate YAML document template from a JSON schema.")
    parser.add_argument("schema", help="The schema name or path.")
    parser.add_argument("output_path", help="Path to save the generated YAML document.")
    parser.set_defaults(func=main)
