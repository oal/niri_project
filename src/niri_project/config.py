"""TOML config loading, validation, and placeholder expansion."""

import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


def get_config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "niri-project" / "projects"


@dataclass
class AppConfig:
    command: list[str]
    match_app_id: str
    match_title: str | None = None
    group: str | None = None
    width: str | None = None
    focus: bool = False
    fullscreen: bool = False
    maximized: bool = False
    floating: bool = False
    timeout: int = 30


@dataclass
class ProjectConfig:
    name: str
    directory: str | None = None
    output: str | None = None
    pre_start: list[str] = field(default_factory=list)
    post_start: list[str] = field(default_factory=list)
    pre_stop: list[str] = field(default_factory=list)
    post_stop: list[str] = field(default_factory=list)
    apps: list[AppConfig] = field(default_factory=list)


def expand_placeholders(value: str, directory: str | None) -> str:
    if directory and "{directory}" in value:
        return value.replace("{directory}", directory)
    return value


def _expand_list(lst: list[str], directory: str | None) -> list[str]:
    return [expand_placeholders(v, directory) for v in lst]


def load_project(name: str, config_dir: Path | None = None) -> ProjectConfig:
    d = config_dir or get_config_dir()
    path = d / f"{name}.toml"
    if not path.exists():
        available = list_projects(d)
        avail_str = ", ".join(available) if available else "(none)"
        raise FileNotFoundError(
            f"Project '{name}' not found at {path}. Available: {avail_str}"
        )

    with open(path, "rb") as f:
        data = tomllib.load(f)

    proj = data.get("project", {})
    if not proj.get("name"):
        raise ValueError(f"Project config {path} missing [project].name")

    directory = proj.get("directory")
    if directory:
        directory = os.path.expanduser(directory)

    config = ProjectConfig(
        name=proj["name"],
        directory=directory,
        output=proj.get("output"),
        pre_start=_expand_list(proj.get("pre_start", []), directory),
        post_start=_expand_list(proj.get("post_start", []), directory),
        pre_stop=_expand_list(proj.get("pre_stop", []), directory),
        post_stop=_expand_list(proj.get("post_stop", []), directory),
    )

    for app_data in data.get("app", []):
        if "command" not in app_data:
            raise ValueError(f"App entry missing 'command' in {path}")
        if "match_app_id" not in app_data:
            raise ValueError(f"App entry missing 'match_app_id' in {path}")

        command = _expand_list(app_data["command"], directory)
        app = AppConfig(
            command=command,
            match_app_id=app_data["match_app_id"],
            match_title=app_data.get("match_title"),
            group=app_data.get("group"),
            width=app_data.get("width"),
            focus=app_data.get("focus", False),
            fullscreen=app_data.get("fullscreen", False),
            maximized=app_data.get("maximized", False),
            floating=app_data.get("floating", False),
            timeout=app_data.get("timeout", 30),
        )
        config.apps.append(app)

    return config


def list_projects(config_dir: Path | None = None) -> list[str]:
    d = config_dir or get_config_dir()
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.toml"))
