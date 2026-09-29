# Contracts: Application Foundation and Docker Connection

**Feature**: `001-app-foundation-docker-connection` | **Date**: 2026-09-29

## 1. CLI Contract (`docker-tui`)

| Item | Contract |
|------|----------|
| command | `docker-tui` (from `[project.scripts]`); rename only if package/command conflict proven in implementation |
| flags | `--debug` (force debug verbosity for session); `--config <path>` (override config file, optional) |
| exit | `0` clean quit (`q`, signal handled, terminal restored); non-zero only on fatal init error with concise message, no traceback unless `--debug` |
| behavior | renders layout before Docker probe completes; dead daemon never blocks startup |

## 2. Keyboard Contract (baseline, constitution Principle IV)

| Key | Action |
|-----|--------|
| `j` / `k` | move selection down / up |
| `r` | manual refresh: re-probe Docker, show loading if slow, update status or error |
| `?` | open help view listing all shortcuts |
| `Esc` | close help / cancel |
| `q` | quit from main; close help when help focused |
| resize | reflow without overlap/crash at ≥80x24; smaller degrades gracefully |

Mouse: optional; keyboard-only is the acceptance bar.

## 3. Docker Gateway Contract (app-owned seam; TUI must depend only on this)

- `ConnectionState = connected | unavailable | permission-denied | connection-failed`
- `get_snapshot() -> (ConnectionState, DockerSystemSummary | None, detail: str)`
  - performs `ping()` → `version()` → `info()` with timeout; maps all failures per
    research error table; unknown errors → `connection-failed` with redacted message
  - MUST NOT leak SDK types/exceptions to callers; MUST NOT do I/O on the render thread
    (called from Textual worker)
- `FakeGateway` (tests) returns canned snapshots/errors for: success, unavailable,
  permission-denied, connection-failed, partial-info (missing `api_version`/counts)

## 4. Config File Contract (`config.toml`)

- Location: `platformdirs.user_config_path("docker-tui")/config.toml`
- Format: TOML; unknown keys ignored; per-field fallback to defaults with user notice
- Schema: `[docker] endpoint = "<local socket>"` (local-only; remote values rejected
  with notice); `[display] theme = "dark" | "light"`; `[logging] debug = bool`
- Invalid TOML / missing file / bad value → startup continues on defaults
