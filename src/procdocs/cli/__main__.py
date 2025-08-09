#!/usr/bin/env python3

import argparse

from procdocs.cli import schema, render_template
from procdocs.cli.document import generate, validate, render


def main():
    parser = argparse.ArgumentParser(prog="procdocs", description="ProcDocs CLI Toolkit")
    subparsers = parser.add_subparsers(dest="command")

    # Register high-level command groups
    # Register main document functions
    # generate.register(subparsers)
    # validate.register(subparsers)
    # render.register(subparsers)

    # Register schema and render template sub-commands
    schema.register(subparsers)
    # render_template.register(subparsers)

    args = parser.parse_args()
    if hasattr(args, "func"):
        exit_code = args.func(args)
        exit(exit_code)
    else:
        parser.print_help()
        exit(1)


if __name__ == "__main__":
    main()
