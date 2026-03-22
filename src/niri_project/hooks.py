"""Pre/post lifecycle hook execution."""

import subprocess
import sys


def run_hook(command: list[str], cwd: str | None = None) -> bool:
    """Run a hook command. Returns True on success."""
    cmd_str = " ".join(command)
    print(f"  Running hook: {cmd_str}")
    try:
        result = subprocess.run(
            command, cwd=cwd, timeout=120,
        )
        if result.returncode != 0:
            print(f"  Hook failed (exit {result.returncode}): {cmd_str}", file=sys.stderr)
            return False
        return True
    except FileNotFoundError:
        print(f"  Hook command not found: {command[0]}", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print(f"  Hook timed out: {cmd_str}", file=sys.stderr)
        return False
