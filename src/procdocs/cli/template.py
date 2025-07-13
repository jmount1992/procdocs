import argparse

from procdocs.core.schema.schema import DocumentSchema
from procdocs.tooling.generate_yaml_template import generate_yaml_template


def main(args):
    try:
        meta_schema = DocumentSchema.from_file(args.schema_path)
        generate_yaml_template(meta_schema, args.output_path)
        print(f"Template generated at {args.output_path}")
        return 0

    except Exception as e:
        print(f"Error generating template:\n  {e}")
        return 1


def register(subparser: argparse._SubParsersAction):
    parser = subparser.add_parser("template", help="Generate YAML template from a JSON meta-schema.")
    parser.add_argument("schema_path", help="Path to the JSON meta-schema file.")
    parser.add_argument("output_path", help="Path to save the generated YAML document-schema.")
    parser.set_defaults(func=main)
