# Contract: Container Run Configuration

**Feature**: `004-docker-container-management`

The supported way to run the manager as a container. This is a user-facing
behavioral contract; exact flags live in the run documentation.

## Prerequisites

- Linux host with a running Engine the operator is permitted to share.
- An interactive terminal for the manager container.
- A versioned image tag (never an unpinned floating tag alone).

## Run configuration elements

1. **Shared host Engine access** — the app container sees the host's Engine
   (sibling containers visible). Private in-container Engines are not supported.
2. **Interactive terminal attached** — required; without one the app reports the
   requirement instead of rendering.
3. **Configuration** — same validated TOML semantics as host runs (endpoint,
   display, debug verbosity) with safe defaults; invalid values fall back
   per-field without blocking startup.
4. **Privilege warning** — the run documentation MUST state that shared Engine
   access grants full control of the host.

## Failure modes

| Situation | Displayed behavior |
|-----------|--------------------|
| Engine access not shared in | `unavailable` status + guidance naming the run configuration |
| Permission denied from inside | `permission-denied` status distinct from generic failure + next steps |
| No interactive terminal | Message stating an interactive terminal is required |
| Invalid config values | Defaults apply per-field; user informed what was ignored |

## Non-goals

Multi-host orchestration, registry management, image building.
