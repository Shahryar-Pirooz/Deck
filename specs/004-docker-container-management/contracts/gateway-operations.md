# Contract: Gateway Container Operations

**Feature**: `004-docker-container-management`

Extension of the `DockerGateway` protocol boundary (implemented only in
`docker_sdk.py`; TUI/services never touch Engine details directly).

## Operations

| Operation | Input | Output | Rules |
|-----------|-------|--------|-------|
| `list_containers` | refresh trigger | `ManagedContainer[]` (≤100, one query per refresh) | Sorted stable; includes self row flagged `is_self` |
| `start_container` | container id | updated row | No-op with message if already running |
| `stop_container` | container id | updated row | Graceful; blocked with message when `is_self` |
| `restart_container` | container id | updated row | Blocked with message when `is_self` |
| `remove_container` | container id + explicit confirmation | row removed | Confirmation required; blocked with message when `is_self` |
| `container_details` | container id | details record (name, image, bucket + exact status) | Read-only |
| `container_logs` | container id | bounded log tail | Loading state while fetching; never unbounded |

## Error mapping

All failures map to the four connection states with actionable messages
(what / which operation / likely why / next step); no raw tracebacks in normal
mode; full detail preserved for debug mode and the log file.

## Invariants

- Every operation re-queries the Engine; no persistent app-side container state.
- `remove_container` without confirmation never executes.
- `is_self` rows never transition via stop/restart/remove from inside the tool.
