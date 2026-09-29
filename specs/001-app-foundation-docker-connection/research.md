# Research: Application Foundation and Docker Connection

**Feature**: `001-app-foundation-docker-connection` | **Date**: 2026-09-29

All Technical Context unknowns resolved below. No NEEDS CLARIFICATION remains.

## 1. TUI Framework

- **Decision**: `textual~=8.2` (verified 8.2.8, 2026-06-30; requires Python >=3.9, MIT).
- **Rationale**: Actively maintained top-100 PyPI framework; async-native workers +
  `run_in_thread` keep Docker queries off the render loop; declarative bindings, header/
  footer, data-style status widgets, modal screens, reactive resize, and headless Pilot
  testing directly cover Vim keys, help modal, loading/error states, 80x24 + resize, and
  SSH use.
- **Alternatives considered**: `urwid` — light and stable but LGPL, no native async or
  headless test story, more boilerplate for tables/modals; `python-curses` (stdlib) —
  zero weight and SSH-safe but no widgets/layout/testing, all resize/key/paint manual.

## 2. Docker Client and Query Strategy

- **Decision**: `docker==7.2.0` (docker-py) via `docker.from_env()` with short timeout,
  one lightweight `ping()` liveness gate then `version()` + `info()` per manual refresh;
  pass local-only guard (`DOCKER_HOST` unset → default socket; set `use_context=False`
  or `DOCKER_CONTEXT=default` so the new 7.2 context-honoring default cannot silently
  connect to a remote context — clarifies "local socket only" scope). Never `df()`.
- **Rationale**: Official maintained SDK; `from_env` honors standard socket/env without
  hardcoding; `version()` gives `Version`/`ApiVersion`/`Os`/`Arch`, `info()` gives
  `Containers`/`ContainersRunning`/`ContainersStopped`/`Images` — exactly the mandatory
  acceptance fields with two cheap calls.
- **Alternatives considered**: Raw Engine HTTP over socket — fewer deps but reimplements
  version negotiation, TLS, error taxonomy; `podman`-style clients — out of scope.

## 3. Error Classification

- **Decision**: Map chained SDK/transport errors to the four spec states; inspect
  `__cause__`/`__context__` chain plus message substrings (SDK ≥4.3 surfaces transport
  errors wrapped in `DockerException`, not bare `APIError`).
- **Rationale**: Gives testable, user-actionable categories without tracebacks.
- **Alternatives considered**: String-matching only (brittle) or exposing raw SDK
  exceptions (violates error-handling constitution).

| State | Signal |
|-------|--------|
| connected | `ping()` + `version()` + `info()` succeed |
| unavailable | socket missing (`FileNotFoundError` ENOENT), daemon down / `DockerException: Error while fetching server API version` with missing-socket cause |
| permission-denied | `PermissionError` EACCES in chain or `permission denied` substring |
| connection-failed | refused/reset, `requests.ConnectionError`/`urllib3.ProtocolError`, `APIError(5xx)`, TLS/version mismatch; unknown → `connection-failed` fallback |

## 4. Architecture Boundary

- **Decision**: Single `DockerGateway` protocol owned by the app (`get_snapshot()` →
  frozen snapshot + `ConnectionState` enum); one concrete `SdkGateway` encapsulates ALL
  SDK imports/calls/mapping and never leaks SDK types; TUI depends only on the protocol
  plus an app-level refresh service; tests inject `FakeGateway` or mock the protocol
  method — no live daemon needed for unit/TUI tests.
- **Rationale**: Satisfies layered-architecture gate (TUI never imports `docker`);
  single seam for future `ContainerService`/`ImageService` without rewrite; unit-testable.
- **Alternatives considered**: Service calling SDK directly from widgets (rejected —
  leaks API details, untestable); repository-per-resource now (rejected — overengineering
  for one status screen).

## 5. Packaging, Python Floor, Config, Logging

- **Decision**: `src/` layout with `hatchling>=1.27` build backend;
  `requires-python>=3.11` (3.10 EOL Oct 2026; 3.11 gives `tomllib`, security to Oct 2027;
  keeps Ubuntu 22.04 compat; dev on 3.14); `[project.scripts] docker-tui` entry point;
  runtime deps `textual~=8.2`, `docker==7.2.0`, `platformdirs>=4.3`.
- **Rationale**: Minimal mature graph per dependency principle; `src/` layout prevents
  import shadowing; entry point satisfies FR-001.
- **Alternatives considered**: `setuptools` (fine but hatchling simpler for `src/` +
  scripts); `>=3.12` floor (cleaner syntax but drops 22.04 system Python); hand-rolled
  XDG paths (rejected — `platformdirs` is the maintained standard).
- **Config**: `platformdirs.user_config_path("docker-tui")/config.toml`
  (`~/.config/docker-tui/`, respects `XDG_CONFIG_HOME`); read with stdlib `tomllib`;
  frozen dataclass defaults; per-field `dict.get(key, default)` merge inside
  `try/except (TOMLDecodeError, OSError)` → fallback + user notice, never crash.
- **Logging**: stdlib only; `FileHandler` at
  `platformdirs.user_log_path("docker-tui")/docker-tui.log` (full detail) + console
  handler; `--debug`/`debug=true` selects DEBUG else INFO; custom `logging.Filter`
  redacts `password|token|secret|authorization` values to `***REDACTED***` on both
  handlers; never log raw env/args.

## 6. Testing, Lint, Types

- **Decision**: `pytest>=8.3` (+ `pytest-asyncio>=0.26`, `asyncio_mode=auto`,
  `pytest-cov>=6`); `tests/unit/` (faked gateway: success/unavailable/permission,
  info parsing, config defaults + per-field fallback, redaction filter — no daemon) +
  `tests/integration/` (`-m integration`, skipped without daemon via socket probe;
  Textual `Pilot` via `run_test()` for startup/shutdown/refresh/keypress);
  `ruff>=0.12` (lint+format, replaces black/isort/flake8) + `mypy~=1.18 --strict`.
- **Rationale**: Matches constitution test layers; keeps core logic daemon-free;
  `ruff`+`mypy --strict` is the stable 2026 CI standard.
- **Alternatives considered**: `pyright` over `mypy` (good but `mypy --strict` more
  established for CI gating here); `unittest`-only (rejected — Pilot needs pytest style).

## 7. Non-Blocking Refresh and Startup

- **Decision**: Manual-only refresh (per clarification): `r` dispatches a Textual worker
  thread that calls the blocking SDK synchronously with timeout; UI shows loading
  indicator, stays navigable, `q`/`Esc` always live; startup renders layout first, then
  probes Docker off-loop so a dead daemon never blocks or crashes launch.
- **Rationale**: Satisfies SC-001 (<10s status) and SC-004 (keypress ack <1s, never
  force-kill); avoids timer/background-refresh scope creep.
- **Alternatives considered**: `asyncio`-native SDK wrapper (rejected — `docker-py` is
  blocking; thread worker is the documented Textual pattern); auto-poll timer now
  (rejected — explicitly out of scope per clarification).
