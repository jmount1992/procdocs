# procdocs/tooling/template.py
from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Set

from procdocs.core.constants import DEFAULT_TEXT_ENCODING
from procdocs.core.schema.document_schema import DocumentSchema
from procdocs.core.schema.field_descriptor import FieldDescriptor
from procdocs.core.schema.field_type import FieldType


def write_yaml_template(schema: DocumentSchema, path: Path, *, list_examples: int = 2) -> None:
    path = Path(path)
    text = render_yaml_template(schema, list_examples=list_examples)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=DEFAULT_TEXT_ENCODING)


def render_yaml_template(schema: DocumentSchema, *, list_examples: int = 2) -> str:
    lines: List[str] = []
    lines.append("---")
    lines.append("metadata:")
    lines.append(f"  document_type: {schema.schema_name}")
    lines.append("  document_version: 0.0.0")
    lines.append(f"  format_version: {schema.format_version}")
    lines.append("")
    lines.append("contents:")

    seen_list_uids: Set[str] = set()
    for fd in schema.structure:
        lines.extend(_render_field(fd, indent=2, list_examples=list_examples, seen_list_uids=seen_list_uids))

    lines.append("")  # trailing newline
    return "\n".join(lines)


# --- Internal Helpers --- #

def _render_field(fd: FieldDescriptor, *, indent: int, list_examples: int,
                  is_first_line: bool = False, in_list: bool = False,
                  seen_list_uids: Optional[Set[str]] = None) -> List[str]:
    if seen_list_uids is None:
        seen_list_uids = set()

    prefix, child_indent = _prefix(indent, is_first_line, in_list)
    comment = _comment(fd) or ("Required" if fd.required else "Optional")
    lines: List[str] = []

    # scalar
    if not fd.fields:
        placeholder = "<required>" if fd.required else "<optional>"
        lines.append(f"{prefix}{fd.fieldname}: {placeholder}  # {comment}")
        return lines

    # container
    if indent == 2:
        lines.append(f"\n# {fd.fieldname.replace('-', ' ').title()} - {comment}")
        lines.append(f"{prefix}{fd.fieldname}:")
    else:
        lines.append(f"{prefix}{fd.fieldname}:  # {comment}")

    if fd.fieldtype == FieldType.LIST:
        if fd.uid not in seen_list_uids:
            lines.append(" " * child_indent + f"# Example list: '{fd.fieldname}' shows {list_examples} items.")
            seen_list_uids.add(fd.uid)
        # render N example items
        for _ in range(max(1, list_examples)):
            for idx, child in enumerate(fd.fields or []):
                lines.extend(_render_field(child, indent=child_indent, list_examples=list_examples,
                                           is_first_line=(idx == 0), in_list=True, seen_list_uids=seen_list_uids))
    else:  # DICT
        for child in fd.fields or []:
            lines.extend(_render_field(child, indent=child_indent, list_examples=list_examples,
                                       is_first_line=False, in_list=False, seen_list_uids=seen_list_uids))
    return lines


def _prefix(indent: int, is_first_line: bool, in_list: bool) -> tuple[str, int]:
    if is_first_line:
        return " " * indent + "- ", indent + 2
    if in_list:
        return " " * (indent + 2), indent + 4
    return " " * indent, indent + 2


def _comment(fd: FieldDescriptor) -> str | None:
    parts: List[str] = []
    if not fd.required:
        parts.append("optional")
    if fd.description:
        parts.append(fd.description)
    if fd.default is not None:
        parts.append(f"Default = {fd.default!r}")
    if fd.pattern:
        parts.append(f"Pattern: {fd.pattern}")
    if fd.fieldtype == FieldType.ENUM and fd.options:
        parts.append(f"Options: {', '.join(map(str, fd.options))}")
    return ". ".join(parts) if parts else None
