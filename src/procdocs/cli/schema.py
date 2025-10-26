#!/usr/bin/env python3

from pathlib import Path
from pydantic import ValidationError
from typing import Optional

from procdocs.core.app_context import AppContext
from procdocs.core.schema.document_schema import DocumentSchema
from procdocs.core.formatting import format_pydantic_errors_simple


def register(subparsers):
    sp = subparsers.add_parser("schema", help="Schema utilities")
    sps = sp.add_subparsers(dest="schema_cmd")

    # default when user runs: `procdocs schema`
    def schema_default(args, ctx: AppContext) -> int:
        sp.print_help()
        return 1
    sp.set_defaults(func=schema_default)

    lp = sps.add_parser("list", help="List schemas")
    lp.add_argument("--all", action="store_true", help="Include invalid schemas")
    lp.add_argument("--invalid", action="store_true", help="Show only invalid schemas")
    lp.add_argument("--json", action="store_true", help="JSON output")
    lp.set_defaults(func=list_schemas)

    vsp = sps.add_parser("validate", help="Validate a schema")
    vsp.add_argument("schema", help="Schema name or path")
    vsp.set_defaults(func=validate_schema)

    ssp = sps.add_parser("show", help="Show schema JSON")
    ssp.add_argument("schema", help="Schema name")
    ssp.set_defaults(func=show_schema)

    dsp = sps.add_parser("doctor", help="Scan schema paths and report issues")
    dsp.set_defaults(func=doctor_schema)


def list_schemas(args, ctx: AppContext) -> int:
    print("Searched schema_paths:", ", ".join(ctx.config.get("schema_paths", [])) or "<none>")

    entries = _select_entries(args, ctx)

    if args.json:
        return _print_entries_json(entries)

    if not entries:
        print("No schemas found.")
        return 1

    print("\nSchemas Found:")
    for e in _sorted_entries(entries):
        print(_format_entry_line(e))
    return 0


def validate_schema(args, ctx: AppContext) -> int:
    target = args.schema

    # Try by schema name via registry (valids only)
    try:
        ctx.schemas.require(target)
        path_hint = next((e.path for e in ctx.schemas.valid_entries() if e.name == target), None)
        suffix = f"  ({path_hint})" if path_hint else ""
        print(f"Schema '{target}' is VALID{suffix}")
        return 0
    except Exception:
        print(f"Could not find Schema '{target}' in registery. Attempting to find via path.")

    # Try as a direct file path (covers invalid/unregistered files)
    p = Path(target)
    if p.exists():
        return _validate_schema_file(p)

    # Fallback: look up an invalid entry recorded by the registry (by name or stem)
    matches = [e for e in ctx.schemas.invalid_entries() if e.name == target or e.path.stem == target]
    if matches:
        e = matches[0]
        # Re-parse now to recover structured errors (file may have changed since scan)
        try:
            _ = DocumentSchema.from_file(e.path)  # If it succeeds, file is now valid
            print(f"Schema '{target}' is now VALID  ({e.path})")
            return 0
        except ValidationError as ve:
            return _report_pydantic_invalid(f"Schema '{target}' is INVALID  ({e.path})", ve)
        except Exception as ex:
            return _report_exception_invalid(f"Schema '{target}' is INVALID  ({e.path})", ex)

    print(f"Schema '{target}' not found by name or path.")
    return 1


def show_schema(args, ctx: AppContext) -> int:
    try:
        s = ctx.schemas.require(args.schema)
        data = s.to_dict() if hasattr(s, "to_dict") else s.__dict__
        import json
        print(json.dumps(data, indent=2, default=str))
        return 0
    except Exception as e:
        print(f"Schema '{args.schema}' not found: {e}")
        return 1


def doctor_schema(args, ctx: AppContext) -> int:
    roots = [Path(p) for p in ctx.config.get("schema_paths", [])]
    print("Schema roots:")
    for r in roots:
        print(f"  • {r.resolve()}  ({'exists' if r.exists() else 'missing'})")

    any_found = False
    for r in roots:
        if not r.exists():
            continue
        for p in r.rglob("*.json"):
            any_found = True
            try:
                s = DocumentSchema.from_file(p)
                print(f"  ✓ {p}  -> schema_name='{s.schema_name}'")
            except Exception as e:
                first = str(e).splitlines()[0]
                brief = first.split(" for ")[0]
                print(f"  ✗ {p}  -> INVALID: {brief}")
    if not any_found:
        print("No *.json files found under configured roots.")
        return 1
    return 0


# --- Internal helpers --- #

def _report_pydantic_invalid(header: str, ve: ValidationError) -> int:
    msgs = format_pydantic_errors_simple(ve)
    print(f"\n{header}")
    for m in msgs:
        print(f"  - {m}")
    print(f"\n({len(msgs)} error{'s' if len(msgs) != 1 else ''})")
    return 1


def _report_exception_invalid(header: str, ex: Exception) -> int:
    first = str(ex).splitlines()[0] if str(ex) else ex.__class__.__name__
    print(f"\n{header}")
    print(f"  - {first}")
    print("\n(1 error)")
    return 1


def _validate_schema_file(path: Path, label: str = "Schema file") -> int:
    try:
        _ = DocumentSchema.from_file(path)
        print(f"{label} is VALID  ({path})")
        return 0
    except ValidationError as ve:
        return _report_pydantic_invalid(f"{label} is INVALID  ({path})", ve)
    except Exception as ex:
        return _report_exception_invalid(f"{label} is INVALID  ({path})", ex)


def _select_entries(args, ctx: AppContext):
    if getattr(args, "invalid", False):
        return ctx.schemas.invalid_entries()
    if getattr(args, "all", False):
        return ctx.schemas.entries()
    return ctx.schemas.valid_entries()


def _sorted_entries(entries):
    def display_name(e):
        return (e.name or e.path.stem).lower()
    # valid first (False < True), then by display name
    return sorted(entries, key=lambda x: (not x.valid, display_name(x)))


def _brief_reason(reason: Optional[str]) -> str:
    if not reason:
        return "unknown"
    first = reason.splitlines()[0]
    return first.split(" for ")[0]


def _format_entry_line(e) -> str:
    status = "✓ valid" if e.valid else f"✗ invalid ({_brief_reason(e.reason)})"
    name = e.name or e.path.stem
    ver = f" v{e.version}" if e.version else ""
    return f"  - {name:24} {status:35}  {e.path}{ver}"


def _print_entries_json(entries) -> int:
    import json
    payload = [{
        "name": e.name,
        "valid": e.valid,
        "path": str(e.path),
        "version": e.version,
        "reason": e.reason,
    } for e in entries]
    print(json.dumps(payload, indent=2))
    return 0 if payload else 1
