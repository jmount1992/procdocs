#!/usr/bin/env python3
import procdocs.core.app as app


class _StubContext:
    def __init__(self, tag, **kwargs):
        self.tag = tag
        self.kwargs = kwargs


def test_get_context_builds_once_and_caches(monkeypatch):
    # Reset module cache
    app._CTX = None

    calls = []

    def fake_build_context(**kwargs):
        calls.append(kwargs)
        return _StubContext(tag=len(calls), **kwargs)

    monkeypatch.setattr(app, "build_context", fake_build_context)

    # First call builds
    ctx1 = app.get_context()
    assert isinstance(ctx1, _StubContext)
    assert ctx1.tag == 1
    assert calls[-1]["preload"] is True  # always True per implementation

    # Second call reuses cache (no new build_context call)
    ctx2 = app.get_context()
    assert ctx2 is ctx1
    assert len(calls) == 1


def test_get_context_force_reload_triggers_rebuild(monkeypatch):
    app._CTX = None
    calls = []

    def fake_build_context(**kwargs):
        calls.append(kwargs)
        return _StubContext(tag=len(calls), **kwargs)

    monkeypatch.setattr(app, "build_context", fake_build_context)

    # Initial build
    first = app.get_context()
    assert first.tag == 1
    assert len(calls) == 1

    # Force reload -> second build
    second = app.get_context(force_reload=True)
    assert second is not first
    assert second.tag == 2
    assert len(calls) == 2


def test_get_context_passes_overrides(monkeypatch, tmp_path):
    app._CTX = None
    recorded = []

    def fake_build_context(**kwargs):
        recorded.append(kwargs)
        return _StubContext(tag=len(recorded), **kwargs)

    monkeypatch.setattr(app, "build_context", fake_build_context)

    cfg = {"schema_paths": ["ignored"], "render_template_paths": ["ignored"]}
    sroots = [tmp_path / "schemas"]
    troots = [tmp_path / "templates"]

    ctx = app.get_context(
        config_override=cfg,
        schema_roots_override=sroots,
        template_roots_override=troots,
    )

    assert isinstance(ctx, _StubContext)
    assert recorded  # at least one call recorded

    last = recorded[-1]
    # Overrides should be passed through as-is
    assert last["config"] is cfg
    assert last["schema_roots"] is sroots
    assert last["template_roots"] is troots
    # Preload is always True
    assert last["preload"] is True


def test_get_context_returns_cached_when_no_overrides(monkeypatch):
    app._CTX = None
    calls = []

    def fake_build_context(**kwargs):
        calls.append(kwargs)
        return _StubContext(tag=len(calls), **kwargs)

    monkeypatch.setattr(app, "build_context", fake_build_context)

    # Build once
    ctx1 = app.get_context()
    assert ctx1.tag == 1
    assert len(calls) == 1

    # Call again with no overrides and no force_reload: cached
    ctx2 = app.get_context()
    assert ctx2 is ctx1
    assert len(calls) == 1
