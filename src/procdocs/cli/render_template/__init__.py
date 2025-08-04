#!/usr/bin/env python3

import argparse
from procdocs.cli.render_template.tools import list_render_templates


def register(subparser: argparse._SubParsersAction):
    """
    Register all render-template related subcommands:
      - procdocs render-template list
      - procdocs render-template show
      - procdocs render-template generate
    """
    render_template_parser = subparser.add_parser("render-template", help="Render-template management commands")
    render_template_subparsers = render_template_parser.add_subparsers(dest="render_template_cmd")

    # Add default function to print help if no document subcommand provided
    def render_template_default(args):
        render_template_parser.print_help()
        return 1
    render_template_parser.set_defaults(func=render_template_default)

    # schema list
    list_parser = render_template_subparsers.add_parser("list", help="List available render-templates")
    list_parser.set_defaults(func=list_render_templates)

    # # schema validate <schema>
    # validate_parser = render_template_subparsers.add_parser("validate", help="Validate a schema by name or path")
    # validate_parser.add_argument("schema", help="Schema name (no .json) or path to schema file")
    # validate_parser.set_defaults(func=validate_schema)

    # # schema show <schema>
    # show_parser = render_template_subparsers.add_parser("generate", help="Pretty-print schema contents")
    # show_parser.add_argument("schema", help="Schema name (no .json) or path to schema file")
    # show_parser.set_defaults(func=show_schema)
