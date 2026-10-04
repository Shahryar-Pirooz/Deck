# Research: Sidebar Resource Menu

**Feature**: `005-sidebar-resource-menu` | **Date**: 2026-10-02

All unknowns below were resolved during clarification (5/5) and codebase review;
no `NEEDS CLARIFICATION` items remain in the Technical Context.

## 1. Engine reads for images, volumes, networks (docker SDK 7.2.0)

- **Decision**: Extend the `DockerGateway` protocol with `list_images`, `list_volumes`, `list_networks` (plus lightweight inspect/detail reads backed by `get`), implemented only in `docker_sdk.py` via the SDK collections `client.images.list()`, `client.volumes.list()`, `client.networks.list()`. Failures degrade to an empty list with the existing four-state status guidance; unparsable rows are skipped with debug logging (same pattern as `list_containers`).
- **Rationale**: Reuses the proven degraded-list pattern (`SdkGateway.list_containers` returns `[]` on failure while the status panel explains); keeps TUI/services free of SDK types; read-only methods need no confirmation or self-action machinery.
- **Alternatives considered**:
  - Raw Engine HTTP calls — rejected: duplicates SDK auth/error handling and breaks adapter isolation.
  - Shelling out to a container CLI — rejected: violates Constitution II (layered interface) and is untestable without a daemon.

## 2. Row shaping for the clarified detailed columns

- **Decision**: New frozen dataclasses `ManagedImage` (repository tag, id, size, created), `ManagedVolume` (name, driver, mountpoint), `ManagedNetwork` (name, driver, scope) with non-empty identity validation in `__post_init__` (mirroring `ManagedContainer`); builder helpers `build_managed_image/volume/network` translate native SDK objects, falling back to `unknown` labels for missing optional fields but skipping rows with missing identity.
- **Rationale**: Matches the clarified FR-005a/b/c minimums exactly while keeping validation consistent with existing row types; `unknown` fallbacks preserve list usability when the Engine omits optional metadata.
- **Alternatives considered**:
  - Names-only rows — rejected: contradicts the accepted clarification (detailed columns).
  - Exposing native SDK objects to the TUI — rejected: leaks Engine details past the adapter boundary.

## 3. TUI sidebar + view-switch architecture (Textual 8.2)

- **Decision**: Add a non-focusable `SidebarView` indicator widget docked left with the fixed order 1 Containers / 2 Images / 3 Volumes / 4 Networks; keep a `ResourceType` selection plus per-view list state (rows + highlight index) in `DeckApp`; app-level `BINDINGS` for `1`-`4` call a `switch_view` action that updates the highlight, shows loading, and runs one worker-thread query for the target view; `j`/`k`/`Enter` continue to operate on the active list; modal screens keep their own bindings so `1`-`4` never reach the switch action while a dialog or input is focused (FR-009); help text gains the `1`-`4` row.
- **Rationale**: Delivers the accepted sticky-focus model with zero focus-trap risk; one query per switch preserves responsiveness; modal suppression falls out of Textual's focused-screen binding routing without special-casing.
- **Alternatives considered**:
  - Focusable sidebar with Tab/`h`/`l` pane switching — rejected: contradicts the accepted sticky-focus clarification and complicates `j`/`k` routing.
  - Eagerly loading all four views on startup — rejected: four Engine round-trips on launch; lazy per-view loading is faster and matches worker-thread patterns.

## 4. Per-view highlight memory and rapid switching

- **Decision**: Store one highlight index per `ResourceType` in the app (clamped on new data); switching restores that view's index; rapid `1`-`4` presses run through the single exclusive worker so only the last requested view renders (existing `exclusive=True` probe pattern in `tui/app.py`).
- **Rationale**: Implements the accepted remember-per-view clarification with minimal state; exclusive workers prevent mixed/duplicated content without extra locking.
- **Alternatives considered**:
  - Reset-to-top on every switch — rejected: contradicts the accepted clarification.
  - Shared single highlight across views — rejected: index from a long list would mis-clamp into short lists and disorient.

## 5. Test strategy (fake gateway + Pilot + live daemon)

- **Decision**: Extend the `FakeGateway` test double with the three new list methods; unit tests cover number→view mapping order, detailed-column builders, sticky focus (sidebar never focusable), modal key suppression, per-view memory, and named empty states — all without a daemon; Textual Pilot tests drive `1`-`4` presses; marked integration tests verify real `list_images/volumes/networks` against a live daemon.
- **Rationale**: Mirrors the existing `tests/unit` (fake gateway) / `tests/integration` (marked live) split and the `test_tui_keys.py` Pilot pattern; keeps the 80% coverage gate achievable without daemon dependence.
- **Alternatives considered**:
  - Daemon-only testing for new views — rejected: breaks the unit-without-daemon requirement.
  - Snapshot-image UI tests — rejected: brittle for terminal rendering; Pilot keybinding + row-text assertions are stable.
