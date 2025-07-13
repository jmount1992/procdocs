#!/usr/bin/env python3

import argparse
from procdocs.cli import template, validate, render


def main():
    parser = argparse.ArgumentParser(prog="procdocs", description="ProcDocs CLI Toolkit")
    subparsers = parser.add_subparsers(dest="command")

    # Register subcommands
    template.register(subparsers)
    validate.register(subparsers)
    render.register(subparsers)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        exit_code = args.func(args)
        exit(exit_code)
    else:
        parser.print_help()
