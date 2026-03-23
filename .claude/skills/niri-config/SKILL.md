---
name: niri-config
description: Generate a niri-project workspace config. Use when the user wants to create or set up a new niri project config, or asks which apps to include in a workspace.
argument-hint: <project-name> [apps...]
allowed-tools: Read, Write, Bash, Grep, Glob
---

Generate a niri-project TOML config file based on the user's description.

The user will provide a project name (first argument) and describe which applications they want. Use the remaining arguments and conversation context to determine the apps.

## Config location

Save the config to `~/.config/niri-project/projects/$0.toml`. Create the directory if it doesn't exist.

## Config format

```toml
[project]
name = "<project-name>"
# directory = "~/Projects/<project-name>"
# output = "DP-2"

# pre_start = ["echo", "starting"]
# post_stop = ["echo", "stopped"]

[[app]]
command = ["<app-command>"]
match_app_id = "<wayland-app-id>"
# width = "50%"
# focus = true
```

## Rules

1. **Ask if unclear.** If the user just says app names without detail, use sensible defaults but confirm before saving.
2. **Set `focus = true`** on the terminal app if one is included, otherwise on the first app.
3. **Use `{directory}` placeholder** in commands where a working directory makes sense (terminals, editors). Only include `directory` in `[project]` if apps reference it.
4. **Group related apps.** If multiple editors or browser tabs are specified, use `group` to put them in a tabbed column.
5. **Assign reasonable widths.** Editors/IDEs ~50-60%, terminals ~30-40%, browsers ~50-60%. Widths across columns should roughly sum to 100%.
6. **Comment out optional fields** (`directory`, `output`, hooks) with a sensible placeholder so the user can easily uncomment them.

## Common app IDs

Use these known Wayland `app_id` values:

| App | Command | `match_app_id` |
|-----|---------|-----------------|
| Ghostty | `ghostty` | `com.mitchellh.ghostty` |
| Alacritty | `alacritty` | `Alacritty` |
| kitty | `kitty` | `kitty` |
| foot | `foot` | `foot` |
| WezTerm | `wezterm` | `org.wezfurlong.wezterm` |
| Firefox | `firefox` | `firefox` |
| Google Chrome | `google-chrome` | `google-chrome` |
| Chromium | `chromium` | `chromium-browser` |
| VS Code | `code` | `code` |
| Zed | `zed` | `dev.zed.Zed` |
| WebStorm | `webstorm` | `jetbrains-webstorm` |
| PyCharm | `pycharm` | `jetbrains-pycharm` |
| IntelliJ IDEA | `idea` | `jetbrains-idea` |
| CLion | `clion` | `jetbrains-clion` |
| GoLand | `goland` | `jetbrains-goland` |
| RustRover | `rustrover` | `jetbrains-rustrover` |
| Nautilus | `nautilus` | `org.gnome.Nautilus` |
| Thunar | `thunar` | `thunar` |
| Slack | `slack` | `Slack` |
| Discord | `discord` | `discord` |
| Obsidian | `obsidian` | `obsidian` |
| Spotify | `spotify` | `spotify` |

If an app is not in this list, make a best guess for the `app_id` and add a comment noting the user should verify it: `# verify this app_id with: niri msg --json windows`.

## After saving

After writing the file, tell the user:
- The path where the config was saved
- How to start it: `niri-project start <name>`
- Suggest they review and tweak widths/options as needed
