# Quickstart: Docker Container Management

**Feature**: `004-docker-container-management` | **Date**: 2026-09-29

Validation guide proving the feature end to end. Details: [data-model.md](./data-model.md),
[contracts/container-run.md](./contracts/container-run.md),
[contracts/gateway-operations.md](./contracts/gateway-operations.md),
[contracts/keyboard.md](./contracts/keyboard.md).

## Prerequisites

- Linux host with a running Engine and permission to share Engine access.
- A test container image available locally (e.g. a minimal long-running sample).
- An interactive terminal.

## 1. Build and start the manager as a container

1. Build the versioned image per the repository packaging definition.
2. Start the manager container per the documented run configuration (shared host
   Engine access + interactive terminal).
3. **Expected**: connected status with Engine summary and the sibling container
   list (name, image, running/stopped/other).

## 2. Handle a misconfigured run

1. Start the manager container WITHOUT shared Engine access.
2. **Expected**: usable `unavailable` status naming the run configuration; no
   traceback in normal mode.

## 3. Lifecycle a test container

1. Select a stopped test container → start → **expect** running state update.
2. Select it again → stop → **expect** stopped state update.
3. Select it → remove → **expect** a confirmation prompt; confirm → **expect**
   the row disappears. Decline once → **expect** no change.

## 4. Self-container guard

1. Locate the manager's own row (clearly identified).
2. Attempt stop or remove.
3. **Expected**: blocked with an explanatory message; the manager keeps running.

## 5. Logs and navigation

1. Open details/logs on a running container → **expect** log content within
   10 seconds with a loading indication first.
2. With ~100 containers present → **expect** smooth `j`/`k` navigation and one
   refresh round-trip per `r` press.
3. Press `?`, then `Esc`, then `q` → **expect** help opens/closes and the app
   exits cleanly with the terminal restored.

## 6. Test suites

- `pytest tests/unit -q` — gateway mapping, buckets, guards, confirmation flow
  (no daemon needed).
- `pytest -m integration -q` — live-daemon lifecycle and logs.
- `ruff check . && ruff format --check .` and `mypy src` — gates.
