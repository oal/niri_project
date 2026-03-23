"""Workspace setup, window arrangement, and project lifecycle."""

import json
import re
import sys
import time
from datetime import datetime, timezone

from . import niri
from .config import AppConfig, ProjectConfig
from .hooks import run_hook
from .state import is_running, load_state, remove_state, save_state


def _match_window(window: dict, app: AppConfig) -> bool:
    """Check if a window matches an app config."""
    if not re.fullmatch(app.match_app_id, window.get("app_id", "")):
        return False
    if app.match_title:
        title = window.get("title", "")
        if not re.search(app.match_title, title):
            return False
    return True


def _try_match_windows(
    config: ProjectConfig, known_ids: set[int], matched: dict[int, int],
    verbose: bool = False,
) -> None:
    """Check current windows for any new matches."""
    try:
        current_windows = niri.get_windows()
    except niri.NiriError:
        return

    for window in current_windows:
        wid = window["id"]
        if wid in known_ids or wid in matched.values():
            continue
        for i, app in enumerate(config.apps):
            if i in matched:
                continue
            if _match_window(window, app):
                matched[i] = wid
                if verbose:
                    print(f"  Matched window {wid} ({window.get('app_id')}) -> {app.match_app_id}")
                break



def _arrange_windows(config: ProjectConfig, matched: dict[int, int], verbose: bool = False) -> None:
    """Arrange matched windows: ordering, grouping, sizing."""
    if not matched:
        return

    time.sleep(0.3)  # let niri settle

    # Step 1: Move all windows to the project workspace and order them
    for i in sorted(matched.keys()):
        wid = matched[i]
        try:
            niri.focus_window(wid)
            time.sleep(0.1)
            niri.move_column_to_index(i + 1)
            time.sleep(0.1)
        except niri.NiriError as e:
            if verbose:
                print(f"  Warning: could not position window {wid}: {e}", file=sys.stderr)

    time.sleep(0.2)

    # Step 2: Handle groups — consume windows into tabbed columns
    groups: dict[str, list[int]] = {}  # group name -> [app indices in order]
    for i, app in enumerate(config.apps):
        if app.group and i in matched:
            groups.setdefault(app.group, []).append(i)

    consumed_indices: set[int] = set()
    for group_name, indices in groups.items():
        if len(indices) < 2:
            continue
        if verbose:
            print(f"  Grouping '{group_name}': indices {indices}")

        # Windows are already ordered by index from Step 1, so grouped windows
        # are adjacent.  Focus the first window, then consume each neighbor.
        first_wid = matched[indices[0]]
        niri.focus_window(first_wid)
        time.sleep(0.15)

        for idx in indices[1:]:
            niri.consume_window_into_column()
            time.sleep(0.15)
            consumed_indices.add(idx)

        niri.set_column_display("tabbed")
        time.sleep(0.1)

    # Step 3: Set column widths
    for i, app in enumerate(config.apps):
        if i not in matched or i in consumed_indices:
            continue
        if app.width:
            wid = matched[i]
            try:
                niri.focus_window(wid)
                time.sleep(0.1)
                niri.set_column_width(app.width)
                time.sleep(0.1)
            except niri.NiriError as e:
                if verbose:
                    print(f"  Warning: could not set width for window {wid}: {e}", file=sys.stderr)

    # Step 4: Fullscreen / maximized
    for i, app in enumerate(config.apps):
        if i not in matched:
            continue
        wid = matched[i]
        if app.fullscreen:
            niri.fullscreen_window(wid)
            time.sleep(0.1)
        if app.maximized:
            niri.focus_window(wid)
            time.sleep(0.1)
            niri.maximize_column()
            time.sleep(0.1)

    # Step 5: Focus the designated window
    focus_idx = None
    for i, app in enumerate(config.apps):
        if app.focus and i in matched:
            focus_idx = i
            break
    if focus_idx is None and matched:
        focus_idx = min(matched.keys())
    if focus_idx is not None:
        niri.focus_window(matched[focus_idx])


def start_project(config: ProjectConfig, verbose: bool = False) -> None:
    """Start a project: spawn apps, wait for windows, arrange them."""
    if is_running(config.name):
        print(f"Project '{config.name}' is already running. Use 'restart' to re-setup.", file=sys.stderr)
        sys.exit(1)

    # Pre-start hook
    if config.pre_start:
        if not run_hook(config.pre_start, cwd=config.directory):
            print("pre_start hook failed, aborting.", file=sys.stderr)
            sys.exit(1)

    # Snapshot existing window IDs
    existing_windows = niri.get_windows()
    known_ids = {w["id"] for w in existing_windows}

    # Find an empty workspace, or use the last one (niri always has an empty one at the end)
    workspaces = niri.get_workspaces()
    windows = existing_windows
    # Build set of workspace IDs that have windows
    occupied_ws_ids = {w["workspace_id"] for w in windows if w.get("workspace_id")}

    candidates = workspaces
    if config.output:
        output_candidates = [ws for ws in workspaces if ws.get("output") == config.output]
        if output_candidates:
            candidates = output_candidates
        else:
            print(f"Warning: output '{config.output}' not found, using current", file=sys.stderr)

    # Prefer first empty, unnamed workspace; fall back to the last one (always empty in niri)
    empty = [
        ws for ws in candidates
        if ws["id"] not in occupied_ws_ids and not ws.get("name")
    ]
    if empty:
        target = min(empty, key=lambda ws: ws["idx"])
    else:
        target = max(candidates, key=lambda ws: ws["idx"])
    niri.focus_workspace(str(target["idx"]))

    time.sleep(0.2)

    # Name the workspace
    niri.set_workspace_name(config.name)
    time.sleep(0.1)

    # Spawn apps one at a time, waiting for each window before starting the next.
    # This avoids issues with launchers (e.g. JetBrains Toolbox) that can't handle
    # multiple simultaneous spawn requests.
    print(f"Starting project '{config.name}'...")
    matched: dict[int, int] = {}

    max_attempts = 3
    for i, app in enumerate(config.apps):
        for attempt in range(1, max_attempts + 1):
            if attempt > 1 and verbose:
                print(f"  Retry {attempt}/{max_attempts}: {' '.join(app.command)}")
            elif verbose:
                print(f"  Spawning: {' '.join(app.command)}")

            event_proc = niri.event_stream()
            niri.spawn(app.command)

            # Use a short initial timeout; niri spawn failures are instant,
            # successful apps open a window within a few seconds.
            wait = 10 if attempt < max_attempts else app.timeout
            deadline = time.monotonic() + wait
            while i not in matched and time.monotonic() < deadline:
                line = event_proc.stdout.readline()
                if not line:
                    break
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "WindowsChanged" not in event and "WindowOpenedOrChanged" not in event:
                    continue
                _try_match_windows(config, known_ids, matched, verbose=verbose)

            event_proc.terminate()
            event_proc.wait()

            if i in matched:
                break

        if i not in matched and verbose:
            print(f"  Warning: no window appeared for {app.match_app_id}")

    if len(matched) < len(config.apps):
        missing = [
            config.apps[i].match_app_id
            for i in range(len(config.apps))
            if i not in matched
        ]
        print(f"  Warning: some windows didn't appear: {', '.join(missing)}", file=sys.stderr)

    # Move windows to the project workspace
    for i in sorted(matched.keys()):
        wid = matched[i]
        try:
            niri.move_window_to_workspace(config.name, window_id=wid, focus=False)
            time.sleep(0.15)
        except niri.NiriError as e:
            if verbose:
                print(f"  Warning: could not move window {wid}: {e}", file=sys.stderr)

    time.sleep(0.3)

    # Focus the workspace and arrange
    niri.focus_workspace(config.name)
    time.sleep(0.2)
    _arrange_windows(config, matched, verbose=verbose)

    # Save state
    state_data = {
        "project": config.name,
        "workspace_name": config.name,
        "windows": [
            {"app_id": config.apps[i].match_app_id, "window_id": wid}
            for i, wid in sorted(matched.items())
        ],
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    save_state(config.name, state_data)

    print(f"  Project '{config.name}' started with {len(matched)}/{len(config.apps)} windows.")

    # Post-start hook
    if config.post_start:
        run_hook(config.post_start, cwd=config.directory)


def stop_project(project_name: str, verbose: bool = False) -> None:
    """Stop a running project: close windows, clean up state."""
    from .config import load_project

    state = load_state(project_name)
    if state is None:
        print(f"Project '{project_name}' is not running.", file=sys.stderr)
        sys.exit(1)

    # Load config for hooks
    try:
        config = load_project(project_name)
    except FileNotFoundError:
        config = None

    cwd = config.directory if config else None

    # Pre-stop hook
    if config and config.pre_stop:
        run_hook(config.pre_stop, cwd=cwd)

    print(f"Stopping project '{project_name}'...")

    # Close each window
    window_ids = [w["window_id"] for w in state.get("windows", [])]
    for wid in window_ids:
        try:
            niri.close_window(wid)
            if verbose:
                print(f"  Closed window {wid}")
        except niri.NiriError:
            pass  # window may already be gone

    # Wait for windows to close
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        current = niri.get_windows()
        current_ids = {w["id"] for w in current}
        remaining = [wid for wid in window_ids if wid in current_ids]
        if not remaining:
            break
        time.sleep(0.5)
    else:
        current = niri.get_windows()
        current_ids = {w["id"] for w in current}
        remaining = [wid for wid in window_ids if wid in current_ids]
        if remaining:
            print(
                f"  Warning: {len(remaining)} window(s) still open (may have unsaved changes).",
                file=sys.stderr,
            )

    remove_state(project_name)

    # Clean up workspace: unname it so niri auto-removes it if empty
    workspace_name = state.get("workspace_name")
    if workspace_name:
        try:
            workspaces = niri.get_workspaces()
            current_windows = niri.get_windows()
            for ws in workspaces:
                if ws.get("name") == workspace_name:
                    ws_windows = [
                        w for w in current_windows
                        if w.get("workspace_id") == ws["id"]
                    ]
                    if not ws_windows:
                        niri.unset_workspace_name(workspace_name)
                        if verbose:
                            print(f"  Removed workspace '{workspace_name}'")
                    break
        except niri.NiriError:
            pass

    print(f"  Project '{project_name}' stopped.")

    # Post-stop hook
    if config and config.post_stop:
        run_hook(config.post_stop, cwd=cwd)


def status_projects(verbose: bool = False) -> None:
    """Show status of all running projects."""
    from .state import list_running

    running = list_running()
    if not running:
        print("No projects currently running.")
        return

    try:
        current_windows = niri.get_windows()
        current_ids = {w["id"] for w in current_windows}
    except niri.NiriError:
        current_ids = set()

    for name in running:
        state = load_state(name)
        if state is None:
            continue
        windows = state.get("windows", [])
        alive = sum(1 for w in windows if w["window_id"] in current_ids)
        total = len(windows)
        status = "healthy" if alive == total else f"{alive}/{total} alive"
        started = state.get("started_at", "unknown")
        print(f"  {name}: {status} (started {started})")

        if verbose:
            for w in windows:
                wid = w["window_id"]
                marker = "+" if wid in current_ids else "-"
                print(f"    [{marker}] {w['app_id']} (id={wid})")
