#!/usr/bin/env python3

import pytest

from procdocs.core.base.base import BaseValidator


class ValidBase(metaclass=BaseValidator):
    _REQUIRED = ["_foo"]
    _ATTRIBUTES = ["_foo"]

    def __init__(self):
        self._foo = None
        super().__init__()

    @property
    def foo(self): self._foo


# --- VALID CLASS DEFINITIION TESTS --- #
def test_valid_class_definition():
    """Simple instantiation of a valid object"""
    assert hasattr(ValidBase(), "foo")


def test_valid_subclass_without_extending():
    """Check a valid derived class doesn't throw any errors."""
    class Sub(ValidBase):
        _REQUIRED = []
        _ATTRIBUTES = []
    assert hasattr(Sub(), "foo")


def test_multiple_inheritance_ok():
    """Test multiple inheritance doesn't throw errors."""
    class DummyMixin:
        pass
    class Mixed(ValidBase, DummyMixin):
        _REQUIRED = []
        _ATTRIBUTES = []
    assert hasattr(Mixed(), "foo")


@pytest.mark.parametrize("baseclass, metaclass", [
    (object, BaseValidator),
    (ValidBase, type)
])
def test_empty_lists_are_valid(baseclass, metaclass):
    class EmptyOK(baseclass, metaclass=metaclass):
        _REQUIRED = []
        _ATTRIBUTES = []


# --- INVALID CLASS DEFINITION TESTS --- #
@pytest.mark.parametrize("baseclass, metaclass", [
    (object, BaseValidator),
    (ValidBase, type)
])
def test_missing_lists(baseclass, metaclass):
    with pytest.raises(NotImplementedError, match="_REQUIRED, _ATTRIBUTES"):
        class MissingRequired(baseclass, metaclass=metaclass):
            @property
            def bar(self): return "x"


@pytest.mark.parametrize("baseclass, metaclass", [
    (object, BaseValidator),
    (ValidBase, type)
])
def test_missing_required_list(baseclass, metaclass):
    with pytest.raises(NotImplementedError, match="_REQUIRED"):
        class MissingRequired(baseclass, metaclass=metaclass):
            _ATTRIBUTES = []
            @property
            def bar(self): return "x"


@pytest.mark.parametrize("baseclass, metaclass", [
    (object, BaseValidator),
    (ValidBase, type)
])
def test_missing_attributes_list(baseclass, metaclass):
    with pytest.raises(NotImplementedError, match="_ATTRIBUTES"):
        class MissingAttributes(baseclass, metaclass=metaclass):
            _REQUIRED = []
            @property
            def bar(self): return "x"


@pytest.mark.parametrize("baseclass, metaclass", [
    (object, BaseValidator),
    (ValidBase, type)
])
def test_required_not_list(baseclass, metaclass):
    with pytest.raises(TypeError):
        class RequiredNotList(baseclass, metaclass=metaclass):
            _REQUIRED = "_bar"
            _ATTRIBUTES = ["_bar"]
            @property
            def bar(self): return "x"


@pytest.mark.parametrize("baseclass, metaclass", [
    (object, BaseValidator),
    (ValidBase, type)
])
def test_attributes_not_list(baseclass, metaclass):
    with pytest.raises(TypeError):
        class AttributesNotList(baseclass, metaclass=metaclass):
            _REQUIRED = ["_bar"]
            _ATTRIBUTES = "_bar"
            @property
            def bar(self): return "x"


@pytest.mark.parametrize("baseclass, metaclass", [
    (object, BaseValidator),
    (ValidBase, type)
])
def test_required_not_subset_of_attributes(baseclass, metaclass):
    with pytest.raises(ValueError, match="includes unknown fields"):
        class NotSubset(baseclass, metaclass=metaclass):
            _REQUIRED = ["_att"]
            _ATTRIBUTES = ["_bar"]
            @property
            def bar(self): return "x"


@pytest.mark.parametrize("baseclass, metaclass", [
    (object, BaseValidator),
    (ValidBase, type)
])
def test_invalid_attribute_name(baseclass, metaclass):
    with pytest.raises(ValueError, match="must start with '_'"):
        class InvalidAttrName(baseclass, metaclass=metaclass):
            _REQUIRED = ["bad"]
            _ATTRIBUTES = ["bad"]
            @property
            def bad(self): return "x"


@pytest.mark.parametrize("baseclass, metaclass", [
    (object, BaseValidator),
    (ValidBase, type)
])
def test_missing_property(baseclass, metaclass):
    with pytest.raises(AttributeError, match="is missing @property declarations for"):
        class MissingProperty(baseclass, metaclass=metaclass):
            _REQUIRED = ["_bar"]
            _ATTRIBUTES = ["_bar"]


@pytest.mark.parametrize("baseclass, metaclass", [
    (object, BaseValidator),
    (ValidBase, type)
])
def test_duplicate_attribute(baseclass, metaclass):
    with pytest.raises(ValueError, match="contains duplicate entries"):
        class DuplicateAttribute(baseclass, metaclass=metaclass):
            _REQUIRED = ["_bar", "_bar"]
            _ATTRIBUTES = ["_bar", "_bar"]


def test_parent_attribute_override():
    with pytest.raises(ValueError, match="already declared in parent classes"):
        class AttributeOverride(ValidBase, metaclass=BaseValidator):
            _REQUIRED = ["_foo"]
            _ATTRIBUTES = ["_foo"]
