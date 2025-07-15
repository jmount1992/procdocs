# tests/test_base_class.py

import pytest
import re

from procdocs.core.base.base import Base
from procdocs.core.validation import ValidationResult


def test_object_instantiation():
    instance = Base()
    assert hasattr(instance, "user_defined")
    assert instance.user_defined == []
    assert instance._user_defined == {}


def test_attributes_properties():
    instance = Base()
    assert hasattr(instance, "user_defined")
    assert instance.attributes == ["user_defined"]
    assert instance._attributes == ["_user_defined"]


def test_required_properties():
    class ExtendedBase(Base):
        _REQUIRED = ["_foo"]
        _ATTRIBUTES = ["_foo"]
        @property
        def foo(self): return self._foo
    instance = ExtendedBase()
    assert hasattr(instance, "foo")
    assert instance.required == ["foo"]
    assert instance._required == ["_foo"]


@pytest.mark.parametrize("dynamic_gen", [True, False])
def test_dynamic_attribute_generation(dynamic_gen):
    class ExtendedBase(Base):
        _REQUIRED = ["_foo"]
        _ATTRIBUTES = ["_foo"]
        def __init__(self, dynamic_gen):
            if not dynamic_gen:
                self._foo = "x"
            super().__init__()
        @property
        def foo(self): return self._foo
    instance = ExtendedBase(dynamic_gen)
    assert hasattr(instance, "foo")

    if dynamic_gen:
        assert instance.foo is None
        assert instance._foo is None
    else:
        assert instance.foo == "x"
        assert instance._foo == "x"


@pytest.mark.parametrize("strict", [True, False])
def test_not_implemented_error(strict):
    with pytest.raises(NotImplementedError, match=re.escape("Derived class must implement _validate_additional()")):
        Base.from_dict({}, strict=strict)


@pytest.mark.parametrize("data", [
    ({}),
    ({"attribute_1": 1, "attribute_2": "two", "attribute_2": ["one", "two"]}),
])
def test_user_defined_attribute(monkeypatch, data):
    def dummy(self, collector, strict):
        return collector
    monkeypatch.setattr(Base, "_validate_additional", dummy)

    b = Base.from_dict(data, strict=False)
    assert b._user_defined == data
    assert b.user_defined == list(data.keys())

    for key, val in data.items():
        assert hasattr(b, key) is True
        assert getattr(b, key) == val

    outdict = b.to_dict()
    for key, val in data.items():
        assert outdict.get(key) == val


class DummyParent(Base):
    _REQUIRED = ["_a"]
    _ATTRIBUTES = ["_a", "_x"]
    def __init__(self):
        super().__init__()
    def _validate_additional(self, collector, strict):
        return collector
    @property
    def a(self):
        return self.a
    @property
    def x(self):
        return self.x


class DummyChild(DummyParent):
    _REQUIRED = ["_b"]
    _ATTRIBUTES = ["_b", "_y"]
    def __init__(self):
        super().__init__()
    @property
    def b(self):
        return self.b
    @property
    def y(self):
        return self.y


def test_required_and_derived_collection_across_inheritance():
    d = DummyChild()
    assert set(d.required) == set(["a", "b"])
    assert set(d.attributes) == set(["a", "b", "x", "y", "user_defined"])


def test_get_attribute(monkeypatch):
    # test quick grab of attribute obj.attribute
    def dummy(self, collector, strict):
        return collector
    monkeypatch.setattr(Base, "_validate_additional", dummy)

    b = Base.from_dict({"attribute_1": 1})
    assert b.attribute_1 == 1


class LooseBase(Base):
    _REQUIRED = ["_a"]
    _ATTRIBUTES = ["_a", "_b"]

    def __init__(self):
        super().__init__()

    def _validate_additional(self, collector, strict):
        collector.report("Test warning from _validate_additional()", strict)
        return collector
    @property
    def a(self):
        return self._a
    @property
    def b(self):
        return self._b


def test_validation_collects_errors_when_not_strict():
    lb = LooseBase()
    result = lb.validate(strict=False)
    print(result.errors)

    # Should report:
    #   - missing required attributes: 'a'
    #   - Test warning from _validate_additional'
    assert isinstance(result, ValidationResult)
    assert len(result) == 2 

    error_strs = list(result)
    assert "Missing required metadata fields" in error_strs[0]
    assert "a" in error_strs[0]
    assert "Test warning from _validate_additional()" in error_strs[1]


def test_to_dict_strips_private_prefix():
    class MyClass(Base):
        _REQUIRED = ["_foo"]
        _ATTRIBUTES = ["_foo"]
        def __init__(self):
            super().__init__()
            self._foo = "bar"
        def _validate_additional(self, collector, strict): return collector
        @property
        def foo(self): return self._foo

    instance = MyClass()
    d = instance.to_dict()
    assert "foo" in d
    assert "_foo" not in d
    assert "user_defined" not in d


def test_unknown_attribute_raises():
    md = Base()
    with pytest.raises(AttributeError):
        _ = md.non_existent_key


def test_user_defined_does_not_shadow_property(monkeypatch):
    class ShadowTest(Base):
        _REQUIRED = ["_foo"]
        _ATTRIBUTES = ["_foo"]
        def __init__(self):
            super().__init__()
            self._foo = "correct"
        def _validate_additional(self, collector, strict): return collector
        @property
        def foo(self): return self._foo

    instance = ShadowTest()
    instance._add_user_field("foo", "incorrect")
    assert instance.foo == "correct"  # property wins


@pytest.mark.parametrize("data", [
    {"attribute-1": "value", "attribute_2": 2},  # dash key
])
def test_user_defined_dash_keys_are_normalized(monkeypatch, data):
    def dummy(self, collector, strict):
        return collector
    monkeypatch.setattr(Base, "_validate_additional", dummy)
    instance = Base.from_dict(data, strict=False)
    assert hasattr(instance, "attribute-1")
    assert getattr(instance, "attribute-1") == data["attribute-1"]
    assert hasattr(instance, "attribute_2")
    assert getattr(instance, "attribute_2") == data["attribute_2"]


def test_validate_reports_errors_from_custom_logic():
    class Custom(Base):
        _REQUIRED = ["_foo"]
        _ATTRIBUTES = ["_foo"]
        def __init__(self): super().__init__()
        def _validate_additional(self, collector, strict):
            collector.report("This is a test error", strict)
            return collector
        @property
        def foo(self): return self._foo

    instance = Custom()
    result = instance.validate(strict=False)
    assert any("test error" in err.lower() for err in result.errors)
