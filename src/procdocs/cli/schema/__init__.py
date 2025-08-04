#!/usr/bin/env python3

import argparse
from procdocs.cli.schema.tools import list_schemas, show_schema, validate_schema


def register(subparser: argparse._SubParsersAction):
    """
    Register all schema-related subcommands:
      - procdocs schema list
      - procdocs schema show
      - procdocs schema validate
    """
    schema_parser = subparser.add_parser("schema", help="Schema management commands")
    schema_subparsers = schema_parser.add_subparsers(dest="schema_cmd")

    # Add default function to print help if no document subcommand provided
    def document_default(args):
        schema_parser.print_help()
        return 1
    schema_parser.set_defaults(func=document_default)

    # schema list
    list_parser = schema_subparsers.add_parser("list", help="List available schemas")
    list_parser.set_defaults(func=list_schemas)

    # schema validate <schema>
    validate_parser = schema_subparsers.add_parser("validate", help="Validate a schema by name or path")
    validate_parser.add_argument("schema", help="Schema name (no .json) or path to schema file")
    validate_parser.set_defaults(func=validate_schema)

    # schema show <schema>
    show_parser = schema_subparsers.add_parser("show", help="Pretty-print schema contents")
    show_parser.add_argument("schema", help="Schema name (no .json) or path to schema file")
    show_parser.set_defaults(func=show_schema)
