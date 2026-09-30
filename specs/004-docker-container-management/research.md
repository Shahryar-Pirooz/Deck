# Research: Docker Container Management

**Feature**: `004-docker-container-management` | **Date**: 2026-09-29

All unknowns below were resolved during clarification (5/5) and codebase review;
no `NEEDS CLARIFICATION` items remain in the Technical Context.

## 1. Engine access mode from inside the app container

- **Decision**: Share the host Engine access into the app container (single shared
  Engine scope). A private Engine inside the container and remote TCP Engines are
  out of scope.
- **Rationale**: Directly delivers "manage other (host) containers" with one source
  of truth; reuses the existing local-only `SdkGateway` path (`docker.from_env`
  semantics); least new machinery.
- **Alternatives considered**:
  - Private Engine inside the container (Docker-in-Docker daemon) — rejected: it
    cannot see host containers, needs a privileged daemon, and contradicts the
    feature request.
  - Remote TCP Engine — rejected: deferred by foundation config policy (local-only)
    and expands the security surface.

## 2. Container image packaging

- **Decision**: Minimal official Python 3.11 image definition at the repository root
  that installs the packaged app (`pyproject.toml`, hatchling) and sets the
  `docker-tui` entry point as the container command; versioned tags per release.
- **Rationale**: Matches `requires-python >=3.11` and the existing
  `[project.scripts]` entry point; keeps the dependency graph unchanged (textual,
  docker SDK, platformdirs); mature, maintained base.
- **Alternatives considered**:
  - Alpine base — rejected: musl wheel/build risk for pinned dependencies with no
    meaningful size benefit for a TUI tool.
  - Distroless base — rejected: harder interactive debugging and TTY troubleshooting
    for a terminal-first tool.

## 3. Self-container identification

- **Decision**: Best-effort identification combining container hostname/id visible
  from inside with Engine-side matching; when undetermined, destructive guards apply
  broadly with warnings (per spec Assumptions).
- **Rationale**: No single mechanism is reliable across runtimes; best-effort plus
  fail-safe guards satisfies FR-007 without blocking startup.
- **Alternatives considered**:
  - Require an explicit self-id variable — rejected: extra setup friction against
    "Simple Operations Must Stay Simple".
  - No self handling — rejected: violates Safety Over Convenience (manager could
    stop/remove itself).

## 4. Container state grouping (running/stopped/other)

- **Decision**: Map Engine statuses to three buckets — `running` (running,
  restarting), `stopped` (exited, created, dead, removing), `other` (paused plus
  anything unrecognized) — with the exact Engine status string preserved for the
  details view.
- **Rationale**: Keeps the list scannable per clarification C while never hiding a
  true condition; consistent with foundation counts (total/running/stopped).
- **Alternatives considered**:
  - Running/stopped only — rejected: mislabels paused/restarting containers.
  - Verbatim states in the list — rejected: noisy, complicates keyboard scanning.

## 5. List scale strategy (100 siblings)

- **Decision**: One list query per manual refresh; render rows lazily through the
  existing Textual view pattern; fetch logs/details on demand only.
- **Rationale**: Meets the 100-container target within the "never block rendering"
  rule; matches the manual-refresh-only foundation (no polling streams).
- **Alternatives considered**:
  - Eager-fetch all details/logs — rejected: unbounded memory and slow refresh.
  - Event streaming for live updates — rejected: foundation scope is manual-only;
    revisit in a later feature.

## 6. Keybindings for container actions

- **Decision**: Reuse the Vim baseline (`j/k` move, `Enter` open/select, `r`
  refresh, `?` help, `Esc` cancel, `q` quit); container actions (start/stop/restart/
  logs/remove) exposed on the details view plus discoverable single keys documented
  in help; remove always confirms; no new mouse dependency.
- **Rationale**: Constitution prefers conventional Vim bindings and forbids
  excessive arbitrary shortcuts; details-view actions keep the list keys minimal.
- **Alternatives considered**:
  - One-letter direct keys for every action on the list — rejected: shortcut
    sprawl, higher accidental-destruction risk.
  - Command-mode (`:`) only — rejected: harder to discover for first-time users
    (SC-005).

## 7. Test strategy without and with a daemon

- **Decision**: Unit tests use a fake `DockerGateway` (list/action/logs mapping,
  state buckets, self-block, confirmation flow, error classification) with no
  daemon; integration tests (marked) run lifecycle + logs against a live daemon;
  TUI tests cover new bindings and the blocked-self message.
- **Rationale**: Follows the constitution's testing pyramid and the existing
  `tests/unit` vs `tests/integration` split; keeps the 80% coverage gate.
- **Alternatives considered**:
  - Daemon-required tests only — rejected: breaks hermetic unit runs and CI without
    Docker.
  - Snapshot golden files of Engine payloads — rejected: SDK payload shapes drift;
    mapping tests on curated fixtures are more stable.
