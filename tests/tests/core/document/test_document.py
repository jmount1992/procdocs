#!/usr/bin/env python3
import json
import yaml
import pytest
from types import SimpleNamespace

from procdocs.core.constants import DEFAULT_TEXT_ENCODING
from procdocs.core.document.document import Document, _format_pydantic_errors_simple
from procdocs.core.registry import SchemaRegistry


def _write_schema(tmp, name: str):
    payload = {
        "metadata": {"schema_name": name},
        "structure": [
            {"fieldname": "id", "pattern": r"^[A-Z]{2,4}-\d{3}$"},
            {"fieldname": "title"},
            {
                "fieldname": "steps",
                "fieldtype": "list",
                "fields": [
                    {"fieldname": "step_number", "fieldtype": "number"},
                    {"fieldname": "action"},
                ],
            },
        ],
    }
    p = tmp / f"{name}.json"
    p.write_text(json.dumps(payload), encoding=DEFAULT_TEXT_ENCODING)
    return p


def _write_doc(tmp, name: str, contents: dict, document_type: str = "alpha"):
    doc = {
        "metadata": {"document_type": document_type},
        "contents": contents,
    }
    p = tmp / f"{name}.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False), encoding=DEFAULT_TEXT_ENCODING)
    return p


# --- Happy paths --- #

def test_document_from_file_and_validate_via_registry(tmp_path):
    # schema
    root = tmp_path / "schemas"; root.mkdir()
    _write_schema(root, "alpha")

    reg = SchemaRegistry([root]); reg.load()

    # document
    dpath = _write_doc(tmp_path, "doc1", {
        "id": "AB-123",
        "title": "Run",
        "steps": [{"step_number": 1, "action": "start"}],
    }, document_type="alpha")

    doc = Document.from_file(dpath)
    errs = doc.validate(registry=reg)
    assert errs == []
    assert doc.is_valid is True


def test_document_validate_with_explicit_schema(tmp_path):
    root = tmp_path / "schemas"; root.mkdir()
    spath = _write_schema(root, "alpha")

    reg = SchemaRegistry([root]); reg.load()
    schema = reg.require("alpha")

    dpath = _write_doc(tmp_path, "doc2", {"id": "AB-123", "title": "t", "steps": []}, document_type="alpha")
    doc = Document.from_file(dpath)
    errs = doc.validate(schema=schema)
    assert errs == []


# --- Error paths --- #

def test_document_schema_resolution_failures(tmp_path):
    dpath = _write_doc(tmp_path, "doc3", {"id": "AB-123", "title": "t", "steps": []}, document_type="missing")
    doc = Document.from_file(dpath)

    # neither schema nor registry
    errs = doc.validate()
    assert errs and "No schema provided" in errs[0]

    # registry present but missing schema
    reg = SchemaRegistry([tmp_path]); reg.load()
    errs = doc.validate(registry=reg)
    assert errs and "Schema resolution failed" in errs[0]


def test_document_type_mismatch_error(tmp_path):
    root = tmp_path / "schemas"; root.mkdir()
    _write_schema(root, "alpha")
    reg = SchemaRegistry([root]); reg.load()

    dpath = _write_doc(tmp_path, "doc4", {"id": "AB-123", "title": "t", "steps": []}, document_type="beta")
    doc = Document.from_file(dpath)
    schema = reg.require("alpha")
    doc = Document.from_file(dpath)
    errs = doc.validate(schema=schema)  # explicit schema to trigger mismatch
    assert any("does not match schema 'alpha'" in e for e in errs)


def test_document_validation_reports_shape_and_type_errors(tmp_path):
    root = tmp_path / "schemas"; root.mkdir()
    _write_schema(root, "alpha")
    reg = SchemaRegistry([root]); reg.load()

    # bad: id fails pattern, steps[0].step_number wrong type, unknown key
    dpath = _write_doc(tmp_path, "doc5", {
        "id": "BAD123",
        "title": "t",
        "steps": [{"step_number": "one", "action": "go", "extra": True}],
        "oops": 1,
    }, document_type="alpha")

    doc = Document.from_file(dpath)
    errs = doc.validate(registry=reg)
    assert any("id" in e and "match" in e for e in errs)
    assert any("steps[0].step_number" in e for e in errs)
    assert any("extra" in e or "Unknown" in e for e in errs)


def test_document_from_file_rejects_non_yaml_ext(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match=r"expected a \.yml/\.yaml file|\.yml/.yaml"):
        Document.from_file(p)


def test_document_from_file_missing_raises(tmp_path):
    p = tmp_path / "missing.yaml"
    with pytest.raises(FileNotFoundError, match="does not exist"):
        Document.from_file(p)


def test_document_validate_without_schema_or_registry_returns_error(tmp_path):
    # minimal valid doc (no schema lookup here)
    p = tmp_path / "doc.yaml"
    p.write_text(yaml.safe_dump({"metadata": {"document_type": "x"}, "contents": {}}), encoding="utf-8")
    doc = Document.from_file(p)
    errs = doc.validate()  # neither schema nor registry passed
    assert errs and "No schema provided" in errs[0]
    # touches is_valid property too
    assert doc.is_valid is False


def test__format_pydantic_errors_simple_handles_root_loc():
    """
    Exercise the '<root>' branch when Pydantic returns an error entry with empty 'loc'.
    We feed a dummy object that quacks like a ValidationError.
    """
    dummy = SimpleNamespace(
        errors=lambda: [
            {"loc": (), "msg": "Something went boom"},  # empty loc -> '<root>'
            {"loc": ("contents",), "msg": "Another issue"},  # normal path
        ]
    )
    msgs = _format_pydantic_errors_simple(dummy)  # type: ignore[arg-type]
    assert any(m.startswith("<root>: ") for m in msgs)
    assert any(m.startswith("contents: ") for m in msgs)


def test_document_from_json_str_helper_covers_path():
    """
    Touch the from_json_str() helper to cover that construction path.
    """
    json_text = '{"metadata": {"document_type": "x"}, "contents": {}}'
    doc = Document.from_json_str(json_text)
    # ensure the model parsed
    assert doc.metadata.document_type == "x"


def test_validate_branch_when_document_type_missing_via_model_construct(tmp_path):
    # Empty registry is fine; we only need it present to bypass the "no registry" early return.
    reg = SchemaRegistry([tmp_path])
    reg.load()

    # Bypass normal validation to simulate a missing metadata/document_type
    doc = Document.model_construct(metadata=None, contents={})  # no validation on construct

    errs = doc.validate(registry=reg)
    assert errs and "metadata.document_type is missing" in errs[0]