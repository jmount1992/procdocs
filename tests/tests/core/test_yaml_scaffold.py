#!/usr/bin/env python3
from pathlib import Path

from procdocs.core.constants import DEFAULT_TEXT_ENCODING
from procdocs.core.schema.document_schema import DocumentSchema
from procdocs.core.schema.field_descriptor import FieldDescriptor
from procdocs.core.yaml_scaffold import (
    render_yaml_template,
    write_yaml_template,
    _render_field,          # internal, used to hit the seen_list_uids=None init
    _string_pattern,        # internal, used to cover non-string path
)


def _schema():
    """
    Build a schema that hits:
      - string (with and without pattern, with description)
      - enum (optional + default + options in comment)
      - dict (top-level container header)
      - list of dicts (example block + bullet formatting)
      - list of scalars (optional items)
    """
    payload = {
        "metadata": {"schema_name": "Demo"},
        "structure": [
            {"fieldname": "title", "description": "Human title"},                 # required string, desc
            {"fieldname": "code", "pattern": r"^[A-Z]+$"},                        # string w/ pattern
            {"fieldname": "state", "fieldtype": "enum", "required": False,
             "default": "open", "options": ["open", "closed"]},                   # enum optional+default
            {"fieldname": "config", "fieldtype": "dict", "fields": [              # dict container
                {"fieldname": "retries", "fieldtype": "number", "required": False, "default": 3},
                {"fieldname": "label", "fieldtype": "string"},
            ]},
            {"fieldname": "steps", "fieldtype": "list", "item": {                 # list of dicts
                "fieldname": "step",
                "fieldtype": "dict",
                "fields": [
                    {"fieldname": "step_number", "fieldtype": "number"},
                    {"fieldname": "action", "fieldtype": "string"},
                ],
            }},
            {"fieldname": "tags", "fieldtype": "list", "item": {                  # list of scalars (optional)
                "fieldname": "tag", "fieldtype": "string", "required": False
            }},
        ],
    }
    return DocumentSchema.model_validate(payload)


# --- render_yaml_template --- #

def test_render_yaml_template_includes_headers_metadata_and_contents_block():
    schema = _schema()
    text = render_yaml_template(schema, list_examples=2)

    # Metadata header
    assert text.splitlines()[0] == "---"
    assert "metadata:" in text
    assert f"  document_type: {schema.schema_name}" in text
    assert "  document_version: 0.0.0" in text
    assert f"  format_version: {schema.format_version}" in text
    # Contents root
    assert "\ncontents:" in text


def test_render_yaml_template_scalars_comments_and_placeholders():
    schema = _schema()
    txt = render_yaml_template(schema, list_examples=2)

    # title: required + has description -> comment shows description (not "optional")
    assert "title: <required>  # Human title" in txt

    # code: pattern comment is included
    assert "code: <required>  # Pattern: ^[A-Z]+$" in txt

    # state: enum optional + default + options
    # (ordering in _comment: "optional", default, options)
    assert "state: <optional>  # optional. Default = 'open'. Options: open, closed" in txt


def test_render_yaml_template_containers_and_lists_formatting():
    schema = _schema()
    txt = render_yaml_template(schema, list_examples=2)
    lines = txt.splitlines()

    # Top-level dict gets a section header comment and a key line
    assert any(l.strip().startswith("# Config - Required") for l in lines)
    assert any(l.strip() == "config:" for l in lines)

    # list of dicts: shows one example comment and bullets for children
    assert "Example list: 'steps' shows 2 items." in txt
    # First list item should have "- " then child fields under it (indent rules)
    assert any(l.strip().startswith("- step_number:") for l in lines)
    assert any(l.strip().endswith("# Required") and "action:" in l for l in lines)

    # list of scalars (optional item) -> N lines "- <optional>"
    # We asked for 2 examples
    scalar_lines = [l for l in lines if l.strip() == "- <optional>"]
    assert len(scalar_lines) >= 2  # at least 2 lines rendered for tags


def test_render_yaml_template_list_examples_clamped_to_minimum_one():
    schema = _schema()
    txt = render_yaml_template(schema, list_examples=0)  # should clamp to 1
    # For scalar list 'tags', there should be exactly one "- <optional>" line
    count = sum(1 for l in txt.splitlines() if l.strip() == "- <optional>")
    assert count >= 1


# --- write_yaml_template --- #

def test_write_yaml_template_creates_parent_and_writes(tmp_path: Path):
    schema = _schema()
    out = tmp_path / "nested" / "doc.yaml"
    write_yaml_template(schema, out, list_examples=1)

    assert out.exists()
    text = out.read_text(encoding=DEFAULT_TEXT_ENCODING)
    # Sanity checks on written content
    assert "metadata:" in text and "contents:" in text
    assert "document_type: demo" in text  # normalized in schema metadata


def test__render_field_initializes_seen_list_set_when_none():
    # Minimal scalar field; pass seen_list_uids=None to hit the init branch
    fd = FieldDescriptor(fieldname="x")  # defaults to string/required
    lines = _render_field(fd, indent=2, list_examples=1, seen_list_uids=None)
    # Scalar line should be rendered; branch executed without error
    assert any(l.strip().startswith("x: <required>") for l in lines)


def test_nested_dict_uses_inline_container_comment_indent_not_two():
    # Structure: outer(dict) -> inner(dict) -> leaf(string)
    payload = {
        "metadata": {"schema_name": "demo"},
        "structure": [
            {
                "fieldname": "outer",
                "fieldtype": "dict",
                "fields": [
                    {
                        "fieldname": "inner",
                        "fieldtype": "dict",
                        "fields": [{"fieldname": "leaf"}],
                    }
                ],
            }
        ],
    }
    schema = DocumentSchema.model_validate(payload)
    txt = render_yaml_template(schema, list_examples=1)
    # For nested dicts (indent != 2), header should be "inner:  # Required"
    assert "inner:  # Required" in txt
    # And the scalar under it should still render
    assert "leaf: <required>" in txt


def test__string_pattern_returns_none_for_non_string_field():
    fd_num = FieldDescriptor(fieldname="n", fieldtype="number")
    assert _string_pattern(fd_num) is None


def test__enum_options_returns_empty_for_non_enum_field():
    from procdocs.core.schema.field_descriptor import FieldDescriptor
    from procdocs.core.yaml_scaffold import _enum_options

    # Default FieldDescriptor is a STRING (not ENUM), so _enum_options should fall back to []
    fd = FieldDescriptor(fieldname="x")
    assert _enum_options(fd) == []
