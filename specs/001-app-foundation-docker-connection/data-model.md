# Data Model: Application Foundation and Docker Connection

**Feature**: `001-app-foundation-docker-connection` | **Date**: 2026-09-29

Derived from spec Key Entities + FR-003/FR-004/FR-011/FR-013 and clarifications.
Conceptual only — no storage of Docker state beyond the in-memory snapshot.

## 1. DockerConnectionStatus

Current Engine reachability for one manual probe.

| Field | Type | Rules |
|-------|------|-------|
| state | enum `ConnectionState` | REQUIRED; one of `connected`, `unavailable`, `permission-denied`, `connection-failed` |
| endpoint | string | REQUIRED; probed endpoint label (e.g. local socket path); never a secret |
| detail | string | REQUIRED; human-readable cause + remediation hint; no traceback in normal mode |
| probed_at | timestamp | REQUIRED; when the probe completed |

State transitions: any state → any state on each manual refresh (`r`) or startup probe.
Initial state before first probe completes: `unavailable` with `detail="Probing…"`.

## 2. DockerSystemSummary

Point-in-time Engine facts; present only when `state == connected`, else all fields
shown as unavailable (never blank/crash). Source: `version()` + `info()`.

| Field | Type | Source / Rule |
|-------|------|---------------|
| version | string | REQUIRED for acceptance; `version().Version` |
| api_version | string \| null | `version().ApiVersion`; null → display "unavailable" |
| os | string | REQUIRED; `version().Os` |
| architecture | string | REQUIRED; `version().Arch` |
| containers_total | int ≥ 0 | REQUIRED; `info().Containers` |
| containers_running | int ≥ 0 | REQUIRED; `info().ContainersRunning`; ≤ total |
| containers_stopped | int ≥ 0 | REQUIRED; `info().ContainersStopped` (or derived total − running − paused) |
| images | int ≥ 0 | REQUIRED; `info().Images` |

Validation: counts are non-negative ints; `running + stopped ≤ total` (paused covers
remainder); missing numeric → field shown as unavailable, status stays connected if the
probe itself succeeded (spec edge case).

## 3. ApplicationConfiguration

Validated user preferences with defaults + per-field fallback (invalid file or invalid
single value never blocks startup; user is informed what was ignored).

| Field | Type | Default | Rule |
|-------|------|---------|------|
| docker.endpoint | string | local socket (`unix:///var/run/docker.sock` unless `DOCKER_HOST` set) | Local-only this release; remote TCP/SSH rejected or ignored with notice |
| display.theme | string | `dark` | One of `dark`, `light`; unknown → default |
| debug | bool | `false` | `true` adds on-screen cause + diagnostics; always writes full log file |
| log_path | string | platform log dir | Informational; redaction filter always applied |

Relationships: `ApplicationConfiguration` parametrizes probe (endpoint, timeout) and
presentation (theme, debug verbosity). No relationship to Docker entities beyond that;
config never stores Docker state.

## 4. DiagnosticRecord (conceptual)

| Field | Rule |
|-------|------|
| on_screen | Human-readable cause + endpoint probed + remediation hints; secrets redacted |
| log_file | Complete technical detail (error chain, SDK message) at platform log path; same redaction filter |

No Docker socket data, env secrets, or credentials are persisted outside the log file,
and never in plain-text config.
