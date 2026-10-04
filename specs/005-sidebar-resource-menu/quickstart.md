# Quickstart: Sidebar Resource Menu

**Feature**: `005-sidebar-resource-menu` | **Date**: 2026-10-02

Validation guide proving the feature end to end. Details: [data-model.md](./data-model.md),
[contracts/gateway-resources.md](./contracts/gateway-resources.md),
[contracts/keyboard-views.md](./contracts/keyboard-views.md).

## Prerequisites

- Linux host with a running Engine (or a misconfigured endpoint for the failure case).
- At least one image, container, volume, and network present (plus an empty state to check, e.g. a fresh test prefix).
- An interactive terminal.

## 1. See the sidebar and switch with number keys

1. Launch the app → **expect** a left-side menu reading `1 Containers`, `2 Images`,
   `3 Volumes`, `4 Networks` with Containers active by default.
2. Press `2`, `3`, `4`, `1` in turn → **expect** the main panel title, columns, and
   menu highlight to match each press with focus remaining in the main list.
3. Press `?` → **expect** the help view to document the `1`-`4` shortcuts.

## 2. Detailed columns per view

1. Switch to Images → **expect** repository tag, id, size, and created per row.
2. Switch to Volumes → **expect** name, driver, and mountpoint per row.
3. Switch to Networks → **expect** name, driver, and scope per row.

## 3. Selection, details, and per-view memory

1. In Images, move with `j`/`k`, note the highlighted row, press `Enter` →
   **expect** a read-only details panel (no actions offered).
2. Switch to another view and back → **expect** the previous highlight restored.
3. Repeat for Volumes and Networks.

## 4. Empty, loading, and failure states

1. Switch to a resource type with zero items → **expect** a named empty message
   (not another type's rows).
2. Stop the Engine (or point at a bad endpoint) and switch views → **expect** each
   view shows an unavailable message with retry guidance while the menu stays
   switchable; press `r` after restoring the Engine → **expect** recovery.
3. Open a details modal and press `1`-`4` → **expect** no view switch until the
   modal is closed.

## 5. No container regressions

1. Switch to Containers → **expect** the existing list, details, and
   start/stop/restart/logs/remove-with-confirmation behavior unchanged.
2. Rapidly tap `1`-`4` → **expect** only the last requested view rendered, no
   mixed content, no frozen input.

## 6. Test suites

- `pytest tests/unit -q` — mapping order, builders/columns, sticky focus, modal
  suppression, per-view memory, empty states (no daemon needed).
- `pytest -m integration -q` — live-daemon images/volumes/networks lists.
- `ruff check . && ruff format --check .` and `mypy src` — gates.
