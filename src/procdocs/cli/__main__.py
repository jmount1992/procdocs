#!/usr/bin/env python3

import argparse

from procdocs.cli import document, schema


def main():
    parser = argparse.ArgumentParser(prog="procdocs", description="ProcDocs CLI Toolkit")
    subparsers = parser.add_subparsers(dest="command")

    # Register high-level command groups
    schema.register(subparsers)
    document.register(subparsers)

    args = parser.parse_args()
    if hasattr(args, "func"):
        exit_code = args.func(args)
        exit(exit_code)
    else:
        parser.print_help()
        exit(1)


if __name__ == "__main__":
    main()
