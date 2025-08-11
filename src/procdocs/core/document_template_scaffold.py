#!/usr/bin/env python3

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
        lines.extend(
            _render_field(
                fd,
                indent=2,
                list_examples=list_examples,
                seen_list_uids=seen_list_uids,
            )
        )

    lines.append("")  # trailing newline
    return "\n".join(lines)


# --- Internal Helpers --- #

def _render_field(
    fd: FieldDescriptor,
    *,
    indent: int,
    list_examples: int,
    is_first_line: bool = False,
    in_list: bool = False,
    seen_list_uids: Optional[Set[str]] = None,
) -> List[str]:
    """
    Render one FieldDescriptor into YAML template lines.

    - Scalars: inline placeholder `<required>` / `<optional>`
    - Dicts: nested keys
    - Lists:
        * list of dicts -> N example items with nested fields
        * list of scalars -> N example `- <placeholder>` entries
    """
    if seen_list_uids is None:
        seen_list_uids = set()

    prefix, child_indent = _prefix(indent, is_first_line, in_list)
    comment = _comment(fd) or ("Required" if fd.required else "Optional")
    lines: List[str] = []

    # Containers vs scalars
    is_dict = fd.fieldtype == FieldType.DICT
    is_list = fd.fieldtype == FieldType.LIST

    if not is_dict and not is_list:
        # Scalar
        placeholder = "<required>" if fd.required else "<optional>"
        lines.append(f"{prefix}{fd.fieldname}: {placeholder}  # {comment}")
        return lines

    # Container header
    if indent == 2:
        lines.append(f"\n  # {fd.fieldname.replace('-', ' ').title()} - {comment}")
        lines.append(f"{prefix}{fd.fieldname}:")
    else:
        lines.append(f"{prefix}{fd.fieldname}:  # {comment}")

    if is_dict:
        # Dict: render nested children
        for child in _dict_fields(fd):
            lines.extend(
                _render_field(
                    child,
                    indent=child_indent,
                    list_examples=list_examples,
                    is_first_line=False,
                    in_list=False,
                    seen_list_uids=seen_list_uids,
                )
            )
        return lines

    # List
    if fd.uid not in seen_list_uids:
        lines.append(" " * child_indent + f"# Example list: '{fd.fieldname}' shows {max(1, list_examples)} items.")
        seen_list_uids.add(fd.uid)

    item_fd = _list_item(fd)

    if item_fd.fieldtype == FieldType.DICT:
        # list of dicts -> render each example item with child fields
        children = _dict_fields(item_fd)
        for _ in range(max(1, list_examples)):
            for idx, child in enumerate(children):
                lines.extend(
                    _render_field(
                        child,
                        indent=child_indent,
                        list_examples=list_examples,
                        is_first_line=(idx == 0),
                        in_list=True,
                        seen_list_uids=seen_list_uids,
                    )
                )
    else:
        # list of scalars -> render `- <placeholder>` entries
        placeholder = "<required>" if item_fd.required else "<optional>"
        for i in range(max(1, list_examples)):
            lines.append(" " * child_indent + f"- {placeholder}")

    return lines


def _prefix(indent: int, is_first_line: bool, in_list: bool) -> tuple[str, int]:
    """
    Compute the YAML prefix and the next child indent.

    - If this is the first line of a list item, prefix is "- " at current indent.
    - If inside a list but not first line, indent shifts to align fields under the bullet.
    - Otherwise, normal key indentation.
    """
    if is_first_line:
        return " " * indent + "- ", indent + 2
    if in_list:
        return " " * (indent + 2), indent + 4
    return " " * indent, indent + 2


def _comment(fd: FieldDescriptor) -> str | None:
    """
    Build a compact inline comment string from descriptor metadata and spec.
    Includes: optionality, description, default, string pattern, enum options.
    """
    parts: List[str] = []
    if not fd.required:
        parts.append("optional")
    if fd.description:
        parts.append(fd.description)
    if fd.default is not None:
        parts.append(f"Default = {fd.default!r}")

    # string pattern
    if fd.fieldtype == FieldType.STRING:
        pat = _string_pattern(fd)
        if pat:
            parts.append(f"Pattern: {pat}")

    # enum options
    if fd.fieldtype == FieldType.ENUM:
        opts = _enum_options(fd)
        if opts:
            parts.append(f"Options: {', '.join(map(str, opts))}")

    return ". ".join(parts) if parts else None


# ---- spec accessors ---------------------------------------------------------

def _dict_fields(fd: FieldDescriptor) -> List[FieldDescriptor]:
    # fd is fieldtype == dict
    spec = getattr(fd, "spec", None)
    return list(getattr(spec, "fields", []) or [])


def _list_item(fd: FieldDescriptor) -> FieldDescriptor:
    # fd is fieldtype == list
    spec = getattr(fd, "spec", None)
    return getattr(spec, "item")  # canonical, always present after packing


def _string_pattern(fd: FieldDescriptor) -> str | None:
    spec = getattr(fd, "spec", None)
    return getattr(spec, "pattern", None) if spec and fd.fieldtype == FieldType.STRING else None


def _enum_options(fd: FieldDescriptor) -> List[str]:
    spec = getattr(fd, "spec", None)
    if spec and fd.fieldtype == FieldType.ENUM:
        return list(getattr(spec, "options", []) or [])
    return []
