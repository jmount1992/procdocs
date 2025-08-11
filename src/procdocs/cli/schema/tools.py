#!/usr/bin/env python3

from pathlib import Path

from procdocs.core.app_context import AppContext
from procdocs.core.schema.document_schema import DocumentSchema


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

    # choose set to display
    if args.invalid:
        entries = ctx.schemas.invalid_entries()
    elif args.all:
        entries = ctx.schemas.entries()
    else:
        entries = ctx.schemas.valid_entries()

    if args.json:
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

    if not entries:
        print("No schemas found.")
        return 1

    # Pretty listing: sort valids first, then by display name (case-insensitive)
    def display_name(e):
        return (e.name or e.path.stem).lower()

    print("\nSchemas Found:")
    for e in sorted(entries, key=lambda x: (not x.valid, display_name(x))):
        if not e.valid and e.reason:
            first = e.reason.splitlines()[0]
            brief = first.split(" for ")[0]
        status = "✓ valid" if e.valid else f"✗ invalid ({brief})"
        name = e.name or e.path.stem
        ver = f" v{e.version}" if e.version else ""
        line = f"  - {name:24} {status:35}  {e.path}{ver}"
        print(line)
    return 0


def validate_schema(args, ctx: AppContext) -> int:
    target = args.schema

    # Try by name (valids only)
    try:
        ctx.schemas.require(target)
        print(f"Valid schema: {target}")
        return 0
    except Exception:
        pass

    # Try as path (for invalids or unregistered files)
    p = Path(target)
    if p.exists():
        try:
            DocumentSchema.from_file(p)  # will raise if invalid
            print(f"Valid schema file: {p}")
            return 0
        except Exception as e:
            print(f"Schema file invalid: {p}\n{e}")
            return 1

    # Fallback: attempt to match invalid by stem or recorded name
    matches = [e for e in ctx.schemas.invalid_entries()
               if (e.path.stem == target or (e.name and e.name == target))]
    if matches:
        e = matches[0]
        print(f"Invalid schema: {target} ({e.path})\n{e.reason or ''}")
        return 1

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
