#!/usr/bin/env python3
import pytest
from pydantic import BaseModel, ValidationError

from procdocs.core.schema.field_specs import (
    StringSpec, NumberSpec, BooleanSpec, EnumSpec, DictSpec, ListSpec, RefSpec,
    FieldSpec
)


# --- Helpers --- #
class Holder(BaseModel):
    spec: FieldSpec


# --- Discriminated union parsing for each 'kind' --- #

@pytest.mark.parametrize("payload,expected_cls", [
    ({"kind": "string"}, StringSpec),
    ({"kind": "number"}, NumberSpec),
    ({"kind": "boolean"}, BooleanSpec),
    ({"kind": "enum", "options": ["A", "B"]}, EnumSpec),

    # Use FieldDescriptor-shaped dicts, not Dummy
    ({"kind": "dict", "fields": [{"fieldname": "x", "fieldtype": "string"}]}, DictSpec),
    ({"kind": "list", "item": {"fieldname": "x", "fieldtype": "number"}}, ListSpec),

    ({"kind": "ref"}, RefSpec),
])
def test_fieldspec_discriminated_union_parses(payload, expected_cls):
    obj = Holder.model_validate({"spec": payload}).spec
    assert isinstance(obj, expected_cls)


# --- StringSpec --- #

def test_string_spec_optional_pattern_field():
    s = StringSpec()
    assert s.kind == "string" and s.pattern is None
    s2 = StringSpec(pattern=r"^[A-Z]+$")
    assert s2.pattern == r"^[A-Z]+$"


# --- EnumSpec --- #

def test_enum_spec_requires_non_empty_options():
    with pytest.raises(ValidationError):
        EnumSpec(options=[])

    e = EnumSpec(options=["A"])
    assert e.options == ["A"]


# --- DictSpec --- #

def test_dict_spec_requires_at_least_one_field():
    with pytest.raises(ValidationError):
        DictSpec(fields=[])

    d = DictSpec(fields=[{"fieldname": "id", "fieldtype": "string"}])
    assert len(d.fields) == 1


# --- ListSpec --- #

def test_list_spec_requires_item_and_accepts_fielddescriptor_payload():
    with pytest.raises(ValidationError):
        ListSpec.model_validate({"kind": "list"})  # missing item

    l = ListSpec(item={"fieldname": "val", "fieldtype": "number"})
    assert l.item.fieldname == "val"


# --- RefSpec --- #

def test_ref_spec_defaults_and_valid_overrides():
    r = RefSpec()
    assert r.cardinality == "one"
    assert r.allow_globs is False
    assert r.must_exist is False
    assert r.base_dir is None
    assert r.extensions is None

    r2 = RefSpec(cardinality="many", allow_globs=True, must_exist=True,
                 base_dir="/tmp", extensions=[".yml", ".yaml"])
    assert r2.cardinality == "many"
    assert r2.allow_globs is True
    assert r2.must_exist is True
    assert r2.base_dir == "/tmp"
    assert r2.extensions == [".yml", ".yaml"]


def test_ref_spec_invalid_cardinality_rejected():
    with pytest.raises(ValidationError):
        RefSpec.model_validate({"kind": "ref", "cardinality": "several"})
