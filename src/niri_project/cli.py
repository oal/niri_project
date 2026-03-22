"""CLI entry point for niri-project."""

import argparse
import os
import sys
from pathlib import Path

from .config import get_config_dir, list_projects, load_project
from .state import is_running, list_running
from .workspace import start_project, status_projects, stop_project


SCAFFOLD_TEMPLATE = """\
[project]
name = "{name}"
# directory = "/home/user/Projects/{name}"
# output = "DP-2"

# pre_start = ["echo", "starting"]
# post_stop = ["echo", "stopped"]

[[app]]
command = ["ghostty"]
match_app_id = "com.mitchellh.ghostty"
# width = "50%"
# focus = true
"""


def cmd_start(args: argparse.Namespace) -> None:
    config = load_project(args.name, config_dir=args.config_dir)
    start_project(config, verbose=args.verbose)


def cmd_stop(args: argparse.Namespace) -> None:
    stop_project(args.name, verbose=args.verbose)


def cmd_restart(args: argparse.Namespace) -> None:
    if is_running(args.name):
        stop_project(args.name, verbose=args.verbose)
        import time
        time.sleep(1)
    config = load_project(args.name, config_dir=args.config_dir)
    start_project(config, verbose=args.verbose)


def cmd_status(args: argparse.Namespace) -> None:
    status_projects(verbose=args.verbose)


def cmd_list(args: argparse.Namespace) -> None:
    available = list_projects(config_dir=args.config_dir)
    running = list_running()
    if not available:
        config_dir = args.config_dir or get_config_dir()
        print(f"No project configs found in {config_dir}")
        return
    for name in available:
        marker = " *" if name in running else ""
        print(f"  {name}{marker}")
    if running:
        print("\n  * = currently running")


def cmd_init(args: argparse.Namespace) -> None:
    config_dir = args.config_dir or get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / f"{args.name}.toml"
    if path.exists():
        print(f"Config already exists: {path}", file=sys.stderr)
        sys.exit(1)
    path.write_text(SCAFFOLD_TEMPLATE.format(name=args.name))
    print(f"Created {path}")


def main() -> None:
    # Shared flags available on all subcommands
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--verbose", "-v", action="store_true", help="verbose output")
    common.add_argument(
        "--config-dir", type=Path, default=None,
        help="override config directory",
    )

    parser = argparse.ArgumentParser(
        prog="niri-project",
        description="Manage project workspaces in the Niri compositor",
        parents=[common],
    )

    sub = parser.add_subparsers(dest="command")

    p_start = sub.add_parser("start", help="start a project", parents=[common])
    p_start.add_argument("name")
    p_start.set_defaults(func=cmd_start)

    p_stop = sub.add_parser("stop", help="stop a project", parents=[common])
    p_stop.add_argument("name")
    p_stop.set_defaults(func=cmd_stop)

    p_restart = sub.add_parser("restart", help="restart a project", parents=[common])
    p_restart.add_argument("name")
    p_restart.set_defaults(func=cmd_restart)

    p_status = sub.add_parser("status", help="show running projects", parents=[common])
    p_status.set_defaults(func=cmd_status)

    p_list = sub.add_parser("list", help="list available project configs", parents=[common])
    p_list.set_defaults(func=cmd_list)

    p_init = sub.add_parser("init", help="scaffold a new project config", parents=[common])
    p_init.add_argument("name")
    p_init.set_defaults(func=cmd_init)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
