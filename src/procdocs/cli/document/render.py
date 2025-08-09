#!/usr/bin/env python3

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from procdocs.core.schema.document_schema import DocumentSchema
from procdocs.core.document.document import Document


def extract_schema_metadata(template_path: Path) -> dict:
    with template_path.open("r") as f:
        for line in f:
            if line.startswith("{# PROCDOCS_METADATA"):
                content = line.strip().strip("{# PROCDOCS_METADATA").strip("#}")
                return dict(item.strip().split(": ") for item in content.split(","))
    return {}


def main(args):
    try:
        # Load schema
        schema = DocumentSchema.from_file(args.schema_path)

        # Load document
        document = Document.from_file(args.doc_path, schema)

        # Validate
        errors = document.validate()
        if errors:
            print("Validation failed:")
            for err in errors:
                print(f"  - {err}")
            return 1

        # Render with Jinja2
        template_path = Path(args.template_path)
        template_metadata = extract_schema_metadata(template_path)
        print(template_metadata)

        env = Environment(loader=FileSystemLoader(template_path.parent))
        template = env.get_template(template_path.name)

        html = template.render(
            metadata=document.metadata.to_dict(),
            contents=document._contents,
        )

        # Output PDF
        output_path = Path(args.output_path)
        HTML(string=html).write_pdf(str(output_path))
        print(f"PDF rendered successfully: {output_path}")
        return 0

    except Exception as e:
        print(f"Error rendering document:\n  {e}")
        return 1


def register(subparser):
    parser = subparser.add_parser("render", help="Render a document instance to PDF using a Jinja2 template.")
    parser.add_argument("doc_path", help="Path to the document YAML instance.")
    parser.add_argument("schema_path", help="Path to the JSON schema.")
    parser.add_argument("template_path", help="Path to the Jinja2 HTML template.")
    parser.add_argument("output_path", help="Path to save the rendered PDF.")
    parser.set_defaults(func=main)
