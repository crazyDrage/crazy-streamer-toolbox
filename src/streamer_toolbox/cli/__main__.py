"""The toolbox from a terminal (toolbox.bat / toolbox.sh start this); the toolbox itself has to be running.

    toolbox list              every action this caller may run
    toolbox list obs.*        only those whose name fits (a word without * is searched in the names)
    toolbox info hello.greet  what one action does and takes
    toolbox run hello.greet name=chat
    toolbox run obs.set_volume --json "{\\"source\\": \\"Mic\\", \\"volume\\": 0.5}"

name=value parameters are sent as text; --json sends the values with their kinds. Another address or a token:
--url / --token, or the variables TOOLBOX_URL / TOOLBOX_TOKEN. The exit code is 0 when it worked, else 1.
"""
import argparse
import json
import os
import sys
from typing import Any

from streamer_toolbox.cli.toolbox_cli import DEFAULT_URL, ToolboxCli


def read_params(pairs: list[str], as_json: str) -> dict[str, Any]:
    """The parameters of `run`: the --json object first, then every name=value on top as text."""
    params = json.loads(as_json) if as_json else {}
    if not isinstance(params, dict):
        raise ValueError("--json must be an object like {\"name\": \"chat\"}")
    for pair in pairs:
        name, equals, value = pair.partition("=")
        if not equals or not name:
            raise ValueError(f"parameters are written name=value, not {pair!r}")
        params[name] = value
    return params


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="toolbox", description="Calls the running toolbox's API.")
    parser.add_argument("--url", default=os.environ.get("TOOLBOX_URL", DEFAULT_URL),
                        help=f"the toolbox's address (default {DEFAULT_URL})")
    parser.add_argument("--token", default=os.environ.get("TOOLBOX_TOKEN", ""),
                        help="a caller's token; without one it is the local caller of this PC")
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="the actions this caller may run")
    listing.add_argument("pattern", nargs="?", default="*", help="e.g. obs.* or scene")
    commands.add_parser("info", help="what one action does and takes").add_argument("action")
    run = commands.add_parser("run", help="run an action")
    run.add_argument("action")
    run.add_argument("params", nargs="*", metavar="name=value", help="parameters, sent as text")
    run.add_argument("--json", default="", help="parameters as a JSON object (values keep their kinds)")
    args = parser.parse_args(arguments)

    cli = ToolboxCli(args.url, args.token)
    if args.command == "list":
        return cli.list(args.pattern)
    if args.command == "info":
        return cli.info(args.action)
    try:
        params = read_params(args.params, args.json)
    except ValueError as e:
        print(e)
        return 1
    return cli.run(args.action, params)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # the Windows console's own encoding can't print every result
    sys.exit(main(sys.argv[1:]))
