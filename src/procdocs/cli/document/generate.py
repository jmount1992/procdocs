#!/usr/bin/env python3

from pathlib import Path

from procdocs.core.app_context import AppContext
from procdocs.core.schema.document_schema import DocumentSchema
from procdocs.core.document_template_scaffold import write_yaml_template


def generate(args, ctx: AppContext) -> int:
    """
    Generate a YAML document template from a loaded schema (by name) or from a direct file path.
    """
    target = args.schema

    # 1) Try registry by name (valid schemas only)
    try:
        schema = ctx.schemas.require(target)
    except Exception:
        # 2) Try interpreting target as a path (works for invalid/unregistered-but-parseable files)
        p = Path(target)
        if p.exists():
            try:
                schema = DocumentSchema.from_file(p)
            except Exception as e:
                print(f"Schema file invalid: {p}\n{e}")
                return 1
        else:
            print(f"Schema '{target}' not found by name or path.")
            return 1

    # 3) Write the YAML template
    output_path = Path(args.output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        write_yaml_template(schema, output_path)
        print(f"Template generated at {output_path}")
        return 0
    except Exception as e:
        print(f"Error generating template:\n  {e}")
        return 1


def register(subparser):
    parser = subparser.add_parser(
        "generate",
        help="Generate YAML document template from a JSON schema."
    )
    parser.add_argument("schema", help="Schema name (preferred) or path to a schema file.")
    parser.add_argument("output_path", help="Path to save the generated YAML document.")
    parser.set_defaults(func=generate)
