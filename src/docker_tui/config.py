"""Validated application configuration with safe defaults.

Config file: ``platformdirs.user_config_path("docker-tui")/config.toml``
(read with stdlib ``tomllib``). Missing files, invalid TOML, invalid single
values, and unknown keys never block startup — defaults apply per-field and
the caller is told what was ignored.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import platformdirs

APP_NAME = "docker-tui"
DEFAULT_ENDPOINT = "unix:///var/run/docker.sock"
DEFAULT_THEME = "dark"
_VALID_THEMES = ("dark", "light")


@dataclass(frozen=True)
class DockerEndpointConfig:
    """Local-only endpoint selection (remote TCP/SSH deferred)."""

    endpoint: str = DEFAULT_ENDPOINT


@dataclass(frozen=True)
class DisplayConfig:
    theme: str = DEFAULT_THEME


@dataclass(frozen=True)
class LoggingConfig:
    debug: bool = False


@dataclass(frozen=True)
class ApplicationConfiguration:
    docker: DockerEndpointConfig = field(default_factory=DockerEndpointConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    ignored: tuple[str, ...] = ()


def default_config_path() -> Path:
    """Return the platform config file path (respects XDG_CONFIG_HOME)."""
    return platformdirs.user_config_path(APP_NAME) / "config.toml"


def load_config(path: Path | None = None) -> ApplicationConfiguration:
    """Load and validate config; fall back per-field on any problem."""
    config_path = path if path is not None else default_config_path()
    try:
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ApplicationConfiguration()
    except OSError as exc:
        return ApplicationConfiguration(ignored=(f"unreadable config file: {exc}",))
    except tomllib.TOMLDecodeError as exc:
        return ApplicationConfiguration(ignored=(f"invalid TOML, using defaults: {exc}",))
    if not isinstance(raw, dict):
        return ApplicationConfiguration(ignored=("config root is not a table",))

    ignored: list[str] = []

    docker_section = raw.get("docker", {})
    if not isinstance(docker_section, dict):
        ignored.append("docker: not a table, using defaults")
        docker_section = {}
    endpoint = docker_section.get("endpoint", DEFAULT_ENDPOINT)
    if not isinstance(endpoint, str) or not endpoint:
        ignored.append("docker.endpoint: must be a non-empty string")
        endpoint = DEFAULT_ENDPOINT
    elif "://" in endpoint and not endpoint.startswith("unix://"):
        # Remote endpoints are out of scope for this release.
        ignored.append(f"docker.endpoint: only unix:// supported ({endpoint})")
        endpoint = DEFAULT_ENDPOINT

    display_section = raw.get("display", {})
    if not isinstance(display_section, dict):
        ignored.append("display: not a table, using defaults")
        display_section = {}
    theme = display_section.get("theme", DEFAULT_THEME)
    if theme not in _VALID_THEMES:
        ignored.append(f"display.theme: must be one of {_VALID_THEMES}")
        theme = DEFAULT_THEME

    logging_section = raw.get("logging", {})
    if not isinstance(logging_section, dict):
        ignored.append("logging: not a table, using defaults")
        logging_section = {}
    debug = logging_section.get("debug", False)
    if not isinstance(debug, bool):
        ignored.append("logging.debug: must be a boolean")
        debug = False

    return ApplicationConfiguration(
        docker=DockerEndpointConfig(endpoint=endpoint),
        display=DisplayConfig(theme=theme),
        logging=LoggingConfig(debug=debug),
        ignored=tuple(ignored),
    )
