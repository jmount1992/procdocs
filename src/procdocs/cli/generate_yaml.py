from typing import List, Optional
from pathlib import Path
from procdocs.engine.meta_schema import MetaSchema
from procdocs.engine.field_descriptor import FieldDescriptor


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
        line = f"{prefix}{fd.field}: {value}  # {comment}"
        lines.append(line)
        return lines

    lines.append(f"{prefix}{fd.field}:  # {comment}")

    next_indent = indent + 2
    for idx, child in enumerate(fd.fields):
        is_first = (idx == 0 and fd.fieldtype == "list")
        child_lines = _render_field_descriptor_lines(
            child,
            indent=next_indent,
            is_list_item=is_first
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
