# Data Model: Image Run Menu

## Entities

### Container Configuration (created per run)

| Field | Type | Required | Validation |
|---|---|---|---|
| `name` | `str` | Yes | Non-empty, non-whitespace-only; unique (no running container with same name) |
| `image` | `str` | Yes | Must be locally available (or pull in background) |
| `ports` | `list[PortMapping]` | No | Each entry `host_port:container_port` (e.g., "8080:80") |
| `volumes` | `list[VolumeMount]` | No | Each entry `source_path:container_path` |
| `network` | `str | None` | No | Must match an existing network name, or empty (default bridge) |
| `env_vars` | `list[EnvVar]` | No | Each entry `KEY=value` |
| `detach` | `bool` | Implicit `True` | Always detached (background) |

### Port Mapping

| Field | Type |
|---|---|
| `host_port` | `str` |
| `container_port` | `str` |

### Volume Mount

| Field | Type |
|---|---|
| `source_path` | `str` |
| `container_path` | `str` |

### Environment Variable

| Field | Type |
|---|---|
| `key` | `str` |
| `value` | `str` |

## Relationships

- **Container Configuration** references one **Image** (selected from Images view).
- **Container Configuration** has zero-or-more **Port Mappings**, **Volume Mounts**, and **Env Vars**.
- **Container Configuration** optionally references one **Network** (by name).

## State Transitions

1. `form_open` → user fills configuration (name, ports, volumes, network, env vars)
2. `confirmation_shown` → review screen shows all inputs
3. `container_created` → Docker API `containers.run(image, detach=True, ...)` call
4. `container_running` → container appears in Containers view
5. `error` → notification shown; form remains open for retry

## Constraints (from spec & constitution)

- Name uniqueness: rejected if collides with existing container; suggest `name-<num>` alternative (FR-011, Clarifications).
- Image availability: only local images displayed in Images view; missing image triggers background pull (Clarifications).
- Confirmation required before execution (Constitution §III).
- Keyboard-only navigation for all fields (Constitution §IV).
- No TUI event loop blocking (Constitution §V); image pull runs in background.
- Simple operations stay simple: single "Run" action (Constitution §VI).