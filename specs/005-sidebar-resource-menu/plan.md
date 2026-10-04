# Implementation Plan: Sidebar Resource Menu

**Branch**: `005-sidebar-resource-menu` | **Date**: 2026-10-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-sidebar-resource-menu/spec.md`

## Summary

Add a persistent left-side menu (`1 Containers`, `2 Images`, `3 Volumes`, `4 Networks`) to the terminal manager with number-key view switching, sticky main-list focus, per-view remembered highlight, and read-only detailed lists for images/volumes/networks. Approach per research: extend the `DockerGateway` protocol with frozen image/volume/network row types implemented only in `docker_sdk.py`, add matching read-only services, introduce a non-focusable sidebar indicator plus a per-view list state in the TUI (`tui/app.py`, `tui/screens.py`), and gate `1`-`4` bindings so modals/text inputs keep the keypress.

## Technical Context

**Language/Version**: Python ≥3.11 (pinned minimum in `pyproject.toml`; codebase uses 3.11 idioms: `StrEnum`, `datetime.UTC`, `X | None`)

**Primary Dependencies**: `textual~=8.2` (TUI), `docker==7.2.0` (Engine SDK, imported only in `src/deck/docker_sdk.py`), `platformdirs>=4.3` (config paths). No new runtime dependencies planned.

**Storage**: N/A — no app persistence. Docker Engine is the source of truth (queried per view switch/refresh); per-view highlight positions are in-memory UI state only.

**Testing**: `pytest` (asyncio auto mode, `--cov-fail-under=80`); `tests/unit` runnable without a daemon via a fake gateway; `tests/integration` (marked) against a live daemon; `ruff check` + `ruff format --check`; `mypy` strict.

**Target Platform**: Linux host Engine; app runs on host or inside a Linux container with an interactive terminal attached (80x24 minimum, SSH-friendly, resizable).

**Project Type**: Terminal TUI application (single project).

**Performance Goals**: View switch shows highlight plus content change in under 2s when Engine data is available (SC-004); keypresses acknowledged without frozen input; loading indication for slow Engine responses; one list query per view per refresh/switch.

**Constraints**: TUI must never block rendering on Engine calls (existing worker-thread pattern in `tui/app.py`); SDK imports isolated to `docker_sdk.py`; strict typing and lint must pass; `1`-`4` MUST NOT fire while a modal dialog or text input is focused (FR-009); new views are read-only lists with read-only details (no lifecycle actions); single local Engine only.

**Scale/Scope**: Single host, single interactive user, four resource views; up to ~100 items per resource type (consistent with the 100-container baseline); rapid `1`-`4` presses resolve to the last requested view.

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

- [x] **I. Docker is source of truth** — every view re-queries the Engine on switch/refresh; no persistent app-side resource state; per-view highlight is UI-only, never treated as Engine state.
- [x] **II. Layered interface** — TUI calls services, services call the `DockerGateway` protocol, only `docker_sdk.py` touches the SDK; new image/volume/network reads follow the same seam.
- [x] **III. Safety over convenience (NON-NEGOTIABLE)** — new views are read-only; no new destructive operations added; existing container confirmation and self-action guards untouched.
- [x] **IV. Keyboard first (NON-NEGOTIABLE)** — all switching keyboard-operable (`1`-`4` additive, `j`/`k` + `Enter` preserved in every list); shortcuts documented in help; no mouse dependency.
- [x] **V. TUI first** — same Textual app, SSH-friendly, resizable; no graphical dependency; UI state separated from Engine state.
- [x] **VI. Simple ops stay simple** — sticky main focus keeps container actions one key away; sidebar adds no submenu or extra steps to start/stop/logs.
- [x] **Adapter isolation** — gateway protocol extended with list/inspect reads; no SDK types leak past `docker_sdk.py`.
- [x] **Security** — read-only lists expose no secrets; permission/unavailable states reuse the four-state reporting with guidance; no credentials logged.
- [x] **Error handling** — per-view loading/empty/unavailable states with retry guidance; no raw tracebacks in normal mode; debug detail preserved.
- [x] **Testing** — fake-gateway unit tests (mapping, switching, memory, key suppression) plus live-daemon integration for new lists; TUI keybinding tests for `1`-`4`.
- [x] **Performance** — worker-thread queries, single list call per view per switch, bounded rows; no blocking render.
- [x] **Dependencies** — no new runtime dependencies.
- [x] **Documentation** — shortcuts, view columns, failure modes documented (quickstart + contracts).

_Post-design re-check (after Phase 1): no new violations introduced — data model keeps Engine-query semantics with UI-only selection state, contracts preserve the adapter boundary and keyboard baseline, quickstart validates switching end to end._

## Project Structure

### Documentation (this feature)

```text
specs/005-sidebar-resource-menu/
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
├── docker_gateway.py # DockerGateway protocol + row types (extend here: images/volumes/networks)
├── docker_sdk.py     # ONLY module importing `docker` (implement list/inspect here)
├── services.py       # application services over the gateway (add read-only list services)
└── tui/
    ├── app.py        # Textual app, bindings 1-4, worker-thread probes, per-view state
    ├── screens.py    # StatusView, HelpScreen, list views (add sidebar + resource lists/details)
    └── widgets.py    # FieldRow and shared row widgets

tests/
├── unit/             # fake-gateway tests: mapping, columns, switching, memory, key suppression
└── integration/      # live-daemon tests: images/volumes/networks lists (marked)
```

**Structure Decision**: Single-project layout (existing `src/deck` package). No new top-level project; sidebar and views live inside the existing TUI module.

## Complexity Tracking

> No Constitution Check violations — this section is intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --------- | ---------- | ------------------------------------ |
| —         | —          | —                                    |
