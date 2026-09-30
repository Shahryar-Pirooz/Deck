# Deck TUI Manager

Keyboard-first terminal UI for local Docker Engine state. Linux/SSH-friendly;
no mouse required. Can also run as a container to manage sibling containers.

## Install

Requires Python ≥ 3.11.

```sh
pip install -e ".[dev]"
```

## Usage

```sh
Deck            # launch (uses ~/.config/deck/config.toml)
Deck --debug    # extra on-screen diagnostics + full log file
Deck --config PATH  # override config file
```

The status screen shows connection state (`Connected`, `Unavailable`,
`Permission denied`, `Connection failed`) plus Engine version, API version,
OS/architecture, container total/running/stopped, and image count. When Docker
is unreachable the app stays usable with next-step guidance — no tracebacks in
normal mode.

The container list shows sibling containers grouped as running, stopped, or
other (exact status in details). Open a container with `Enter` to inspect it,
act on it (`s` start, `t` stop, `r` restart, `d` remove, `l` logs), and confirm
removal with `y`. Stopping or removing the manager's own container is blocked
with an explanatory message.

## Running as a container

Build a versioned image and run it with the host Engine shared in plus an
interactive terminal:

```sh
docker build -t deck:0.1.0 .
docker run -it --name deck \
  -v /var/run/docker.sock:/var/run/docker.sock \
  deck:0.1.0
```

> **Privilege warning**: sharing Engine access grants the container full control
> of the host. Only run images you trust, preferably with a pinned version tag.

Failure modes: without shared Engine access the app shows `Unavailable` with
guidance naming the run configuration; permission problems report
`Permission denied` distinctly; without an interactive terminal the app reports
the requirement instead of rendering.

## Keyboard

| Key       | Action                                     |
|-----------|--------------------------------------------|
| j / k     | Move down / up                             |
| Enter     | Open selected container                    |
| s / t / r | Start / stop / restart (in details)        |
| d         | Remove — always confirms first (y / n)     |
| l         | View recent logs (in details)              |
| r         | Refresh Docker information                 |
| ?         | Show help                                  |
| Esc       | Close / cancel                             |
| q         | Quit (closes help first)                   |

## Configuration

`~/.config/deck/config.toml` (respects `XDG_CONFIG_HOME`):

```toml
[docker]
endpoint = "unix:///var/run/docker.sock"  # local only; remote deferred

[display]
theme = "dark"  # or "light"

[logging]
debug = false
```

Invalid files or values fall back per-field with a notice; startup never blocks.
Logs (with secrets redacted) go to the platform log directory `deck.log`.

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
