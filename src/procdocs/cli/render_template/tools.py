#!/usr/bin/env python3

import json
from pathlib import Path

from procdocs.core.config import load_config
from procdocs.core.schema.schema import DocumentSchema
from procdocs.core.utils import find_schema_path


def list_render_templates(args) -> int:
    """List all available document render templates from configured paths."""
    config = load_config()
    template_paths = config.get("render_template_paths", [])
    found = []

    for path in template_paths:
        found.extend((Path(path) / f).resolve() for f in Path(path).glob("*.html.j2"))

    if not found:
        print("No templates found in configured paths.")
        return 1

    print("Available Document Render Templates:")
    for f in sorted(found):
        print(f"  - {Path(f.stem).stem}")
    return 0
