# Implementation Plan: Image Run Menu

**Branch**: `006-image-run-menu` | **Date**: 2026-10-07 | **Spec**: /specs/006-image-run-menu/spec.md

**Input**: Feature specification from `/specs/006-image-run-menu/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Add a "Run" action to the Images view that opens a configuration menu for name, port mappings, volumes, network, and environment variables. On confirmation, the container is created and started in detached mode via the existing Docker adapter. Image pulls are performed in the background so the TUI stays responsive; a notification is shown on completion. The flow respects Constitution III (safety confirmation), V (TUI first), and VI (simple operations).

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: Textual (TUI framework), Docker SDK for Python >= 7.1, platformdirs

**Storage**: N/A (runtime: Docker Engine; no persistent storage in application itself)

**Testing**: pytest >= 8.3, pytest-asyncio, pytest-cov

**Target Platform**: Linux (TUI first); SSH-compatible terminal; Textual 8.x

**Project Type**: Desktop TUI application / CLI tool (keyboard-first Docker management)

**Performance Goals**: Normal navigation feels instantaneous; container launch operations complete within 30 seconds (excluding image pull time per SC-001)

**Constraints**: 
- Must not block TUI event loop during Docker operations (Constitution §V)
- Keyboard-first navigation mandatory per Constitution §IV
- All Docker access through adapter layer only (Constitution §II)
- Simple operations must stay simple per Constitution §VI

**Scale/Scope**: Single-feature MVP; targeting Docker Engine features: containers, images, networks, volumes; MVP includes core container creation with name, ports, volumes, network, env vars

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status | Note |
|---|---|---|---|
| I. Docker Is the Source of Truth | The container creation flow MUST call the Engine directly via the adapter; no stale cache may be used to decide image availability | PASS | Adapter already isolates Engine calls; `list_images` reads locally pulled images only |
| II. AI Is an Interface, Not Infrastructure | Feature has no AI tools; no SDK command execution outside the adapter layer | PASS | No AI surface in scope |
| III. Safety Over Convenience | Container creation (CAUTION-class) MUST require explicit user confirmation; background image pull must be cancellable | PASS | Clarified in spec: confirmation review screen before create+start; image pull runs in background on TUI thread |
| IV. Keyboard First | Run menu fully operable via j/k/h/l/Enter/Space/Enter/Escape without mouse | PASS | Textual screen uses Vim-style bindings; list navigation via `j`/`k`, confirm via `Enter` |
| V. TUI First | Image pull MUST NOT block the TUI event loop; user remains in the run flow | PASS | Pull dispatched as background task; notification on completion |
| VI. Simple Operations Must Stay Simple | Common run operation: 2-3 key actions (select image, confirm) | PASS | Single "Run" action creates and starts in detached mode; defaults minimize clicks |

> All gates pass; no complexity justifications required.

### Post-Design Re-evaluation

| Principle | Status | Design Impact |
|---|---|---|
| I. Docker Is the Source of Truth | PASS | New `create_and_run_container` method added to `DockerGateway` protocol and implemented in `SdkGateway`; no local state maintained for container lifecycle. |
| II. AI Is an Interface, Not Infrastructure | PASS | No AI integration in this feature. |
| III. Safety Over Convenience | PASS | Confirmation review screen (`RunConfigScreen`) shown before any Docker API call. |
| IV. Keyboard First | PASS | `RunConfigScreen` uses `Input` widgets with Vim-style navigation; confirm via `Enter`, cancel via `Escape`. |
| V. TUI First | PASS | Image pull dispatched via `asyncio.to_thread()`; TUI remains responsive. |
| VI. Simple Operations Must Stay Simple | PASS | Default network = bridge; empty ports/volumes/envs allowed; single confirm action. |

> All gates remain PASS after Phase 1 design. No complexity justifications required.

## Project Structure

### Documentation (this feature)

```text
specs/006-image-run-menu/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── container-run-api.yml
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── deck/
│   ├── config.py
│   ├── cli.py
│   ├── docker_gateway.py
│   ├── docker_sdk.py
│   ├── services.py
│   ├── logging_setup.py
│   └── tui/
│       ├── __init__.py
│       ├── app.py
│       ├── screens.py
│       ├── widgets.py
│       └── run_config.py        # NEW: RunConfigScreen overlay
```

**Structure Decision**: Single-project layout (Option 1). The new `run_config.py` in `deck/tui/` contains the modal overlay screen for container configuration. No new packages or services needed; the existing `SdkGateway` adapter in `docker_sdk.py` already supports `list_images` and `start_container`/`remove_container`; a new `create_and_run_container` method will be added to the `DockerGateway` protocol and implemented in `SdkGateway`.

## Complexity Tracking

> No complexity justifications required. All Constitution gates pass without violations.
