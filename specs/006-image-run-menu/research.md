# Research: Image Run Menu Design

## Background Tasks & Modal Overlays (Textual)

Textual supports overlay screens that can capture user input without blocking the main TUI event loop. For the Image Run Menu:

- **Pattern**: An overlay modal screen is presented for the container configuration form. The overlay is modal (captures all key events) but runs on the same event loop, meaning the main TUI remains responsive.
- **Background tasks**: Textual's `await` pattern with `self.run_worker()` or threading can be used for non-blocking Docker operations. The `docker.from_env()` client calls are synchronous, so they must be wrapped in a worker thread or `asyncio.to_thread()` to avoid freezing the TUI.
- **Notification system**: Textual's `Notification` class (from `textual.message`) shows transient messages in the bottom banner. Success/failure of image pull and container creation should use this.

**Decision**: Use a modal overlay screen (`RunConfigScreen`) presented on the Images view selection; background image pull and container creation use `asyncio.to_thread()` or a `Worker` thread; notifications on completion.

## Docker SDK: Container Create + Start

The Docker SDK for Python supports `client.containers.run()` which creates and starts a container in one call, or `client.containers.create()` + `client.containers.start()` in two steps.

For the feature's needs:
- The existing `docker_sdk.py` adapter already has `SdkGateway.start_container()` which calls `client.containers.get(container_id).start()`.
- The adapter has `SdkGateway.list_images()` which reads locally available images (via `client.images.list(all=True)`).
- **Decision**: Use `client.containers.run(image, **kwargs)` where kwargs include `detach=True`, `ports=`, `volumes=`, `environment=`, `networking=`. This is equivalent to `docker run` in one SDK call, creating and starting in detached mode.

**Alternatives considered**:
- Two-step `create()` + `start()` — adds complexity without benefit for the detached-mode use case.
- `client.images.pull()` — the feature uses background pull before run; this research confirmed the SDK API pattern.

## Textual: Modal Overlay Pattern

Textual's overlay pattern works as follows:
- A screen class (e.g., `RunConfigScreen`) is pushed onto the app's screen stack via `app.push_screen(RunConfigScreen())` or `app.set_screen(RunConfigScreen())`.
- The overlay captures all keyboard input until it closes/dismisses.
- The main app receives the result (or cancellation) as a callback or return value.
- The overlay can display form fields, list inputs, and buttons.

**Decision**: Create a `RunConfigScreen` that displays the form fields in a vertical `Container` with `Input` widgets for name, ports, volumes, env vars, and a `List` for network selection. On `Confirm`, validate inputs and emit a result event.

## Data Model: Container Configuration Entity

Based on the feature spec requirements and existing types in `docker_gateway.py`:

| Field | Type | Source |
|---|---|---|
| `name` | `str` | Text input, FR-002 |
| `ports` | `list[PortMapping]` | FR-003; each `PortMapping` = `(host_port: str, container_port: str)` |
| `volumes` | `list[VolumeMount]` | FR-004; each `VolumeMount` = `(source_path: str, destination_path: str)` |
| `network` | `str \| None` | FR-005; Docker network name |
| `env_vars` | `list[EnvVar]` | FR-006; each `EnvVar` = `(key: str, value: str)` |
| `image` | `str` | Selected from Images view |
| `status` | `ContainerStatus` | Running after creation |
| `snapshot_id` | `str` | Container ID from SDK response |

Existing types in `docker_gateway.py`:
- `PortMapping` concept not yet defined — needs to be added.
- `ManagedVolume`, `ManagedNetwork` already exist; reuse where possible.
- `ContainerOperationError` already defined for error mapping.

## Validation Rules (derived from spec)

- Container name cannot be empty or whitespace-only (FR-011; also Edge Case "empty name")
- Port mapping format must be `host_port:container_port` (FR-003; also Edge Case "invalid port syntax")
- Volume format must be `source_path:container_path` (FR-004)
- If name collides with existing container → error + suggest suffixed alternative (clarified in spec)
- If selected image not found locally → background pull; if pull fails → error notification

## Image Pull Handling

The Textual overlay can dispatch the image pull as a background worker:
- `asyncio.to_thread(client.images.pull, image_name)` runs the pull without blocking the event loop.
- A status indicator could be added later, but minimal implementation shows a notification on completion.
- Cancellation: Textual's `worker` can be cancelled; the pull is cooperative-cancellable via `asyncio.Task.cancel()`.

**Output artifacts**:
- research.md complete with decisions/rationale/alternatives
- TODO: Phase 1 generates data-model.md, /contracts/, quickstart.md