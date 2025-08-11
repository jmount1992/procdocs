#!/usr/bin/env python3

from pathlib import Path

from procdocs.core.app_context import AppContext


def register(subparsers):
    sp = subparsers.add_parser("render-template", help="Render template utilities")
    sps = sp.add_subparsers(dest="render_templates_cmd")

    # default when user runs: `procdocs schema`
    def render_template_default(args, ctx: AppContext) -> int:
        sp.print_help()
        return 1
    sp.set_defaults(func=render_template_default)

    lp = sps.add_parser("list", help="List render templates")
    lp.add_argument("--all", action="store_true", help="Include invalid schemas")
    lp.add_argument("--invalid", action="store_true", help="Show only invalid schemas")
    lp.set_defaults(func=list_render_templates)


def list_render_templates(args, ctx: AppContext) -> int:
    print("Searched template_paths:", ", ".join(ctx.config.get("render_template_paths", [])) or "<none>")

    # choose set to display
    if args.invalid:
        entries = ctx.templates.invalid_entries()
    elif args.all:
        entries = ctx.templates.entries()
    else:
        entries = ctx.templates.valid_entries()

    if not entries:
        print("No render templates found.")
        return 1

    # Pretty listing: sort valids first, then by display name (case-insensitive)
    def display_name(e):
        return (e.name or e.path.stem).lower()

    print("\nRender Templates Found:")
    for e in sorted(entries, key=lambda x: (not x.valid, display_name(x))):
        if not e.valid and e.reason:
            first = e.reason.splitlines()[0]
            brief = first.split(" for ")[0]
        status = "✓ valid" if e.valid else f"✗ invalid ({brief})"
        name = e.name or e.path.stem
        line = f"  - {name:24} {status:35}  {e.path}"
        print(line)
    return 0
