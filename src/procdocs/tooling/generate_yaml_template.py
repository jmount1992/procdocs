#!/usr/bin/env python3
"""
YAML Template Generator from Meta-Schema

This module generates example YAML document templates from a validated JSON meta-schema.
Each template shows the required structure, placeholder values, and inline comments
to guide users in filling out schema-compliant documents. List fields automatically
show two example entries, with contextual comments to aid correct duplication.

Intended usage:
    - Generate editable templates for work instructions, test cases, or other schema-defined documents.
    - Aid human users in writing valid YAML by example, including structure, indentation, and comments.

Typical entry point:
    generate_yaml_template(meta_schema, filepath)
"""

from typing import List, Optional, Set
from pathlib import Path

from procdocs.core.schema.schema import DocumentSchema
from procdocs.core.schema.field_descriptor import FieldDescriptor


def generate_yaml_template(meta_schema: DocumentSchema, filepath: Path) -> None:
    """
    Generate a YAML template from a DocumentSchema and write it to disk.

    Args:
        meta_schema: The DocumentSchema instance describing the document structure.
        filepath: The output path for the generated YAML template.

    This will write a YAML file with placeholder values, comments, and example
    structures, including two entries for each list-type field.
    """
    lines = []
    lines.append("metadata:")
    lines.append(f"  document_type: {meta_schema.metadata.schema_name}")
    lines.append("  document_version: 0.0.0")
    lines.append(f"  format_version: {meta_schema.metadata.format_version}")
    lines.append("")
    lines.append("contents:")
    for fd in meta_schema.structure.values():
        lines.extend(_render_field_descriptor_lines(fd, indent=2))
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        f.write("---\n")
        f.write("\n".join(lines))


def _build_comment(fd: FieldDescriptor) -> Optional[str]:
    """
    Construct an inline comment string for a field, based on metadata.

    Args:
        fd: The FieldDescriptor for the field.

    Returns:
        A formatted comment string with description, default, options, etc.,
        or None if no comment is applicable.
    """
    parts = []
    if not fd.required:
        parts.append("optional")
    if fd.description:
        parts.append(fd.description)
    if fd.default is not None:
        parts.append(f"Default value = {fd.default!r}")
    if fd.fieldtype == "enum" and fd.options:
        parts.append(f"Options: {', '.join(map(str, fd.options))}")
    return ". ".join(parts) if parts else None


def _get_prefix_and_indent(indent: int, is_first_line: bool, in_list: bool) -> tuple[str, int]:
    """
    Determine YAML prefix and next indentation level for a field line.

    Args:
        indent: The current indentation level.
        is_first_line: Whether this is the first line in a list item.
        in_list: Whether this field appears within a list.

    Returns:
        A tuple of (line prefix string, indent level for children).
    """
    if is_first_line:
        prefix = " " * indent + "- "
        child_indent = indent + 2
    elif in_list:
        prefix = " " * (indent + 2)
        child_indent = indent + 4
    else:
        prefix = " " * indent
        child_indent = indent + 2
    return prefix, child_indent


def _render_scalar_field(fd: FieldDescriptor, prefix: str) -> str:
    """
    Render a single scalar field (no children) as a YAML line.

    Args:
        fd: The FieldDescriptor for the scalar field.
        prefix: The YAML line prefix (including indentation and optional '- ').

    Returns:
        A single YAML-formatted line with a placeholder value and comment.
    """
    value = "<required>" if fd.required else "<optional>"
    comment = _build_comment(fd) or ("Required" if fd.required else "Optional")
    return f"{prefix}{fd.fieldname}: {value}  # {comment}"


def _render_field_descriptor_lines(
    fd: FieldDescriptor,
    indent: int = 0,
    is_first_line: bool = False,
    in_list: bool = False,
    already_commented_lists: Optional[Set[str]] = None,
) -> List[str]:
    """
    Recursively render a field and its children into YAML-formatted lines.

    Args:
        fd: The FieldDescriptor to render.
        indent: The base indentation level for this field.
        is_first_line: Whether this line starts a list item (adds '-').
        in_list: Whether this field appears inside a list.
        already_commented_lists: Set of UID strings for which the list example comment
                                 has already been rendered (to avoid duplicates).

    Returns:
        A list of strings representing YAML lines for this field.
    """
    if already_commented_lists is None:
        already_commented_lists = set()

    lines = []
    prefix, child_indent = _get_prefix_and_indent(indent, is_first_line, in_list)
    comment = _build_comment(fd) or ("Required" if fd.required else "Optional")

    if not fd.fields:
        lines.append(_render_scalar_field(fd, prefix))
        return lines

    # Render container field
    if indent == 2:
        lines.append(f"\n# {fd.fieldname.replace('-', ' ').title()} - {comment}")
        lines.append(f"{prefix}{fd.fieldname}:")
    else:
        lines.append(f"{prefix}{fd.fieldname}:  # {comment}")

    # Recurse into children
    if fd.is_list():
        if fd.uid not in already_commented_lists:
            lines.append(
                f"{' ' * child_indent}"
                f"# Example list: '{fd.fieldname}' can contain one or more entries. Two shown below."
            )
            already_commented_lists.add(fd.uid)

        for _ in range(2):  # render 2 example entries
            for idx, child in enumerate(fd.fields):
                lines.extend(_render_field_descriptor_lines(
                    child,
                    indent=child_indent,
                    is_first_line=(idx == 0),
                    in_list=True,
                    already_commented_lists=already_commented_lists,
                ))
    else:
        for child in fd.fields:
            lines.extend(_render_field_descriptor_lines(
                child,
                indent=child_indent,
                is_first_line=False,
                in_list=False,
                already_commented_lists=already_commented_lists,
            ))

    return lines
