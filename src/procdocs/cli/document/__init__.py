# #!/usr/bin/env python3

# import argparse
# from . import generate, validate, render


# def register(subparser: argparse._SubParsersAction):
#     """
#     Register all document-related subcommands:
#       - procdocs document validate
#       - procdocs document template
#       - procdocs document render
#     """
#     doc_parser = subparser.add_parser("document", help="Document instance commands")
#     doc_subparsers = doc_parser.add_subparsers(dest="document_cmd")

#     # Add default function to print help if no document subcommand provided
#     def document_default(args):
#         doc_parser.print_help()
#         return 1
#     doc_parser.set_defaults(func=document_default)

#     # Register document subcommands
#     validate.register(doc_subparsers)
#     generate.register(doc_subparsers)
#     render.register(doc_subparsers)
