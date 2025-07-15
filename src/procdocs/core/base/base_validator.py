#!/usr/bin/env python3


class BaseValidator(type):
    def __init__(cls, name, bases, namespace):
        cls._check_subclass_lists_defined(cls)
        cls._check_subclass_lists_are_lists(cls)
        cls._check_no_duplicate_attributes(cls)
        cls._check_no_override_of_parent_attributes(cls)
        cls._check_required_subset_of_attributes(cls)
        cls._check_attribute_naming_convention(cls)
        cls._check_properties_exists_for_attributes(cls)

        super().__init__(name, bases, namespace)

    @staticmethod
    def _check_subclass_lists_defined(cls):
        missing = [attr for attr in ("_REQUIRED", "_ATTRIBUTES") if attr not in cls.__dict__]
        if missing:
            joined = ", ".join(missing)
            raise NotImplementedError(f"{cls.__name__} must define class-level attribute(s): {joined}")

    @staticmethod
    def _check_subclass_lists_are_lists(cls):
        if not isinstance(cls._REQUIRED, list) or not isinstance(cls._ATTRIBUTES, list):
            raise TypeError(f"{cls.__name__}._REQUIRED and _ATTRIBUTES must be lists")

    @staticmethod
    def _check_no_duplicate_attributes(cls):
        seen = cls._ATTRIBUTES
        if len(seen) != len(set(seen)):
            from collections import Counter
            dupes = [item for item, count in Counter(seen).items() if count > 1]
            raise ValueError(f"{cls.__name__}._ATTRIBUTES contains duplicate entries: {dupes}")

    @staticmethod
    def _check_no_override_of_parent_attributes(cls):
        parent_attrs = []
        for base in cls.__mro__[1:]:  # skip cls itself
            base_attrs = getattr(base, "_ATTRIBUTES", [])
            parent_attrs.extend(base_attrs)

        # Flattened list of parent attributes
        duplicates = [a for a in cls._ATTRIBUTES if a in parent_attrs]
        if duplicates:
            raise ValueError(
                f"{cls.__name__}._ATTRIBUTES redefines attribute(s) already declared in parent classes: {duplicates}"
            )

    @staticmethod
    def _check_required_subset_of_attributes(cls):
        extra = [r for r in cls._REQUIRED if r not in cls._ATTRIBUTES]
        if extra:
            raise ValueError(f"{cls.__name__}._REQUIRED includes unknown fields: {extra}")

    @staticmethod
    def _check_attribute_naming_convention(cls):
        invalid = [a for a in cls._ATTRIBUTES if not a.startswith("_")]
        if invalid:
            raise ValueError(f"{cls.__name__}._ATTRIBUTES entries must start with '_': {invalid}")

    @staticmethod
    def _check_properties_exists_for_attributes(cls):
        missing_properties = []
        for private_name in cls._ATTRIBUTES:
            public_name = private_name.lstrip("_")
            prop = getattr(cls, public_name, None)
            if not isinstance(prop, property):
                missing_properties.append(public_name)
        if missing_properties:
            joined = ", ".join(missing_properties)
            raise AttributeError(f"{cls.__name__} is missing @property declarations for: {joined}")