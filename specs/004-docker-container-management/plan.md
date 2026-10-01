# Implementation Plan: Docker Container Management

**Branch**: `004-docker-container-management` | **Date**: 2026-09-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-docker-container-management/spec.md`

## Summary

Ship the terminal manager as a runnable container image that connects to the single
shared host Engine and manages sibling containers (list, start/stop/restart with
confirmation-gated remove, details/logs), reusing the existing
TUI → services → DockerGateway → Engine layering. Approach per research: share host
Engine access into the app container (no private Engine), extend the gateway protocol
with container operations implemented only in `docker_sdk.py`, add a container list
screen with Vim-consistent bindings, block self stop/remove, and group states as
running/stopped/other for up to 100 siblings.

## Technical Context

**Language/Version**: Python ≥3.11 (pinned minimum in `pyproject.toml`; codebase uses
3.11 idioms: `StrEnum`, `datetime.UTC`, `X | None`)

**Primary Dependencies**: `textual~=8.2` (TUI), `docker==7.2.0` (Engine SDK, imported
only in `src/deck/docker_sdk.py`), `platformdirs>=4.3` (config paths). No new
runtime dependencies planned.

**Storage**: N/A — no app persistence. Docker Engine is the source of truth (queried
per refresh); configuration is a read-only TOML file with per-field defaults.

**Testing**: `pytest` (asyncio auto mode, `--cov-fail-under=80`); `tests/unit` runnable
without a daemon via a fake gateway; `tests/integration` (marked) against a live
daemon; `ruff check` + `ruff format --check`; `mypy` strict.

**Target Platform**: Linux host Engine; app runs either directly on the host or inside
a Linux container with an interactive terminal attached (80x24 minimum, SSH-friendly).

**Project Type**: Terminal TUI application plus a shippable container image definition
for that same application.

**Performance Goals**: Startup-to-status under 10s; log view opens under 10s (SC-004);
keypresses acknowledged within 1s; container list navigable at 100 siblings with one
list query per manual refresh.

**Constraints**: TUI must never block rendering on Engine calls (existing worker-thread
pattern in `tui/app.py`); SDK imports isolated to `docker_sdk.py`; strict typing and
lint must pass; local single Engine only (remote TCP/SSH deferred); destructive
actions confirmed; self stop/remove blocked.

**Scale/Scope**: Single host, single interactive user, up to 100 sibling containers.

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

- [x] **I. Docker is source of truth** — list/details/logs re-queried per refresh;
      no cached persistent container state.before
- [x] **II. Layered interface** — new operations exposed as application commands /
      services; TUI calls services, services call `DockerGateway` protocol, only
      `docker_sdk.py` touches the SDK.
- [x] **III. Safety over convenience (NON-NEGOTIABLE)** — remove requires explicit
      confirmation (FR-006); self stop/remove blocked with message (FR-007); run
      documentation warns shared Engine access grants full host control (FR-002).
- [x] **IV. Keyboard first (NON-NEGOTIABLE)** — all new actions keyboard-reachable;
      new bindings follow the Vim baseline (`Enter` open/select, `r` refresh, `?` help,
      `Esc` cancel, `q` quit); new keys documented and tested.
- [x] **V. TUI first** — same Textual app inside the container; interactive terminal
      required and reported when absent; no graphical dependency.
- [x] **VI. Simple ops stay simple** — start/stop/restart/logs reachable with minimal
      interaction from the list.
- [x] **Adapter isolation** — gateway protocol extended; no SDK types leak past
      `docker_sdk.py`.
- [x] **Security** — permission problems detected and reported; no secrets logged
      (endpoint labels only); privileged run configuration documented with warning.
- [x] **Error handling** — actionable messages (what/which/why/next), no raw
      tracebacks in normal mode, debug detail preserved.
- [x] **Testing** — unit tests via fake gateway (no daemon); live-daemon integration
      tests marked; TUI keybinding tests for new actions.
- [x] **Performance** — worker-thread queries, single list call per refresh, lazy
      log fetching.
- [x] **Dependencies** — no new runtime dependencies; image base is build packaging,
      not an app dependency.
- [x] **Documentation** — run configuration, shortcuts, failure modes, and security
      implications documented (quickstart + contracts).

_Post-design re-check (after Phase 1): no new violations introduced — data model keeps
Engine-query semantics, contracts preserve the adapter boundary, quickstart validates
safety gates end to end._

## Project Structure

### Documentation (this feature)

```text
specs/004-docker-container-management/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/deck/
├── cli.py            # entry point; builds SdkGateway from config
├── config.py         # validated TOML config (endpoint/display/debug)
├── docker_gateway.py # DockerGateway protocol + snapshot/summary types (extend here)
├── docker_sdk.py     # ONLY module importing `docker` (implement ops here)
├── services.py       # application services over the gateway (add container ops here)
└── tui/
    ├── app.py        # Textual app, bindings, worker-thread probes
    ├── screens.py    # StatusView, HelpScreen (add container list/details views)
    └── widgets.py    # FieldRow and shared row widgets

tests/
├── unit/             # fake-gateway tests: mapping, guards, state buckets, config
└── integration/      # live-daemon tests: lifecycle, logs, list (marked)
```

**Structure Decision**: Single-project layout (existing `src/deck` package).
New packaging artifact (container image definition) lives at the repository root
alongside `pyproject.toml`; no new top-level project is created.

## Complexity Tracking

> No Constitution Check violations — this section is intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --------- | ---------- | ------------------------------------ |
| —         | —          | —                                    |
