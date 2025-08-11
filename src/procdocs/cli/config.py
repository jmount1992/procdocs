# procdocs/cli/config.py
#!/usr/bin/env python3
import json
from procdocs.core.app_context import AppContext

def register(subparsers):
    sp = subparsers.add_parser("config", help="Config utilities")
    sps = sp.add_subparsers(dest="config_cmd")

    showp = sps.add_parser("show", help="Show effective config")
    showp.set_defaults(func=show_config)

def show_config(args, ctx: AppContext) -> int:
    print(json.dumps(ctx.config, indent=2))
    return 0
