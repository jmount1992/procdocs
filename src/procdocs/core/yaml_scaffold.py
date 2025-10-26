#!/usr/bin/env python3
"""
Purpose:
    Generates YAML scaffold templates from a DocumentSchema, providing
    functions to render the template as a string or write it to disk with
    example placeholders.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from procdocs.core.constants import DEFAULT_TEXT_ENCODING
from procdocs.core.schema.document_schema import DocumentSchema
from procdocs.core.schema.field_descriptor import FieldDescriptor
from procdocs.core.schema.field_type import FieldType


# --- Public API --- #

def write_yaml_template(schema: DocumentSchema, path: Path, *, list_examples: int = 2) -> None:
    """Render and write a YAML scaffold for `schema` to `path`."""
    path = Path(path)
    text = render_yaml_template(schema, list_examples=list_examples)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=DEFAULT_TEXT_ENCODING)


def render_yaml_template(schema: DocumentSchema, *, list_examples: int = 2) -> str:
    """Return a YAML scaffold for a document that conforms to `schema`."""
    n = max(1, list_examples)

    lines: list[str] = []
    lines.append("---")
    lines.append("metadata:")
    lines.append(f"  document_type: {schema.schema_name}")
    lines.append("  document_version: 0.0.0")
    lines.append(f"  format_version: {schema.format_version}")
    lines.append("")
    lines.append("contents:")

    seen_list_uids: set[str] = set()
    for fd in schema.structure:
        lines.extend(
            _render_field(
                fd,
                indent=2,
                list_examples=n,
                seen_list_uids=seen_list_uids,
            )
        )

    lines.append("")  # trailing newline
    return "\n".join(lines)


# --- Internal Helpers --- #

def _is_dict(fd: FieldDescriptor) -> bool:
    return fd.fieldtype == FieldType.DICT


def _is_list(fd: FieldDescriptor) -> bool:
    return fd.fieldtype == FieldType.LIST


def _is_scalar(fd: FieldDescriptor) -> bool:
    return not _is_dict(fd) and not _is_list(fd)


def _render_scalar(fd: FieldDescriptor, prefix: str, comment: str) -> list[str]:
    placeholder = "<required>" if fd.required else "<optional>"
    return [f"{prefix}{fd.fieldname}: {placeholder}  # {comment}"]


def _render_container_header(fd: FieldDescriptor, prefix: str, indent: int, comment: str) -> list[str]:
    # Top-level containers get a section heading comment for readability
    if indent == 2:
        return [
            f"\n  # {fd.fieldname.replace('-', ' ').title()} - {comment}",
            f"{prefix}{fd.fieldname}:",
        ]
    return [f"{prefix}{fd.fieldname}:  # {comment}"]


def _render_dict_field(
    fd: FieldDescriptor,
    child_indent: int,
    list_examples: int,
    seen_list_uids: set[str],
) -> list[str]:
    out: list[str] = []
    for child in _dict_fields(fd):
        out.extend(
            _render_field(
                child,
                indent=child_indent,
                list_examples=list_examples,
                is_first_line=False,
                in_list=False,
                seen_list_uids=seen_list_uids,
            )
        )
    return out


def _render_list_of_dicts(
    item_fd: FieldDescriptor,
    child_indent: int,
    list_examples: int,
    seen_list_uids: set[str],
) -> list[str]:
    out: list[str] = []
    children = _dict_fields(item_fd)
    for _ in range(list_examples):
        for idx, child in enumerate(children):
            out.extend(
                _render_field(
                    child,
                    indent=child_indent,
                    list_examples=list_examples,
                    is_first_line=(idx == 0),
                    in_list=True,
                    seen_list_uids=seen_list_uids,
                )
            )
    return out


def _render_list_of_scalars(
    item_fd: FieldDescriptor,
    child_indent: int,
    list_examples: int,
) -> list[str]:
    placeholder = "<required>" if item_fd.required else "<optional>"
    return [" " * child_indent + f"- {placeholder}" for _ in range(list_examples)]


def _render_list_field(
    fd: FieldDescriptor,
    child_indent: int,
    list_examples: int,
    seen_list_uids: set[str],
) -> list[str]:
    out: list[str] = []
    # First-time list note
    if fd.uid not in seen_list_uids:
        out.append(" " * child_indent + f"# Example list: '{fd.fieldname}' shows {list_examples} items.")
        seen_list_uids.add(fd.uid)

    item_fd = _list_item(fd)
    if _is_dict(item_fd):
        out.extend(_render_list_of_dicts(item_fd, child_indent, list_examples, seen_list_uids))
    else:
        out.extend(_render_list_of_scalars(item_fd, child_indent, list_examples))
    return out


def _render_field(
    fd: FieldDescriptor,
    *,
    indent: int,
    list_examples: int,
    is_first_line: bool = False,
    in_list: bool = False,
    seen_list_uids: Optional[set[str]] = None,
) -> list[str]:
    """
    Render one `FieldDescriptor` into YAML template lines.

    - Scalars: inline placeholder `<required>` / `<optional>`
    - Dicts: nested keys under the field name
    - Lists:
        * of dicts   -> N example items, each rendering the child fields
        * of scalars -> N lines `- <placeholder>`
    """
    if seen_list_uids is None:
        seen_list_uids = set()

    prefix, child_indent = _prefix(indent, is_first_line, in_list)
    comment = _comment(fd) or ("Required" if fd.required else "Optional")

    # Scalar
    if _is_scalar(fd):
        return _render_scalar(fd, prefix, comment)

    # Container header
    lines: list[str] = []
    lines.extend(_render_container_header(fd, prefix, indent, comment))

    # Dict vs List body
    if _is_dict(fd):
        lines.extend(_render_dict_field(fd, child_indent, list_examples, seen_list_uids))
        return lines

    # List
    lines.extend(_render_list_field(fd, child_indent, list_examples, seen_list_uids))
    return lines


def _prefix(indent: int, is_first_line: bool, in_list: bool) -> tuple[str, int]:
    """
    Compute the YAML prefix and the next child indent.

    - First line of a list item: prefix is "- " at current indent; child indent +2.
    - Inside a list (non-first line): indent shifts by +2 to align under the bullet; child indent +4.
    - Otherwise: normal key indentation; child indent +2.
    """
    if is_first_line:
        return " " * indent + "- ", indent + 2
    if in_list:
        return " " * (indent + 2), indent + 4
    return " " * indent, indent + 2


def _add_if(parts: list[str], value: Optional[str]) -> None:
    """Append value to parts if value is truthy ('' and [] are ignored)."""
    if value:
        parts.append(value)


def _add_if_not_none(parts: list[str], value: object, fmt: str) -> None:
    """Append formatted value when it's not None (preserves 0/False)."""
    if value is not None:
        parts.append(fmt.format(value))


def _comment(fd: FieldDescriptor) -> str | None:
    """
    Build a compact inline comment from descriptor metadata/spec.
    Includes: optionality, description, default, string pattern, enum options.
    """
    parts: list[str] = []

    # Optionality & description
    _add_if(parts, "optional" if not fd.required else None)
    _add_if(parts, fd.description)

    # Default (only when explicitly set)
    _add_if_not_none(parts, fd.default, "Default = {!r}")

    # String pattern / Enum options
    _add_if(parts, (lambda p: f"Pattern: {p}" if p else None)(_string_pattern(fd)))
    opts = _enum_options(fd)
    _add_if(parts, f"Options: {', '.join(map(str, opts))}" if opts else None)

    return ". ".join(parts) if parts else None


# --- Spec accessors --- #

def _dict_fields(fd: FieldDescriptor) -> list[FieldDescriptor]:
    # fd.fieldtype == dict; avoid importing spec classes to keep deps light
    spec = getattr(fd, "spec", None)
    return list(getattr(spec, "fields", []) or [])


def _list_item(fd: FieldDescriptor) -> FieldDescriptor:
    # fd.fieldtype == list; canonical after packing
    spec = getattr(fd, "spec", None)
    return getattr(spec, "item")


def _string_pattern(fd: FieldDescriptor) -> str | None:
    spec = getattr(fd, "spec", None)
    return getattr(spec, "pattern", None) if spec and fd.fieldtype == FieldType.STRING else None


def _enum_options(fd: FieldDescriptor) -> list[str]:
    spec = getattr(fd, "spec", None)
    if spec and fd.fieldtype == FieldType.ENUM:
        return list(getattr(spec, "options", []) or [])
    return []
