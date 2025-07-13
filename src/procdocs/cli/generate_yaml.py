#!/usr/bin/env python3

from typing import List, Optional
from pathlib import Path

from procdocs.core.meta_schema import MetaSchema
from procdocs.core.field_descriptor import FieldDescriptor


def _build_comment(fd: FieldDescriptor) -> Optional[str]:
    parts = []
    if not fd.required:
        parts.append("optional")
    if fd.description:
        parts.append(fd.description)
    if fd.default is not None:
        parts.append(f"Default value = {fd.default!r}")
    if fd.fieldtype == "enum" and fd.enum:
        parts.append(f"Options: {', '.join(map(str, fd.enum))}")

    return ". ".join(parts) if parts else None


def _render_field_descriptor_lines(
    fd: FieldDescriptor,
    indent: int = 0
) -> List[str]:
    lines = []
    prefix = " " * indent
    comment = _build_comment(fd) or ("Required" if fd.required else "Optional")

    if not fd.fields:
        value = "<required>" if fd.required else "<optional>"
        line = f"{prefix}{fd.fieldname}: {value}  # {comment}"
        lines.append(line)
        return lines

    if indent == 0:
        lines.append(f"\n# {fd.fieldname.replace('-', ' ').title()} - {comment}")
        lines.append(f"{prefix}{fd.fieldname}:")
    else:
        lines.append(f"{prefix}{fd.fieldname}:  # {comment}")

    next_indent = indent + 2
    for child in fd.fields:
        child_lines = _render_field_descriptor_lines(
            child,
            indent=next_indent
        )
        lines.extend(child_lines)

    return lines


def generate_yaml_template(meta_schema: MetaSchema, filepath: Path) -> None:
    lines = []
    for fd in meta_schema.structure.values():
        lines.extend(_render_field_descriptor_lines(fd))

    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        f.write("---\n")
        f.write("\n".join(lines))
