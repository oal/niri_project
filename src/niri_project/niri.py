"""Thin wrapper around niri msg IPC commands."""

import json
import subprocess
from typing import Any


class NiriError(Exception):
    pass


def _run(args: list[str], check: bool = True) -> str:
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=10
        )
    except FileNotFoundError:
        raise NiriError("'niri' not found on PATH. Is niri installed?")
    except subprocess.TimeoutExpired:
        raise NiriError(f"Command timed out: {' '.join(args)}")

    if check and result.returncode != 0:
        raise NiriError(
            f"niri command failed: {' '.join(args)}\n{result.stderr.strip()}"
        )
    return result.stdout


def run_action(action: str, *args: str) -> str:
    cmd = ["niri", "msg", "action", action, *args]
    return _run(cmd)


def query_json(command: str) -> Any:
    cmd = ["niri", "msg", "--json", command]
    output = _run(cmd)
    return json.loads(output)


def get_windows() -> list[dict]:
    return query_json("windows")


def get_workspaces() -> list[dict]:
    return query_json("workspaces")


def spawn(command: list[str]) -> str:
    return run_action("spawn", "--", *command)


def close_window(window_id: int) -> str:
    return run_action("close-window", "--id", str(window_id))


def focus_window(window_id: int) -> str:
    return run_action("focus-window", "--id", str(window_id))


def focus_workspace(reference: str) -> str:
    return run_action("focus-workspace", reference)


def move_window_to_workspace(
    reference: str, window_id: int | None = None, focus: bool = False
) -> str:
    args = []
    if window_id is not None:
        args.extend(["--window-id", str(window_id)])
    if not focus:
        args.extend(["--focus", "false"])
    args.append(reference)
    return run_action("move-window-to-workspace", *args)


def set_workspace_name(name: str) -> str:
    return run_action("set-workspace-name", name)


def unset_workspace_name(reference: str | None = None) -> str:
    args = [reference] if reference else []
    return run_action("unset-workspace-name", *args)


def consume_window_into_column() -> str:
    return run_action("consume-window-into-column")


def set_column_display(mode: str) -> str:
    return run_action("set-column-display", mode)


def set_column_width(change: str) -> str:
    return run_action("set-column-width", change)


def maximize_column() -> str:
    return run_action("maximize-column")


def fullscreen_window(window_id: int | None = None) -> str:
    args = []
    if window_id is not None:
        args.extend(["--id", str(window_id)])
    return run_action("fullscreen-window", *args)


def move_column_to_index(index: int) -> str:
    return run_action("move-column-to-index", str(index))


def focus_column(index: int) -> str:
    return run_action("focus-column", str(index))


def event_stream() -> subprocess.Popen:
    return subprocess.Popen(
        ["niri", "msg", "--json", "event-stream"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
