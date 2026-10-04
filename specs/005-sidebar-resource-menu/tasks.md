# Tasks: Sidebar Resource Menu

**Input**: Design documents from `/specs/005-sidebar-resource-menu/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included because the project constitution requires tests for every feature (Definition of Done, Testing Requirements) and quickstart.md defines unit + live-daemon suites.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline verification before any code changes

- [x] T001 Run baseline unit suite with `pytest tests/unit -q` from repository root and record failures (must be green before starting)
- [x] T002 [P] Verify quality gates pass from repository root (`ruff check .`, `ruff format --check .`, `mypy src`) and record failures

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Gateway + service reads for images/volumes/networks that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Extend `DockerGateway` protocol in `src/deck/docker_gateway.py` with frozen `ManagedImage` (`image_id` non-empty string, `repository_tag` non-empty string, `size_bytes` non-negative int, `created` string), `ManagedVolume` (`name` non-empty string, `driver` string, `mountpoint` string), `ManagedNetwork` (`network_id` non-empty string, `name` non-empty string, `driver` string, `scope` string) plus `list_images` / `list_volumes` / `list_networks` methods
- [x] T004 [P] Implement `build_managed_image` / `build_managed_volume` / `build_managed_network` builders plus `list_images` / `list_volumes` / `list_networks` on `SdkGateway` in `src/deck/docker_sdk.py` using `client.images.list()`, `client.volumes.list()`, `client.networks.list()` with degraded empty-list returns and skipped unparsable rows (depends on T003)
- [x] T005 [P] Add read-only `list_managed_images` / `list_managed_volumes` / `list_managed_networks` services in `src/deck/services.py` that return `[]` when the Engine is unreachable (depends on T003)

**Checkpoint**: Foundation ready - `FakeGateway` doubles can now serve all four resource types; user story implementation can begin

---

## Phase 3: User Story 1 - Browse Docker resources via left-side menu (Priority: P1) 🎯 MVP

**Goal**: Persistent left-side menu with fixed order `1 Containers`, `2 Images`, `3 Volumes`, `4 Networks`; main panel switches to the selected resource type with matching highlight

**Independent Test**: Launch the app, observe the four-entry menu in order, press `1`-`4` in turn, and confirm the main panel title and content change per press while focus stays in the main list

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T006 [P] [US1] Unit test for sidebar entry order and `ResourceType` mapping in `tests/unit/test_sidebar_resources.py` (fake gateway, no daemon)
- [x] T007 [P] [US1] Textual Pilot test for view switching via `1`-`4` in `tests/unit/test_sidebar_views.py` (assert panel title + menu highlight per press)

### Implementation for User Story 1

- [x] T008 [US1] Create non-focusable `SidebarView` indicator widget with fixed entries in `src/deck/tui/widgets.py`
- [x] T009 [US1] Add `ResourceType` selection state and dedicated 1-4 switch actions with generation-safe worker-thread queries in `src/deck/tui/app.py` (depends on T008)
- [x] T010 [US1] Render the unified per-view resource list, detailed rows, loading/empty/unavailable states, and read-only details in `src/deck/tui/screens.py`
- [x] T011 [US1] Document the `1`-`4` shortcuts in the help view in `src/deck/tui/screens.py`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Switch resource views with number keys 1-4 (Priority: P1)

**Goal**: `1` → Containers, `2` → Images, `3` → Volumes, `4` → Networks from the main screen; keypresses suppressed while a modal dialog or text input is focused

**Independent Test**: Press each of `1` through `4` from the main screen and observe the correct view plus highlight each time; open a modal, press `1`-`4`, and confirm no switch occurs until the modal closes

### Tests for User Story 2

- [x] T012 [P] [US2] Unit tests for number→view mapping order and modal/input suppression in `tests/unit/test_sidebar_keys.py` (fake gateway, no daemon)
- [x] T013 [P] [US2] Textual Pilot test pressing `1`-`4` with a modal open in `tests/unit/test_sidebar_keys.py` (assert no underlying switch)

### Implementation for User Story 2

- [x] T014 [US2] Add explicit app-level `1`-`4` BINDINGS and reject them when a modal screen is active in `src/deck/tui/app.py`
- [x] T015 [US2] Verify existing container bindings (`j`/`k`, `Enter`, `r`, `?`, `Esc`, `q`) still work with the menu present in `src/deck/tui/app.py` and fix regressions

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Understand current selection and empty states (Priority: P2)

**Goal**: Active entry always visually distinct; named empty states, per-view loading/unavailable-with-retry states, `j`/`k` + `Enter` read-only details in new views, per-view remembered highlight

**Independent Test**: Switch views with an empty resource type and with Docker unreachable; confirm named empty/unavailable messages plus correct highlight; check `j`/`k` + `Enter` opens read-only details and returning to a view restores its highlight

### Tests for User Story 3

- [x] T016 [P] [US3] Unit tests for named empty states, unavailable-with-retry rendering, and per-view highlight behavior in `tests/unit/test_sidebar_states.py` (fake gateway, no daemon)
- [x] T017 [P] [US3] Live-daemon integration test for images/volumes/networks lists in `tests/integration/test_resource_lists_live.py` (marked, requires Engine)

### Implementation for User Story 3

- [x] T018 [US3] Implement per-view `ready` / `loading` / `empty` / `unavailable` states with named empty messages and retry guidance in `src/deck/tui/screens.py`
- [x] T019 [US3] Add `j`/`k` highlight movement with `Enter` opening a read-only details panel (no lifecycle actions) for Images, Volumes, and Networks in `src/deck/tui/screens.py`
- [x] T020 [US3] Store one highlight index per `ResourceType` (clamped to `len(rows) - 1` on new data, restored on return) in `src/deck/tui/app.py`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validation, gates, and documentation

- [x] T021 [P] Update keyboard/shortcut documentation in `README.md` with the `1`-`4` view shortcuts
- [ ] T022 Run `quickstart.md` validation scenarios in `specs/005-sidebar-resource-menu/quickstart.md` end to end and fix deviations
- [ ] T023 Run full gates from repository root (`pytest tests/unit -q`, `ruff check .`, `ruff format --check .`, `mypy src`) and fix failures

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (US1 → US2 → US3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Builds on US1 sidebar state but independently testable via keypress mapping tests
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Builds on US1/US2 views but independently testable via state/memory tests

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Gateway/services (foundational) before TUI
- Sidebar widget before app wiring
- Core implementation before help/docs
- Story complete before moving to next priority

### Parallel Opportunities

- T002 can run in parallel with T001 (different commands, no shared files)
- T004 (`src/deck/docker_sdk.py`) and T005 (`src/deck/services.py`) can run in parallel after T003
- T006 and T007 can run in parallel (different test files)
- T012 and T013 can run in parallel (different test files)
- T016 and T017 can run in parallel (different test files)
- T021 can run in parallel with any implementation task (docs only)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for sidebar entry order and ResourceType mapping in tests/unit/test_sidebar_resources.py"
Task: "Textual Pilot test for view switching via 1-4 in tests/unit/test_sidebar_views.py"
```

## Parallel Example: Foundational

```bash
# After T003 completes, launch both readers together:
Task: "Implement builders plus list methods on SdkGateway in src/deck/docker_sdk.py"
Task: "Add read-only list services in src/deck/services.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently (menu order, switching, highlight)
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
