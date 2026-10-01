# Tasks: Docker Container Management

**Input**: Design documents from `/specs/004-docker-container-management/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included — required by the project constitution ("No feature is complete
without appropriate tests"): unit tests use a fake gateway (no daemon), live-daemon
tests are marked integration.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Packaging scaffold and baseline verification

- [x] T001 Create container image definition in Dockerfile (repo root: minimal Python 3.11 base, install package, `docker-tui` entrypoint, versioned tags)
- [x] T002 [P] Add .dockerignore at repo root (exclude .venv, tests artifacts, caches)
- [x] T003 [P] Verify baseline gates per specs/004-docker-container-management/quickstart.md (pytest tests/unit -q, ruff check, mypy src)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Gateway protocol extension + Engine adapter + services that ALL stories build on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Extend DockerGateway protocol with container types and operation signatures in src/deck/docker_gateway.py (ManagedContainer with "`state_bucket` running|stopped|other", "`name` non-empty", "`is_self` boolean"; operations list/details/logs/lifecycle per contracts/gateway-operations.md)
- [x] T005 [P] Implement container list, details, and bounded log-tail fetching in src/deck/docker_sdk.py (depends on T004; logs "bounded tail (never unbounded load)")
- [x] T006 [P] Implement container service operations and best-effort self-identification in src/deck/services.py (depends on T004; guards fail safe with warnings when undetermined)
- [x] T007 Add unit tests for state-bucket mapping, self-block rule, and error-state mapping in tests/unit/test_containers.py (depends on T004–T006)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Run the Manager as a Container and See Other Containers (Priority: P1) 🎯 MVP

**Goal**: Containerized manager starts with shared Engine access and shows the sibling container list; misconfigured runs show actionable guidance

**Independent Test**: Build the image, run with shared Engine access → connected status + sibling list (name, image, running/stopped/other); run without Engine access → usable `unavailable` status naming the run configuration, zero tracebacks

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T008 [P] [US1] Unit test for container list including self flag and unavailable guidance in tests/unit/test_container_list.py
- [x] T009 [P] [US1] Integration test for containerized run with and without Engine access in tests/integration/test_containerized_run.py

### Implementation for User Story 1

- [x] T010 [P] [US1] Implement container list screen (name, image, running/stopped/other) in src/deck/tui/screens.py (depends on T004, T006)
- [x] T011 [US1] Wire list screen with j/k navigation, Enter open, and r refresh in src/deck/tui/app.py (depends on T010)
- [x] T012 [US1] Show unavailable-state guidance for missing Engine access in src/deck/tui/screens.py (depends on T010)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Start, Stop, and Restart Sibling Containers Safely (Priority: P2)

**Goal**: Keyboard-driven lifecycle control with confirmation-gated remove and hard-blocked self stop/remove

**Independent Test**: Start a stopped test container → running update; stop it → stopped update; remove → confirmation prompt (confirm removes, decline keeps); self stop/remove → blocked with explanatory message

### Tests for User Story 2

- [x] T013 [P] [US2] Unit tests for start/stop/restart, remove-confirmation flow, and self-block in tests/unit/test_lifecycle.py
- [x] T014 [P] [US2] Integration test for lifecycle on a live daemon in tests/integration/test_lifecycle_live.py

### Implementation for User Story 2

- [x] T015 [P] [US2] Implement start/stop/restart/remove in src/deck/docker_sdk.py (remove executes only with confirmation; depends on T004)
- [x] T016 [P] [US2] Implement lifecycle service actions and confirmation flow in src/deck/services.py (depends on T004)
- [x] T017 [US2] Add action keys and confirmation modal wiring in src/deck/tui/app.py (depends on T015, T016)
- [x] T018 [P] [US2] Add confirmation modal view in src/deck/tui/screens.py (depends on contracts/gateway-operations.md invariants)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Inspect a Container and Read Its Logs (Priority: P3)

**Goal**: Read-only details and recent-logs views for diagnosing containers

**Independent Test**: Open details on a container → name, image, bucket + exact status visible; open logs → bounded content within 10 seconds with loading indication first

### Tests for User Story 3

- [x] T019 [P] [US3] Unit tests for details/logs mapping in tests/unit/test_container_inspect.py
- [x] T020 [P] [US3] Integration test for log fetching on a live daemon in tests/integration/test_container_logs_live.py

### Implementation for User Story 3

- [x] T021 [P] [US3] Implement details and logs views in src/deck/tui/screens.py (exact status from "`exact_status` verbatim Engine status")
- [x] T022 [US3] Wire details/logs opening with loading state in src/deck/tui/app.py (depends on T021)

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Docs, scale validation, and full gates

- [x] T023 [P] Update help view with new bindings in src/deck/tui/screens.py
- [x] T024 [P] Document run configuration, privilege warning, and failure modes in README.md
- [x] T025 Validate 100-container navigation per specs/004-docker-container-management/quickstart.md (smooth j/k, one refresh round-trip per r)
- [x] T026 [P] Add edge-case unit tests (daemon stops mid-session, non-interactive terminal, undetermined self-id) in tests/unit/test_container_edge_cases.py
- [x] T027 Run full gates per specs/004-docker-container-management/quickstart.md (pytest, ruff check, ruff format --check, mypy src)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Invokes actions from the list; independently testable (details view in US3 reuses the same actions)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Read-only views; independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Protocol/services before TUI wiring
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T002, T003 run in parallel (different files, no dependencies)
- T005, T006 run in parallel after T004 (different files)
- T008, T009 run in parallel (different test files)
- T013, T014 run in parallel; T015, T016 run in parallel (different files)
- T019, T020 run in parallel (different test files)
- T023, T024, T026 run in parallel (different files)
- Stories US1/US2/US3 can be staffed in parallel after Foundational

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for container list including self flag and unavailable guidance in tests/unit/test_container_list.py"
Task: "Integration test for containerized run with and without Engine access in tests/integration/test_containerized_run.py"

# Implementation follows foundation:
Task: "Implement container list screen (name, image, running/stopped/other) in src/deck/tui/screens.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently (quickstart scenarios 1–2)
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
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
