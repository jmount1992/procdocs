#!/usr/bin/env python3

import argparse
from procdocs.core.app import get_context
from procdocs.cli import config, schema, render_template
from procdocs.cli.document import generate, validate, render

def main():
    parser = argparse.ArgumentParser(prog="procdocs", description="ProcDocs CLI Toolkit")
    # optional global flags you can add later:
    # parser.add_argument("--schema-path", action="append", help="Extra schema roots")
    subparsers = parser.add_subparsers(dest="command")

    # Register subcommands (they should accept ctx)
    generate.register(subparsers)
    validate.register(subparsers)
    render.register(subparsers)
    schema.register(subparsers)
    render_template.register(subparsers)
    config.register(subparsers)

    args = parser.parse_args()
    if hasattr(args, "func"):
        ctx = get_context()  # built once
        exit(args.func(args, ctx))
    parser.print_help()
    exit(1)

if __name__ == "__main__":
    main()
