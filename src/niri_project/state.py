"""Runtime state tracking for running projects."""

import json
import os
from pathlib import Path

from . import niri


def get_state_dir() -> Path:
    xdg = os.environ.get("XDG_STATE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "state"
    return base / "niri-project"


def save_state(project_name: str, state_data: dict) -> None:
    d = get_state_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{project_name}.json"
    with open(path, "w") as f:
        json.dump(state_data, f, indent=2)


def load_state(project_name: str) -> dict | None:
    path = get_state_dir() / f"{project_name}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def remove_state(project_name: str) -> None:
    path = get_state_dir() / f"{project_name}.json"
    if path.exists():
        path.unlink()


def list_running() -> list[str]:
    d = get_state_dir()
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.json"))


def is_running(project_name: str) -> bool:
    state = load_state(project_name)
    if state is None:
        return False
    # Verify at least one window is still alive
    try:
        current_windows = niri.get_windows()
        current_ids = {w["id"] for w in current_windows}
        for w in state.get("windows", []):
            if w["window_id"] in current_ids:
                return True
    except niri.NiriError:
        pass
    # All windows gone — clean up stale state
    remove_state(project_name)
    return False
