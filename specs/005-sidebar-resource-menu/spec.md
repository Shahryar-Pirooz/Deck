# Feature Specification: Sidebar Resource Menu

**Feature Branch**: `005-sidebar-resource-menu`

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: "add a menu in left side that user can switch between images 1.list , 2.containers , 3.valoumes , 4.networks. user can switch them via number"

## Clarifications

### Session 2026-10-02

- Q: How should keyboard focus work between the left-side menu and the main resource list? → A: Sticky main focus — number keys switch views, focus stays in the main list; sidebar is a non-focusable indicator.
- Q: Which number-to-resource mapping should the sidebar use? → A: Containers first — 1 Containers, 2 Images, 3 Volumes, 4 Networks.
- Q: What minimum information should the new Images, Volumes, and Networks lists display? → A: Detailed columns — Images: name/tag + id + size + created; Volumes: name + driver + mountpoint; Networks: name + driver + scope.
- Q: How should selection and Enter behave in the Images, Volumes, and Networks views? → A: Select plus details — j/k moves highlight, Enter opens a read-only details panel.
- Q: When switching between resource views, should each view remember its highlight position? → A: Remember per view — each view keeps its own highlight index when leaving and returning.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse Docker resources via left-side menu (Priority: P1)

An operator opens the terminal manager and sees a left-side menu listing four resource categories: Containers, Images, Volumes, and Networks. The main content area shows the active resource type; the sidebar always indicates the active entry but never takes keyboard focus away from the main list.

**Why this priority**: This is the core requested value — a single persistent place to see and switch between the four main Docker resource groups. Without it the app remains containers-only.

**Independent Test**: Can be fully tested by launching the app, observing the left menu with four entries in order, pressing `1`-`4` in turn, and confirming the main panel title and content change to match the selected resource type while keyboard focus remains in the main list. Delivers navigable multi-resource browsing.

**Acceptance Scenarios**:

1. **Given** the app main screen is open, **When** the user looks at the left side, **Then** a menu is visible showing entries "1 Containers", "2 Images", "3 Volumes", "4 Networks" in that order.
2. **Given** the left menu is visible with Containers selected, **When** the user presses `2`, **Then** the main content area switches to the images view, the menu highlights Images as active, and keyboard focus stays in the main list.
3. **Given** the left menu is visible, **When** the user presses `1`-`4` in turn, **Then** each press updates the main content heading and list to the corresponding resource type.

---

### User Story 2 - Switch resource views with number keys 1-4 (Priority: P1)

An operator who prefers the keyboard presses `1`, `2`, `3`, or `4` and the app immediately switches the main view to Containers, Images, Volumes, or Networks respectively, without needing to move focus step by step.

**Why this priority**: Keyboard-first operation is a non-negotiable project principle; number-key switching is the explicitly requested interaction and makes the menu fast for experienced operators.

**Independent Test**: Can be fully tested by pressing each of `1` through `4` from the main screen and observing the active menu highlight plus main content change each time. Delivers the requested numeric shortcut behavior.

**Acceptance Scenarios**:

1. **Given** any resource view is active, **When** the user presses `2`, **Then** the Images view becomes active and is highlighted in the menu.
2. **Given** any resource view is active, **When** the user presses `1`, `3`, or `4`, **Then** the Containers, Volumes, or Networks view becomes active respectively.
3. **Given** a modal dialog (details, confirm, or help) is open, **When** the user presses `1`-`4`, **Then** the underlying resource view does not switch until the dialog is closed.

---

### User Story 3 - Understand current selection and empty states (Priority: P2)

An operator always knows which resource category is active and what to do when a category has no items or Docker is unreachable, because the active menu entry is visually distinct and each view shows a clear title, count or empty message, and guidance.

**Why this priority**: Prevents confusion when switching fast between views and keeps the app usable when Docker is down or a resource type is empty.

**Independent Test**: Can be fully tested by switching views with Docker unreachable and with an empty resource type, and confirming the active highlight stays correct plus each view shows an explanatory message rather than a blank or stale list. Delivers trustworthy view state.

**Acceptance Scenarios**:

1. **Given** the Images view is active, **When** the user looks at the menu, **Then** only the Images entry appears selected and the main panel identifies itself as the images view.
2. **Given** a resource type has zero items, **When** the user switches to that view, **Then** the view shows an empty message naming that resource type instead of showing another type's items.
3. **Given** Docker is unreachable, **When** the user switches between menu entries, **Then** each view shows an unavailable message with retry guidance and the menu remains switchable.

---

### Edge Cases

- Docker Engine unreachable mid-session — switching menu entries keeps the menu responsive and shows per-view unavailable guidance with retry, without freezing.
- Empty resource category — view shows a named empty message (e.g., no images found) rather than blank or stale data from the previous view.
- Narrow / small terminal — left menu remains visible and usable; labels shorten gracefully rather than pushing the main panel off-screen.
- Number key pressed inside a modal, search input, or command input — the key is treated as input to that context, not as a view switch.
- Rapid repeated presses of `1`-`4` — only the last requested view is shown; no mixed or duplicated content appears.
- Existing container keyboard controls (`j`/`k`, `Enter`, `r`, `?`, `q`, `Esc`) keep working after the menu is added; number keys do not replace them.
- "valoumes" interpreted as Volumes (see Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a persistent left-side menu on the main screen listing exactly four entries in fixed order: `1 Containers`, `2 Images`, `3 Volumes`, `4 Networks`.
- **FR-002**: System MUST visually distinguish the currently active menu entry from inactive entries at all times.
- **FR-003**: Users MUST be able to switch the main content area to any menu entry via number keys (`1`-`4`) while keyboard focus remains in the main list; the sidebar is a non-focusable indicator and MUST NOT capture `j`/`k`/`Enter` navigation.
- **FR-004**: System MUST switch the main content area to Containers when the user presses `1`, to Images on `2`, to Volumes on `3`, and to Networks on `4` from the main screen.
- **FR-005**: System MUST show a view-specific main panel for each selection, identified as Containers, Images, Volumes, or Networks, and MUST NOT mix items from different resource types in one view.
- **FR-005a**: Images view MUST list each image with at minimum repository name/tag, image id, size, and creation date.
- **FR-005b**: Volumes view MUST list each volume with at minimum name, driver, and mountpoint.
- **FR-005c**: Networks view MUST list each network with at minimum name, driver, and scope.
- **FR-006**: System MUST preserve existing container list behavior (columns, selection, details, lifecycle actions) when the Containers view is active.
- **FR-006a**: Images, Volumes, and Networks views MUST support `j`/`k` highlight movement and `Enter` to open a read-only details panel for the selected item; no lifecycle actions are required in these views.
- **FR-006b**: System MUST remember each view's highlight position independently so returning to a view restores its previous selection.
- **FR-007**: System MUST display a named empty state when the selected resource type has no items.
- **FR-008**: System MUST display an actionable unavailable/error state with retry guidance in the main panel when Docker data for the selected view cannot be loaded, while keeping the menu switchable.
- **FR-009**: System MUST NOT trigger a view switch from `1`-`4` presses while a modal dialog or text input is focused; the keypress belongs to that context.
- **FR-010**: System MUST keep all view switching keyboard-operable without a mouse and MUST document the `1`-`4` shortcuts in on-screen help.
- **FR-011**: System MUST derive all displayed resource data from the Docker Engine at view time and MUST NOT show stale data from a previously selected view as if it belonged to the new view.
- **FR-012**: System MUST keep view switching responsive (no frozen input) including when Docker responses are slow, showing a loading indication in the main panel.

### Key Entities

- **Sidebar Menu**: Persistent left-side list of resource categories; attributes: ordered entries (position 1-4, label, target view), active entry. Fixed order is 1 Containers, 2 Images, 3 Volumes, 4 Networks.
- **Resource View**: Main content panel for one Docker resource type; attributes: resource type (containers, images, volumes, networks), title, item list or empty/loading/error state. Detailed columns: images (repository tag, id, size, created), volumes (name, driver, mountpoint), networks (name, driver, scope).
- **View Selection**: Which resource type is currently active; attributes: current type, per-view remembered highlight position, chosen via number key.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: First-time users can locate the left menu and switch to each of the four resource views in under 60 seconds using on-screen hints alone.
- **SC-002**: 100% of `1`-`4` keypress trials from the main screen result in the correct resource view becoming active with matching menu highlight.
- **SC-003**: 90% of users switching between all four views correctly identify which resource type is currently displayed on first attempt.
- **SC-004**: View switches complete with visible feedback (highlight plus content change) in under 2 seconds when Docker data is available, and show a loading or guidance state otherwise with no frozen input.

## Assumptions

- Menu mapping is `1 = Containers`, `2 = Images`, `3 = Volumes`, `4 = Networks`; "valoumes" is treated as a typo for Volumes. Containers is first as the existing default view.
- The menu is single-level with no submenus; filtering, sorting, and per-resource actions beyond the existing container actions are out of scope.
- Containers remains the default active view on startup to preserve current behavior.
- Existing Vim-style navigation (`j`/`k`, `Enter`, `r`, `?`, `Esc`, `q`) continues to work; `1`-`4` are additive shortcuts.
- Images, volumes, and networks views may initially be read-only lists; full lifecycle actions for those types are out of scope for this feature.
- Narrow-terminal behavior reuses the project's existing responsive layout approach: menu stays visible with shortened labels.
