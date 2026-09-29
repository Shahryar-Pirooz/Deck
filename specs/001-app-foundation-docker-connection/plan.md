# Implementation Plan: Application Foundation and Docker Connection

**Branch**: `001-app-foundation-docker-connection` | **Date**: 2026-09-29 | **Spec**: `specs/001-app-foundation-docker-connection/spec.md`

**Input**: Feature specification from `/specs/001-app-foundation-docker-connection/spec.md`

## Summary

Build the minimal installable `docker-tui` terminal app: startup renders a Textual
header/status/footer layout immediately, probes the LOCAL Docker Engine off the render
loop through an app-owned `DockerGateway` seam (`ping` → `version` + `info`), displays
the four connection states plus the mandatory Engine summary (version, OS/arch,
container total/running/stopped, image count, API version when available), supports
manual-only refresh (`r`), Vim baseline (`j/k/r/?/q/Esc`), validated TOML config with
defaults, human-readable diagnostics + redacted log file, and clean shutdown. No
container/image/network/volume/Compose/AI scope (FR-014). Approach per `research.md`:
Textual worker-thread refresh, `docker==7.2.0` local-only guard, `src/` + hatchling
packaging, faked-gateway unit tests + Pilot integration tests, `ruff` + `mypy --strict`.

## Technical Context

**Language/Version**: Python `>=3.11` (dev on 3.14.7; `tomllib` stdlib; 3.10 EOL Oct 2026)

**Primary Dependencies**: `textual~=8.2` (TUI/workers/Pilot), `docker==7.2.0` (official
Engine SDK, local `from_env` only), `platformdirs>=4.3` (config/log paths); dev:
`pytest>=8.3`, `pytest-asyncio>=0.26`, `pytest-cov>=6`, `ruff>=0.12`, `mypy~=1.18`.
Rationale and pins verified in `research.md` (Textual 8.2.8 2026-06-30; docker 7.2.0
2026-07-09 with context-honoring default → local guard required).

**Storage**: N/A for Docker state (in-memory snapshot only, per constitution I);
config file TOML at platform config dir; log file at platform log dir.

**Testing**: `pytest` unit (faked gateway, no daemon) + `pytest -m integration`
(real daemon, socket probe skip) incl. Textual Pilot for startup/shutdown/refresh/keys;
`pytest-cov --fail-under=80`; gates: `ruff check`, `ruff format --check`, `mypy src`.

**Target Platform**: Linux terminal ≥80x24, SSH-safe, keyboard-only acceptance.

**Project Type**: Single-project terminal TUI (`src/` layout, console script).

**Performance Goals**: SC-001 status visible <10s; SC-004 keypress ack <1s during slow
Docker responses, never force-kill; startup renders layout before probe completes.

**Constraints**: Local socket/env only (`use_context=False` guard, remote deferred);
manual-only refresh (no timers); TUI never imports SDK; no tracebacks in normal mode;
secrets always redacted; dead daemon never blocks/crashes startup.

**Scale/Scope**: One status screen; 3 entities (status, summary, config); foundation for
5 future services (container/image/network/volume/compose) without rewrite.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Docker is source of truth | PASS | In-memory snapshot per refresh only; no persistent Docker representation (`data-model.md`) |
| II. AI is interface, not infra | PASS | No AI in scope (FR-014); seam (`DockerGateway`) is AI-ready later |
| III. Safety (NON-NEGOTIABLE) | PASS | Read-only `ping/version/info` only; no destructive ops; quit/signal cleanup |
| IV. Keyboard first (NON-NEGOTIABLE) | PASS | `j/k/r/?/q/Esc` contract + help view; mouse optional (`contracts/foundation-contracts.md`) |
| V. TUI first | PASS | Textual, SSH-safe, resize handling, UI/infra state separated |
| VI. Simple ops stay simple | PASS | Single status screen; no advanced flows |
| Layered architecture | PASS | TUI → service → `SdkGateway` → Engine; SDK types never leak (`research.md` §4) |
| Python standards | PASS | Type hints, `mypy --strict`, `ruff`, small modules, sync SDK in worker thread only |
| TUI standards | PASS | Fast start, non-blocking refresh, loading/error/empty states, palette-ready layout |
| Error handling | PASS | 4 states with cause + guidance; debug adds diagnostics, never raw traceback |
| Testing | PASS | Unit (no daemon) + integration (real Engine) + Pilot TUI layers |
| Performance | PASS | Worker-thread probe, render-first startup, lazy two-call query |
| Configuration | PASS | Validated TOML + defaults + per-field fallback; env override via standard Docker env |
| Observability | PASS | Structured stdlib logs, redaction filter, version/Engine info, debug flag + log file |
| Dependencies | PASS | 3 runtime deps, each justified in `research.md`; stdlib preferred elsewhere |
| Docs / MVP constraint | PASS | FR-014 excludes all advanced scope; quickstart + contracts document actual behavior |

Post-Phase-1 re-check: design adds no new dependencies, no persistent state, no
auto-refresh, no remote endpoints — all gates remain PASS. No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/001-app-foundation-docker-connection/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── foundation-contracts.md  # CLI + keyboard + gateway + config contracts
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── docker_tui/
│   ├── __init__.py
│   ├── cli.py            # entry point (docker-tui, --debug/--config)
│   ├── config.py         # TOML load/validate/defaults
│   ├── logging_setup.py  # handlers + redaction filter
│   ├── docker_gateway.py # DockerGateway protocol + ConnectionState
│   ├── docker_sdk.py     # SdkGateway (only module importing `docker`)
│   ├── services.py       # refresh/status service over the protocol
│   └── tui/
│       ├── __init__.py
│       ├── app.py        # Textual App, worker refresh, bindings
│       ├── screens.py    # status screen + help modal
│       └── widgets.py    # status/error/loading rows
├── tests/
│   ├── unit/             # gateway fakes, parsing, config, redaction, startup/shutdown (no daemon)
│   └── integration/      # live daemon + Pilot (startup/refresh/keys, -m integration)
├── pyproject.toml        # hatchling, src layout, scripts.docker-tui, ruff/mypy/pytest config
└── README.md             # install + `docker-tui` usage (updated at implementation)
```

**Structure Decision**: Single-project `src/` layout (greenfield, one TUI binary). The
`docker_sdk.py`-only SDK import enforces the layered gate and gives one seam for future
`ContainerService`/`ImageService`/etc. without restructuring. `tests/unit` vs
`tests/integration` split keeps core logic daemon-free per constitution testing rules.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations — table intentionally empty.
