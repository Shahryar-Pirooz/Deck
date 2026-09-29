# Docker TUI Manager

Keyboard-first terminal UI for local Docker Engine state. Linux/SSH-friendly;
no mouse required.

## Install

Requires Python ≥ 3.11.

```sh
pip install -e ".[dev]"
```

## Usage

```sh
docker-tui            # launch (uses ~/.config/docker-tui/config.toml)
docker-tui --debug    # extra on-screen diagnostics + full log file
docker-tui --config PATH  # override config file
```

The status screen shows connection state (`Connected`, `Unavailable`,
`Permission denied`, `Connection failed`) plus Engine version, API version,
OS/architecture, container total/running/stopped, and image count. When Docker
is unreachable the app stays usable with next-step guidance — no tracebacks in
normal mode.

## Keyboard

| Key   | Action                          |
|-------|---------------------------------|
| j / k | Move down / up                  |
| r     | Refresh Docker information      |
| ?     | Show help                       |
| Esc   | Close / cancel                  |
| q     | Quit (closes help first)        |

## Configuration

`~/.config/docker-tui/config.toml` (respects `XDG_CONFIG_HOME`):

```toml
[docker]
endpoint = "unix:///var/run/docker.sock"  # local only; remote deferred

[display]
theme = "dark"  # or "light"

[logging]
debug = false
```

Invalid files or values fall back per-field with a notice; startup never blocks.
Logs (with secrets redacted) go to the platform log directory `docker-tui.log`.

## Development

```sh
pytest tests/unit -q
pytest -m "not integration" -q
pytest -m integration -q        # needs a live daemon, skipped otherwise
ruff check . && ruff format --check .
mypy src
```

Architecture: `TUI → services → DockerGateway → Docker Engine`. Only
`src/docker_tui/docker_sdk.py` imports the Docker SDK.
