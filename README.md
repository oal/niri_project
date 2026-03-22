# niri-project

CLI tool for managing project workspaces in the [Niri](https://github.com/YaLTeR/niri) Wayland compositor. Define per-project configs specifying which apps to launch, how to arrange them, and lifecycle hooks — then start/stop entire workspaces with a single command.

## Features

- Launch multiple apps into a dedicated named workspace
- Arrange windows into columns with configurable widths
- Group windows into tabbed columns
- Lifecycle hooks (pre/post start/stop)
- Per-app window matching by `app_id` and title regex
- Zero external dependencies — Python 3.11+ stdlib only

## Installation

```bash
# With uv (recommended)
uv tool install git+https://github.com/oal/niri_project.git

# Or from a local clone
uv tool install .

# Also works with pipx or pip
pipx install .
pip install .
```

## Quick start

```bash
# Scaffold a new project config
niri-project init myproject

# Edit the generated config
$EDITOR ~/.config/niri-project/projects/myproject.toml

# Start the workspace
niri-project start myproject

# Check running projects
niri-project status

# Stop and close all windows
niri-project stop myproject
```

## Configuration

Project configs live in `~/.config/niri-project/projects/<name>.toml`.

### Example

```toml
[project]
name = "myproject"
directory = "~/Projects/myproject"
output = "DP-2"                              # optional: pin to monitor

pre_start = ["docker", "compose", "up", "-d"]
post_stop = ["docker", "compose", "down"]

[[app]]
command = ["google-chrome", "--profile-directory=MyProject"]
match_app_id = "google-chrome"
width = "60%"

[[app]]
command = ["webstorm", "{directory}/frontend"]
match_app_id = "jetbrains-webstorm"
group = "editors"
width = "40%"

[[app]]
command = ["pycharm", "{directory}/backend"]
match_app_id = "jetbrains-pycharm"
group = "editors"

[[app]]
command = ["ghostty", "--working-directory={directory}"]
match_app_id = "com.mitchellh.ghostty"
width = "30%"
focus = true
```

### `[project]` options

| Field | Type | Description |
|---|---|---|
| `name` | string | Project identifier (must match filename) |
| `directory` | string | Base directory, available as `{directory}` in app commands |
| `output` | string | Monitor name to place workspace on (e.g. `"DP-2"`) |
| `pre_start` | list | Command to run before spawning apps |
| `post_start` | list | Command to run after arrangement |
| `pre_stop` | list | Command to run before closing windows |
| `post_stop` | list | Command to run after all windows are closed |

### `[[app]]` options

| Field | Type | Default | Description |
|---|---|---|---|
| `command` | list | *required* | Command + args. `{directory}` is expanded |
| `match_app_id` | string | *required* | Wayland `app_id` to identify the window (regex) |
| `match_title` | string | | Additional title regex for disambiguation |
| `group` | string | | Windows sharing a group become a tabbed column |
| `width` | string | | Column width: `"50%"`, `"960"` (px), or `"0.5"` |
| `focus` | bool | false | Receive focus after arrangement |
| `fullscreen` | bool | false | Open fullscreen |
| `maximized` | bool | false | Open maximized |
| `floating` | bool | false | Open as floating window |
| `timeout` | int | 30 | Seconds to wait for window to appear |

## Commands

```
niri-project start <name>      Start a project workspace
niri-project stop <name>       Gracefully close all project windows
niri-project restart <name>    Stop then start
niri-project status            Show running projects and window health
niri-project list              List available project configs (* = running)
niri-project init <name>       Scaffold a new config file
```

## Requirements

- [Niri](https://github.com/YaLTeR/niri) compositor (with `niri msg` available on PATH)
- Python 3.11+

## License

MIT
