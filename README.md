# Deck

Deck is a keyboard-first TUI for managing a local Docker Engine from Linux and SSH terminals.
It can run directly on the host or, preferably, as a small Docker container with the host Docker
socket mounted into it.

## Docker — recommended

Requirements:

- Docker Engine running on the host
- Docker Compose v2 (for the compose workflow)
- An interactive terminal

Build the image:

```sh
docker compose build
```

Start Deck:

```sh
docker compose run --rm deck
```

The compose configuration mounts `/var/run/docker.sock` and allocates a real TTY, so Deck can
control the host Docker Engine while its application filesystem stays isolated in the container.

You can also use plain Docker:

```sh
docker build -t deck:latest .
docker run --rm -it \
  -e DECK_CONTAINER=1 \
  -e TERM=xterm-256color \
  -v /var/run/docker.sock:/var/run/docker.sock \
  deck:latest
```

> **Security:** access to `/var/run/docker.sock` is effectively root-equivalent control over the
> Docker host. Only run an image you trust.

## TUI controls

| Key       | Action                              |
| --------- | ----------------------------------- |
| `j` / `k` | Move down / up                      |
| `↑` / `↓` | Move down / up                      |
| `Enter`   | Open selected container             |
| `r`       | Refresh Docker state                |
| `s`       | Start container in details          |
| `t`       | Stop container in details           |
| `r`       | Restart container in details        |
| `d`       | Remove container, with confirmation |
| `l`       | Show recent logs                    |
| `?`       | Help                                |
| `Esc`     | Close modal                         |
| `q`       | Quit                                |

The dashboard shows Docker connection state, Engine version/API, host OS/architecture, container
counts, image count, and a selectable container list. Container operations run in background workers
so Docker calls do not block the TUI render loop.

## Host installation

Python 3.11+ is supported:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
deck
```

## Configuration

Default config:

```text
~/.config/Deck/config.toml
```

Example:

```toml
[docker]
endpoint = "unix:///var/run/docker.sock"

[display]
theme = "dark"

[logging]
debug = false
```

The application falls back to safe defaults when the config is missing or invalid.

## Development checks

```sh
pytest -q
ruff check .
ruff format --check .
mypy src
```

Integration tests require a reachable Docker Engine.

## Architecture

```text
TUI → services → DockerGateway → Docker SDK → Docker Engine
```

Only `src/deck/docker_sdk.py` imports the Docker SDK. The TUI depends on the gateway protocol,
which keeps the interface testable without a live Docker daemon.
