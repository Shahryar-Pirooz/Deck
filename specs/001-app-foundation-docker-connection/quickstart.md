# Quickstart: Application Foundation and Docker Connection

**Feature**: `001-app-foundation-docker-connection` | **Date**: 2026-09-29

Validates the feature end-to-end. Details in `data-model.md` and
`contracts/foundation-contracts.md`; no implementation code here.

## Prerequisites

- Linux, terminal ≥80x24, Python ≥3.11, Docker Engine optionally running.

## 1. Install and Launch (FR-001/FR-002, SC-001)

```sh
pip install -e ".[dev]"
docker-tui
```

Expected: header/status/footer render immediately; within 10s the status area shows
`connected` with version, OS/arch, container total/running/stopped, image count
(API version shown when available).

## 2. Docker Unavailable Stays Usable (FR-003/FR-005, SC-002)

```sh
sudo systemctl stop docker   # or revoke socket access to simulate permission-denied
docker-tui
```

Expected: app stays usable; status shows `unavailable` (or `permission-denied`
distinctly) with guidance to check daemon + socket permissions; no traceback in normal
mode. Restart daemon afterward and press `r` to recover.

## 3. Manual Refresh (FR-007/FR-008, SC-004)

With the app open, change Docker state externally (start/stop a container), press `r`.

Expected: loading indication if slow; counts update or a clear error appears; input and
`q`/`Esc` stay live throughout (keypress ack <1s, never force-kill).

## 4. Keyboard, Help, Quit (FR-009/FR-010/FR-012, SC-003)

Press `j`/`k` (selection moves), `?` (help lists `j/k r ? q Esc`), `Esc` (help closes),
`q` (clean exit, terminal restored). Send SIGTERM during refresh as a second pass —
same clean exit.

## 5. Config and Debug (FR-011/FR-013, SC-005)

```sh
# edit cosmically: ~/.config/docker-tui/config.toml (or --config override)
docker-tui --debug
```

Expected: valid edits persist across relaunches; corrupt file or bad value falls back
per-field with a notice and startup continues; `--debug` adds human-readable cause +
endpoint diagnostics on screen while the log file always holds complete (redacted)
detail — verify no secret values appear.

## 6. Quality Gates (Definition of Done)

```sh
pytest tests/unit -q
pytest -m "not integration" -q
pytest -m integration -q            # requires live daemon; skipped otherwise
ruff check . && ruff format --check .
mypy src
```

Expected: all green; unit/TUI paths pass with no daemon (faked gateway); integration
covers startup/shutdown/refresh against a real Engine.
