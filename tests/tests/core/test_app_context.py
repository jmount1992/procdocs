#!/usr/bin/env python3
import pytest
from pathlib import Path
from dataclasses import FrozenInstanceError

import procdocs.core.app_context as ac


class _StubRegistry:
    """Captures roots and load() calls."""
    def __init__(self, roots):
        self.roots = list(roots)
        self.load_calls = []

    def load(self, *, clear: bool):
        self.load_calls.append({"clear": clear})


def test_build_context_uses_load_config_when_config_missing_and_preloads(tmp_path, monkeypatch):
    # Arrange: config returned by load_config()
    cfg = {
        "schema_paths": [str(tmp_path / "schemasA"), str(tmp_path / "schemasB")],
        "render_template_paths": [str(tmp_path / "tmplA")],
    }
    monkeypatch.setattr(ac, "load_config", lambda: cfg)

    # Stub registries to capture constructor args and load() calls
    created = {}
    def _schema_stub(roots):
        created["schemas"] = _StubRegistry(roots)
        return created["schemas"]

    def _tmpl_stub(roots):
        created["templates"] = _StubRegistry(roots)
        return created["templates"]

    monkeypatch.setattr(ac, "SchemaRegistry", _schema_stub)
    monkeypatch.setattr(ac, "TemplateRegistry", _tmpl_stub)

    # Act
    ctx = ac.build_context()  # preload=True default

    # Assert: config came from load_config()
    assert ctx.config is cfg

    # Roots were converted to Path and passed through
    assert [Path(p) for p in cfg["schema_paths"]] == created["schemas"].roots
    assert [Path(p) for p in cfg["render_template_paths"]] == created["templates"].roots

    # Preload triggered load(clear=True) on both registries
    assert created["schemas"].load_calls == [{"clear": True}]
    assert created["templates"].load_calls == [{"clear": True}]


def test_build_context_overrides_and_no_preload(tmp_path, monkeypatch):
    # Provide explicit config (should not call load_config)
    cfg = {"schema_paths": ["ignored"], "render_template_paths": ["ignored"]}
    monkeypatch.setattr(ac, "load_config", lambda: (_ for _ in ()).throw(AssertionError("should not be called")))

    created = {}
    monkeypatch.setattr(ac, "SchemaRegistry", lambda roots: created.setdefault("schemas", _StubRegistry(roots)))
    monkeypatch.setattr(ac, "TemplateRegistry", lambda roots: created.setdefault("templates", _StubRegistry(roots)))

    schema_roots = [tmp_path / "s1", tmp_path / "s2"]
    tmpl_roots = [tmp_path / "t1"]

    ctx = ac.build_context(
        config=cfg,
        schema_roots=schema_roots,
        template_roots=tmpl_roots,
        preload=False,
    )

    # Assert: overrides were used (not cfg values)
    assert created["schemas"].roots == schema_roots
    assert created["templates"].roots == tmpl_roots

    # No preload -> load() not called
    assert created["schemas"].load_calls == []
    assert created["templates"].load_calls == []

    # Returned types are the stub instances
    assert ctx.schemas is created["schemas"]
    assert ctx.templates is created["templates"]


def test_appcontext_is_frozen_dataclass(tmp_path, monkeypatch):
    # Minimal stubs/ctx
    monkeypatch.setattr(ac, "SchemaRegistry", lambda roots: _StubRegistry(roots))
    monkeypatch.setattr(ac, "TemplateRegistry", lambda roots: _StubRegistry(roots))
    monkeypatch.setattr(ac, "load_config", lambda: {"schema_paths": [str(tmp_path)], "render_template_paths": [str(tmp_path)]})

    ctx = ac.build_context(preload=False)

    with pytest.raises(FrozenInstanceError):
        ctx.config = {}
