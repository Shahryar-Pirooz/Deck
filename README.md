# Deck

> A keyboard-first TUI for managing Docker from the terminal.

**Deck** is a terminal user interface (TUI) for managing a local Docker Engine from Linux and SSH terminals.

It is designed around a simple idea:

> Docker management should be fast, keyboard-driven, and comfortable for people who live in the terminal.

Deck can run directly on Linux or, preferably, inside a small Docker container with access to the host Docker socket.

---

## ⚠️ Project Status

Deck is an **experimental / early-stage project**.

It is functional, but it should not currently be considered a production-grade Docker management tool.

Expect:

- incomplete Docker functionality
- changing UI and architecture
- bugs
- missing edge cases
- incomplete test coverage
- breaking changes

If you find a problem, please open an issue or contribute a fix.

---

# ✨ Features

## Terminal-first UI

Deck is designed specifically for the terminal rather than being a web dashboard.

The interface is:

- keyboard driven
- compact
- Vim-friendly
- usable over SSH
- designed for quick Docker operations

## Vim-style navigation

The primary navigation shortcuts are:

| Key     | Action                  |
| ------- | ----------------------- |
| `j`     | Move down               |
| `k`     | Move up                 |
| `↑`     | Move down               |
| `↓`     | Move up                 |
| `1`-`4` | Containers / Images / Volumes / Networks |
| `Enter` | Open selected resource |
| `r`     | Refresh                 |
| `q`     | Quit                    |
| `Esc`   | Close modal             |
| `?`     | Show help               |

Container actions are available from the container details view.

---

# 🐳 Docker Management

Deck communicates with the Docker Engine through the Docker SDK.

The current implementation provides:

- Docker Engine connection status
- Docker Engine version
- Docker API version
- host operating system
- host architecture
- total container count
- running container count
- stopped container count
- image count
- container listing
- container status
- container details
- container logs
- start container
- stop container
- restart container
- remove container
- run a new container from an image (name, ports, volumes, network, env)

The architecture is intentionally separated so that Docker-specific code is isolated from the TUI.

```text
┌─────────────────────┐
│        TUI          │
│      Textual        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│      Services       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Docker Gateway    │
│     Protocol        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    Docker SDK       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    Docker Engine    │
└─────────────────────┘
```

Only the Docker SDK adapter directly communicates with the Docker Python package. This keeps the application layer easier to test without requiring a live Docker daemon.

## 🚀 Image Run Menu

From the **Images** view, press `Enter` on a selected image to open the run configuration menu. The menu collects everything a container needs to start:

| Field | Format | Required |
|---|---|---|
| Name | any unique container name | yes |
| Ports | `host:container` entries (e.g. `8080:80`, `127.0.0.1:9000:9000`) | no |
| Volumes | `source:destination` entries (e.g. `/data:/app/data`) | no |
| Network | existing network name; empty uses the default bridge | no |
| Environment | `KEY=value` entries (e.g. `DEBUG=true`) | no |

**Keyboard shortcuts (inside the menu)**:

- `n` / `Space`: add a list entry (ports, volumes, env) — type the value and press `Enter`
- `d`: remove the selected list entry · `e`: edit it · `j`/`k`: move the selection
- `Tab`: move between fields · `Tab` to **Review & Start**, press `Enter`: open the confirmation review
- `y` / `Enter` on the review: create and start the container (detached)
- `n` / `Esc` on the review: back to the form · `Esc` on the form: cancel without creating anything

**Failure modes**:

- Duplicate name → error with a numeric-suffix suggestion (e.g. `myapp-2`), form stays open
- Invalid port/volume/env format → the entry is rejected with the expected format shown
- Unknown network name → rejected with a hint to check the name or use the default bridge
- Image not available locally → the image is pulled in the background (the TUI stays responsive); success or failure is shown as a notification
- Docker daemon unavailable → actionable error, nothing is created

**Security note**: environment variable values are shown in full on the confirmation review so you can verify them before committing; they are never written to logs (sensitive keys are redacted).

---

# 🐋 Running with Docker

Docker is the recommended way to run Deck.

## Requirements

You need:

- Linux
- Docker Engine
- Docker Compose v2
- an interactive terminal

Make sure Docker is running:

```bash
docker info
```

---

## Build

Clone the repository and enter the project directory:

```bash
git clone <repository-url>
cd Deck
```

Build the image:

```bash
docker compose build
```

---

## Run

Start Deck:

```bash
docker compose run --rm deck
```

Deck should open directly inside your terminal.

---

## Using plain Docker

You can also build and run Deck without Compose.

Build:

```bash
docker build -t deck:latest .
```

Run:

```bash
docker run --rm -it \
  -e DOCKER_TUI_CONTAINER=1 \
  -e TERM=xterm-256color \
  -v /var/run/docker.sock:/var/run/docker.sock \
  deck:latest
```

---

# 🔐 Docker Socket Security

Deck needs access to the Docker socket to manage the host Docker Engine.

The Docker Compose configuration therefore mounts:

```text
/var/run/docker.sock
```

into the Deck container.

This is a significant security consideration.

Access to the Docker socket can effectively provide root-level control over the Docker host.

**Do not run an untrusted Deck image with access to your Docker socket.**

The Docker image isolates the application filesystem, but it does **not** provide a security boundary around the Docker Engine itself.

---

# 💻 Running Without Docker

Docker is recommended, but Deck can also run directly on Linux.

Requirements:

- Python 3.11+
- Docker Engine
- access to the Docker socket

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install the project:

```bash
python -m pip install -e '.[dev]'
```

Run:

```bash
deck
```

Or:

```bash
python -m deck.cli
```

---

# ⚙️ Configuration

Deck uses a TOML configuration file.

Default location:

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

If the configuration file does not exist, Deck uses its default configuration.

Invalid configuration does not intentionally prevent startup; Deck falls back to safe defaults and reports the configuration problem.

---

# 🏗️ Project Structure

```text
Deck/
├── src/
│   └── docker_tui/
│       ├── cli.py
│       ├── config.py
│       ├── docker_gateway.py
│       ├── docker_sdk.py
│       ├── logging_setup.py
│       ├── services.py
│       │
│       └── tui/
│           ├── app.py
│           ├── screens.py
│           └── widgets.py
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── specs/
│   └── ...
│
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── LICENSE
└── README.md
```

## Main components

### `cli.py`

Application entry point.

Responsible for:

- argument parsing
- configuration loading
- logging initialization
- Docker gateway creation
- starting the Textual application

### `config.py`

Handles application configuration and default values.

### `docker_gateway.py`

Defines the application's Docker abstraction.

The TUI does not need to know how the Docker SDK works internally.

### `docker_sdk.py`

Concrete Docker SDK implementation.

This is the main boundary between Deck and the Docker Python SDK.

### `services.py`

Application-level Docker operations.

This layer sits between the UI and Docker gateway.

### `tui/`

Contains the Textual application, screens, widgets, and presentation logic.

---

# 🧪 Testing

The project contains both unit and integration tests.

Run the test suite:

```bash
pytest -q
```

Run static checks:

```bash
ruff check .
```

Check formatting:

```bash
ruff format --check .
```

Run type checking:

```bash
mypy src
```

Integration tests require access to a working Docker Engine.

---

# 🧰 Technology Stack

Deck currently uses:

- **Python 3.11+**
- **Textual** — terminal UI framework
- **Docker SDK for Python** — Docker Engine communication
- **platformdirs** — platform-appropriate configuration directories
- **pytest** — testing
- **Ruff** — linting and formatting
- **mypy** — static type checking
- **Docker**
- **Docker Compose**

---

# 🤖 Vibe Coding

## This project was vibe coded

Deck is intentionally an example of **vibe coding**.

A significant part of this project was created through interaction with AI coding agents rather than by manually writing every part of the implementation.

The development process looks roughly like this:

```text
Idea
  │
  ▼
Natural-language specification
  │
  ▼
AI coding agent
  │
  ▼
Generated implementation
  │
  ▼
Run the application
  │
  ▼
Find errors / unexpected behavior
  │
  ▼
Describe the problem to the agent
  │
  ▼
AI modifies the project
  │
  └───────────────► repeat
```

The project is therefore intentionally transparent about its development methodology.

### Why mention this?

Because Deck is also an experiment in how far this workflow can take a real software project.

Instead of pretending that every line was manually designed and typed, this repository documents the fact that AI was heavily involved in:

- project architecture
- implementation
- UI development
- debugging
- refactoring
- test creation
- Docker configuration
- documentation

The human role is primarily to define the desired behavior, provide constraints, evaluate results, run the software, identify failures, and direct subsequent changes.

---

## Vibe coding does not mean "the code is automatically good"

AI-generated software can contain:

- incorrect assumptions
- bugs
- unnecessary complexity
- API misuse
- security problems
- incomplete error handling
- compatibility problems

Deck itself demonstrates this.

For example, parts of the project have required correction after generated code interacted incorrectly with the installed version of Textual.

That is an intentional part of the experiment.

The fact that an AI-generated project runs is not proof that its implementation is correct.

**Run it. Break it. Test it. Review it. Improve it.**

---

# 🎯 Project Goals

The long-term goal is to make Deck a practical terminal-based Docker manager.

Potential future areas include:

- container management
- image management
- volume management
- network management
- Compose management
- container statistics
- resource monitoring
- logs
- shell access
- inspect views
- image pulling
- image removal
- volume operations
- network operations
- Docker Compose project management
- configurable keyboard shortcuts
- themes
- better filtering and searching
- Docker event monitoring

Not all of these features currently exist.

The project roadmap will evolve as development continues.

---

# 🧭 Design Principles

Deck follows several principles.

### Terminal first

The terminal is not a fallback interface.

It is the primary interface.

### Keyboard first

Common operations should not require a mouse.

### Vim friendly

Navigation should feel natural to users familiar with Vim-style controls.

### Docker-native

Deck should expose Docker functionality without unnecessarily hiding Docker's concepts.

### Small dependencies

The project should avoid unnecessary dependencies and abstractions.

### Testable architecture

Docker communication should be separated from presentation logic.

### Experimental by design

The project is also an experiment in AI-assisted software development.

---

# 📜 License

Deck is released under the **MIT License**.

Copyright © 2026 Shahryar Pirooz.

See [`LICENSE`](LICENSE) for the complete license text.

---

# 🤝 Contributing

Contributions are welcome.

Before submitting a pull request:

1. Explain what you are changing.
2. Keep changes focused.
3. Add or update tests where appropriate.
4. Run the test suite.
5. Run Ruff.
6. Run mypy where applicable.
7. Test Docker-related changes against a real Docker Engine.

For larger features, consider adding or updating the relevant specification under:

```text
specs/
```

---

# ⚠️ Disclaimer

Deck is experimental software.

Use it at your own risk, particularly when granting it access to the Docker socket.

The authors are not responsible for:

- deleted containers
- deleted images
- deleted volumes
- Docker host changes
- data loss
- security incidents
- damage caused by incorrect Docker operations

Always understand what a Docker operation does before executing it.
