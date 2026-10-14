---

description: "Task list template for feature implementation"
---

# Tasks: Image Run Menu

**Input**: Design documents from `/specs/006-image-run-menu/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — SC-005 requires 100% automated test coverage of core functionality (name, ports, volumes, network, envs, start, cancel).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project: `src/`, `tests/` at repository root (per plan.md Project Structure).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module scaffolding and test scaffolding for the run menu feature

- [X] T001 Create `src/deck/tui/run_config.py` module skeleton with a `RunConfigScreen` placeholder class per plan.md project structure
- [X] T002 [P] Create unit test scaffolds `tests/unit/test_run_config.py` (validation logic) and `tests/unit/test_run_config_screen.py` (TUI behavior)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Add `PortMapping` (`host_port: str`, `container_port: str`), `VolumeMount` (`source_path: str`, `container_path: str`), `EnvVar` (`key: str`, `value: str`) dataclasses, `ContainerRunRequest` dataclass (fields per contracts/container-run-api.yml: `image`, `name`, `ports`, `volumes`, `network`, `env_vars`), and a `create_and_run_container(request: ContainerRunRequest) -> str` method declaration on the `DockerGateway` protocol in src/deck/docker_gateway.py
- [X] T004 Implement `SdkGateway.create_and_run_container` in src/deck/docker_sdk.py using `client.containers.run(image, detach=True, ports=..., volumes=..., environment=..., network=...)` per research.md decision (depends on T003)
- [X] T005 Add `pull_image(image: str)` helper to `SdkGateway` in src/deck/docker_sdk.py calling `client.images.pull(image)`, designed to be invoked via `asyncio.to_thread()` so it never blocks the TUI event loop (Constitution §V)
- [X] T006 [P] Add validation helpers to src/deck/services.py: `validate_name` (reject empty/whitespace-only), `parse_port_mapping` (must match `host_port:container_port`, e.g. "8080:80"), `parse_volume_mount` (must match `source_path:container_path`, e.g. "/data:/app/data"), `parse_env_var` (must match `KEY=value`), and `suggest_unique_name(existing_names, base)` appending a numeric suffix (e.g. "myapp-2") per spec Clarifications
- [X] T007 Map Docker SDK failures to contract error codes (`ImageNotFound`, `NameCollision`, `InvalidPortFormat`, `InvalidVolumeFormat`, `DaemonUnavailable`) with actionable user-facing messages in src/deck/services.py (depends on T006)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Launch a Container with Basic Options (Priority: P1) 🎯 MVP

**Goal**: User opens the run configuration menu from the Images view, enters a name, reviews a confirmation screen, and the container is created and started in detached mode with notification and view refresh

**Independent Test**: Open the Images view, select an image, press the Run action, enter a name, confirm on the review screen, and verify a new container appears in the Containers view; press Esc to verify cancel creates nothing

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T008 [P] [US1] Unit tests for name validation (empty, whitespace-only, valid) and `suggest_unique_name` collision suggestion in tests/unit/test_run_config.py
- [X] T009 [P] [US1] TUI tests: Run action on Images view pushes `RunConfigScreen` with all five fields (name, ports, volumes, network, env vars); Esc closes without creating a container in tests/unit/test_run_config_screen.py

### Implementation for User Story 1

- [X] T010 [US1] Implement `RunConfigScreen` modal overlay in src/deck/tui/run_config.py displaying fields for name, ports, volumes, network, and environment variables per spec acceptance scenario 1 (depends on T001, T003)
- [X] T011 [US1] Add dedicated "Run" action on the Images view (Enter on a selected image per acceptance scenario 1) that pushes `RunConfigScreen`, keyboard-only per Constitution §IV, in src/deck/tui/app.py
- [X] T012 [US1] Implement confirmation review screen summarizing name, ports, volumes, network, and env vars shown before ANY Docker API call (FR-007, Constitution §III) in src/deck/tui/run_config.py
- [X] T013 [US1] Enable the start action only when a valid name is provided (FR-011) and reject colliding names with error "Container name '<name>' already exists" plus a numeric-suffix suggestion (e.g. `nginx-test-1`), keeping the form open (depends on T006, T007)
- [X] T014 [US1] On confirm, dispatch the run request through the service/adapter layer via `asyncio.to_thread()` so the TUI event loop is not blocked; on failure show an actionable notification and keep the form open for retry (state `error` per data-model.md) in src/deck/tui/run_config.py (depends on T004)
- [X] T015 [US1] When the selected image is not available locally, pull it in the background via `asyncio.to_thread()` and show a success/failure notification on completion ("Image <name> pulled successfully" / "Failed to pull image <name>. Check network.") without freezing the TUI in src/deck/tui/run_config.py (depends on T005)
- [X] T016 [US1] On successful creation, show notification "Container <name> started successfully" and switch to / refresh the Containers view so the new container is visible (FR-009) in src/deck/tui/app.py (depends on T014)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently (MVP)

---

## Phase 4: User Story 2 - Configure Port Mappings (Priority: P2)

**Goal**: User can add, edit, and remove multiple port mappings that are applied to the created container; empty list means no port mappings

**Independent Test**: Add port mappings (e.g. "8080:80") in the configuration menu, launch the container, and verify the container runs with those port mappings; launch with no ports and verify none are applied

### Tests for User Story 2

- [X] T017 [P] [US2] Unit tests for port list add/remove/edit and `host_port:container_port` validation (valid "8080:80", invalid "abc:80") in tests/unit/test_run_config_ports.py
- [X] T018 [P] [US2] TUI test: launching with multiple port mappings passes all of them into the `ContainerRunRequest` given to a fake gateway; empty list passes no ports in tests/unit/test_run_config_screen_ports.py

### Implementation for User Story 2

- [X] T019 [P] [US2] Implement add (Enter/Space), remove, and edit behavior for list fields with Vim-style navigation (j/k) on the ports list in src/deck/tui/widgets.py per Constitution §IV and FR-010
- [X] T020 [US2] Wire the ports list into the run flow: parse each entry with `parse_port_mapping`, reject invalid syntax with `InvalidPortFormat` message ("Invalid port mapping format: 'abc:80'. Use host_port:container_port") keeping the form open, and allow an empty list (default: no port mappings) in src/deck/tui/run_config.py (depends on T017, T019)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Configure Volumes and Environment Variables (Priority: P3)

**Goal**: User can add volume mounts and environment variables; env var values are visible in the confirmation review so sensitive data can be verified before committing

**Independent Test**: Add volume entries ("/data:/app/data") and env entries ("DEBUG=true"), launch, and verify the container runs with them; check the confirmation screen displays env values

### Tests for User Story 3

- [X] T021 [P] [US3] Unit tests for volume (`source_path:container_path`, invalid "/data" rejected) and env var (`KEY=value`, invalid "DEBUG" rejected) parsing with `InvalidVolumeFormat`/env errors in tests/unit/test_run_config_volumes_envs.py
- [X] T022 [P] [US3] TUI test: volume and env entries appear in their list fields and reach the `ContainerRunRequest`; confirmation review shows env var values in tests/unit/test_run_config_screen_volumes_envs.py

### Implementation for User Story 3

- [X] T023 [US3] Reuse the list field widget from src/deck/tui/widgets.py for volumes and env vars (add/remove/edit, j/k navigation) in src/deck/tui/run_config.py (depends on T019)
- [X] T024 [US3] Wire volumes and env lists into the run flow: parse with `parse_volume_mount`/`parse_env_var`, reject invalid entries with actionable messages keeping the form open, allow empty lists (default behavior), and pass them to the `ContainerRunRequest` in src/deck/tui/run_config.py (depends on T021, T023)
- [X] T025 [US3] Display environment variable values (not just keys) on the confirmation review screen so the user can verify sensitive data before committing (spec acceptance scenario 3) in src/deck/tui/run_config.py (depends on T012)

**Checkpoint**: User Stories 1, 2, and 3 all work independently

---

## Phase 6: User Story 4 - Select a Network (Priority: P3)

**Goal**: User can attach the container to a specific Docker network, or leave it empty to use the default bridge network

**Independent Test**: Type a network name in the configuration menu and verify the container is created on that network; leave it blank and verify the container lands on the default bridge network

### Tests for User Story 4

- [X] T026 [P] [US4] Unit tests: empty network field → no network passed (default bridge); specified network name passed through to the `ContainerRunRequest`; unknown network name rejected with actionable error in tests/unit/test_run_config_network.py

### Implementation for User Story 4

- [X] T027 [US4] Implement the network text input (FR-005), display it on the confirmation review, and pass it to the `ContainerRunRequest` (empty → default Docker bridge network) in src/deck/tui/run_config.py (depends on T012)
- [X] T028 [US4] Validate a specified network name against `DockerGateway.list_networks()` and show an actionable error keeping the form open when it does not exist (data-model.md: network "Must match an existing network name, or empty (default bridge)") in src/deck/tui/run_config.py (depends on T027)

**Checkpoint**: All user stories should now be independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T029 [P] Document the Run menu in README.md: purpose, fields, keyboard shortcuts, failure modes (name collision, invalid formats, pull failure, daemon unavailable), and security note on env var visibility per Constitution Documentation
- [X] T030 [P] Redact sensitive env var values from debug logs in src/deck/logging_setup.py and src/deck/services.py per Constitution Security Principles (never log credentials)
- [X] T031 Validate the feature against all quickstart.md scenarios 1-7 (name only, ports, volume, env, name collision, invalid port, background pull) and record results (see Validation Results below; live-daemon scenarios blocked by environment — automated equivalents pass)
- [X] T032 Run full quality gate: `pytest --cov=src/deck` achieving SC-005 coverage of core functionality, `ruff check`, `ruff format --check`, and `mypy src/deck` per pyproject.toml
- [X] T033 Code cleanup and refactoring pass across run menu code in src/deck/tui/run_config.py, src/deck/tui/widgets.py, src/deck/services.py (dead ContainerCreateScreen removed, unused imports cleared, files formatted)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (P1) first → MVP
  - US2 (P2) and US3/US4 (P3) can proceed in parallel after US1, or in priority order (P1 → P2 → P3)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2); reuses list widget work with US1's screen (independently testable)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2); depends on the list field widget introduced in T019 (US2) and the confirmation screen from T012 (US1) — both are small, isolated increments
- **User Story 4 (P3)**: Can start after Foundational (Phase 2); depends on the confirmation screen from T012 (US1)

### Within Each User Story

- Tests written FIRST and verified to FAIL before implementation
- Data types/services (Phase 2) before screens
- Form fields before confirmation screen before dispatch
- Core implementation before integration/notification
- Story complete before moving to next priority

### Parallel Opportunities

- T001 + T002 (Setup) in parallel
- T003, T005, T006 (different files: docker_gateway.py, docker_sdk.py pull helper is sequential after T004 — T003 ∥ T006) after T001
- T008 ∥ T009 (US1 tests, different files)
- T017 ∥ T018 (US2 tests, different files) ∥ T019 (widgets.py)
- T021 ∥ T022 (US3 tests, different files)
- US2, US3, US4 test tasks can all run in parallel with each other (all different files)
- T029 ∥ T030 (Polish, different files)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit tests for name validation in tests/unit/test_run_config.py"
Task: "TUI tests for Run action and Esc cancel in tests/unit/test_run_config_screen.py"

# Then implementation (run_config.py tasks are sequential; app.py task is independent):
Task: "Add Run action on Images view in src/deck/tui/app.py"
```

## Parallel Example: User Stories 2, 3, 4 (after US1)

```bash
Task: "Unit tests for port mapping validation in tests/unit/test_run_config_ports.py"
Task: "Unit tests for volume/env validation in tests/unit/test_run_config_volumes_envs.py"
Task: "Unit tests for network selection in tests/unit/test_run_config_network.py"
Task: "List field widget in src/deck/tui/widgets.py"
# All different files - safe to run concurrently
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently (quickstart Scenario 1, 5, 7)
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add User Story 4 → Test independently → Deploy/Demo
6. Polish → full quality gate (quickstart scenarios 1-7, coverage SC-005)

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (MVP)
   - Developer B: User Story 2 (tests + widgets.py)
   - Developer C: User Story 3 and 4 tests (all separate test files)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Constitution gates: §III confirmation screen before any Docker call (T012), §IV keyboard-only (T011, T019), §V non-blocking pull/create (T014, T015), §VI single Run action with defaults (T010)

---

## Validation Results (T031)

Live-daemon quickstart scenarios could not be executed in the implementation environment (no permission to access the Docker socket). Automated equivalents validate the same behavior without a daemon:

| Quickstart Scenario | Automated Equivalent | Result |
|---|---|---|
| 1. Name only | `test_confirm_creates_and_starts_container` | PASS |
| 2. Port mapping | `test_multiple_port_mappings_reach_gateway` | PASS |
| 3. Volume | `test_volumes_and_envs_reach_gateway` | PASS |
| 4. Environment variable | `test_volumes_and_envs_reach_gateway`, `test_review_shows_env_values_before_confirm` | PASS |
| 5. Name collision + suggestion | `test_name_collision_shows_error_and_suggestion` | PASS |
| 6. Invalid port syntax | `test_invalid_port_entry_shown_and_not_added` | PASS |
| 7. Background pull (success/failure) | `test_missing_local_image_pulls_in_background_then_runs`, `test_pull_failure_shows_error_and_keeps_form_open` | PASS |

Remaining manual step on a machine with Docker access: run `deck`, exercise scenarios 1–7 live per quickstart.md.

## Quality Gate Status (T032)

- `ruff check`: All checks passed (src + new tests)
- `mypy src/deck`: 8 errors — all pre-existing at base commit (app.py list-variance, screens.py untyped-def); no new errors introduced
- `pytest tests/unit`: 143 passed, 6 failed — all 6 failures pre-existing at base commit (verified via `git stash`)
- Coverage: 78.76% overall (base was 73.03%); the repo's `--cov-fail-under=80` gate was already failing before this feature. All core run-menu functionality (name, ports, volumes, network, envs, start, cancel — SC-005) is covered by the new test files.
