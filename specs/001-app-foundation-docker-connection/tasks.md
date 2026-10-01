# Tasks: Application Foundation and Docker Connection

**Input**: Design documents from `specs/001-app-foundation-docker-connection/`
(`plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`)

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Spec explicitly requests tests (connection success/unavailable/permission failure, info retrieval, config, startup/shutdown, refresh) — test tasks included; write tests FIRST and ensure they FAIL before implementation.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project: `src/deck/`, `tests/unit/`, `tests/integration/` at repository root (per plan.md).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project structure per plan.md (`src/deck/`, `src/deck/tui/`, `tests/unit/`, `tests/integration/`, `specs/001-app-foundation-docker-connection/contracts/`)
- [x] T002 Initialize Python project with hatchling backend and console script in `pyproject.toml` (`requires-python>=3.11`, `textual~=8.2`, `docker==7.2.0`, `platformdirs>=4.3`, dev `pytest>=8.3 pytest-asyncio>=0.26 pytest-cov>=6 ruff>=0.12 mypy~=1.18`, `[project.scripts] docker-tui`)
- [x] T003 [P] Configure linting/formatting/type tooling in `pyproject.toml` (`ruff check`, `ruff format`, `mypy --strict` over `src/`, pytest `asyncio_mode=auto`)
- [x] T004 [P] Configure pytest markers and coverage in `pyproject.toml` (`integration` marker, `--cov=src --cov-fail-under=80`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Define `ConnectionState` enum and `DockerGateway` protocol in `src/deck/docker_gateway.py` (states verbatim: one of `connected`, `unavailable`, `permission-denied`, `connection-failed`; method `get_snapshot() -> (ConnectionState, DockerSystemSummary | None, detail: str)`; MUST NOT leak SDK types)
- [x] T006 [P] Implement validated `ApplicationConfiguration` dataclass with defaults in `src/deck/config.py` (TOML via stdlib `tomllib`, path `platformdirs.user_config_path("docker-tui")/config.toml`, per-field fallback with user notice, never crash on `TOMLDecodeError`/`OSError`; local-only endpoint rule)
- [x] T007 [P] Implement stdlib logging with redaction filter in `src/deck/logging_setup.py` (FileHandler at `platformdirs.user_log_path("docker-tui")/docker-tui.log` + console; `--debug` selects DEBUG else INFO; filter redacts `password|token|secret|authorization` to `***REDACTED***` on both handlers)
- [x] T008 Implement `SdkGateway` in `src/deck/docker_sdk.py` as the ONLY module importing `docker` (init `docker.from_env()` with short timeout and local-only guard `use_context=False`; sequence `ping()` → `version()` → `info()`; map failures per contracts error table; unknown errors → `connection-failed` with redacted message)
- [x] T009 Implement refresh/status service over the protocol in `src/deck/services.py` (synchronous blocking call intended for Textual worker thread; returns frozen snapshot dataclass per `data-model.md`)
- [x] T010 Implement CLI entry point in `src/deck/cli.py` (`docker-tui` with `--debug` and `--config <path>` flags; renders layout before probe; exit `0` on clean quit, non-zero only on fatal init with concise message)

**Checkpoint**: Foundation ready — `DockerGateway` seam, config, logging, SDK adapter, service, CLI all importable; user story implementation can now begin.

---

## Phase 3: User Story 1 — Launch and See Docker Status (Priority: P1) 🎯 MVP

**Goal**: User launches one command and immediately sees connection status plus mandatory Engine summary.

**Independent Test**: With Docker running, launch `docker-tui` and observe `connected` status with version, OS/arch, container total/running/stopped, image count (API version when available) within 10s on an 80x24 terminal and after resize (quickstart §1).

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T011 [P] [US1] Unit test for connection success snapshot in `tests/unit/test_docker_gateway.py` (faked gateway returns `connected` with version/OS/arch/counts per `data-model.md` validation: counts are non-negative ints, `running + stopped ≤ total`)
- [x] T012 [P] [US1] Unit test for info retrieval field mapping in `tests/unit/test_info_mapping.py` (`Version`→version, `ApiVersion`→api_version, `Os`/`Arch`, `Containers`/`ContainersRunning`/`ContainersStopped`/`Images`; missing `api_version` → null displayed as unavailable)
- [x] T013 [P] [US1] Integration test for launch-with-Docker-running in `tests/integration/test_startup_live.py` (`-m integration`, Textual Pilot `run_test()`: header/status/footer visible, summary values populated)

### Implementation for User Story 1

- [x] T014 [P] [US1] Create status screen layout in `src/deck/tui/screens.py` (header, Docker Status area with mandatory fields: Engine version, OS/platform, architecture, container counts total/running/stopped, image count, API version if available else unavailable, footer with shortcut hints)
- [x] T015 [P] [US1] Create status/error/loading row widgets in `src/deck/tui/widgets.py` (loading indicator for slow probe; missing fields shown as unavailable, never blank/crash)
- [x] T016 [US1] Wire Textual App startup in `src/deck/tui/app.py` (render layout first, probe Docker in worker thread via service, populate status; depends on T014, T015, T009)
- [x] T017 [US1] Add startup logging for status probe in `src/deck/services.py` (log endpoint probed + state at INFO, full chain at DEBUG through redaction filter)

**Checkpoint**: US1 fully functional — `docker-tui` with live daemon shows complete Engine summary; testable independently.

---

## Phase 4: User Story 2 — Understand Docker Problems Without a Crash (Priority: P1)

**Goal**: Stopped/missing/permission-restricted daemon yields a usable actionable error screen, never a crash or traceback.

**Independent Test**: Stop daemon or revoke socket access, launch app, verify usable `unavailable` / distinct `permission-denied` screens with next-step guidance and zero tracebacks in normal mode (quickstart §2).

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T018 [P] [US2] Unit test for daemon-unavailable mapping in `tests/unit/test_docker_gateway.py` (missing socket `FileNotFoundError` ENOENT / `DockerException: Error while fetching server API version` → `unavailable` with remediation detail)
- [x] T019 [P] [US2] Unit test for permission-denied mapping in `tests/unit/test_docker_gateway.py` (`PermissionError` EACCES in `__cause__`/`__context__` chain or `permission denied` substring → `permission-denied` distinctly from `connection-failed`)
- [x] T020 [P] [US2] Unit test for connection-failed fallback in `tests/unit/test_docker_gateway.py` (refused/reset, `requests.ConnectionError`, `APIError(5xx)`, unknown → `connection-failed`, no SDK types leak)

### Implementation for User Story 2

- [x] T021 [US2] Implement error-state rendering in `src/deck/tui/screens.py` (status + cause category + next-step guidance for each of `unavailable`, `permission-denied`, `connection-failed`; normal mode hides tracebacks; depends on T014)
- [x] T022 [US2] Harden startup/shutdown paths in `src/deck/tui/app.py` (failed probe never blocks render; fatal init errors exit non-zero with concise message; terminal restored)

**Checkpoint**: US1 AND US2 both work — connected and all three failure states verified independently.

---

## Phase 5: User Story 3 — Refresh Docker Information by Keyboard (Priority: P2)

**Goal**: Pressing `r` re-queries Docker (manual-only, no timers) with loading state while the UI stays responsive.

**Independent Test**: Change Docker state externally, press `r`, observe updated counts or clear error; input and quit stay live with keypress ack <1s (quickstart §3).

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T023 [P] [US3] Unit test for refresh state transitions in `tests/unit/test_services.py` (any state → any state on manual refresh; pre-probe initial state is `unavailable` with `detail="Probing…"`)
- [x] T024 [P] [US3] Integration test for manual refresh via Pilot in `tests/integration/test_refresh_live.py` (`-m integration`: `press("r")`, external state change reflected, failed refresh keeps previous display unbroken with actionable error)

### Implementation for User Story 3

- [x] T025 [US3] Bind `r` to worker-thread refresh in `src/deck/tui/app.py` (dispatches `services` refresh off render loop with timeout; shows loading indicator when slow; manual-only — no timers/interval config; depends on T016)
- [x] T026 [US3] Handle mid-session daemon stop/permission loss in `src/deck/services.py` (next refresh returns `unavailable` / distinct `permission-denied` without freeze)

**Checkpoint**: Refresh loop verified — live state changes surface correctly without blocking input.

---

## Phase 6: User Story 4 — Navigate, Get Help, and Quit Cleanly (Priority: P2)

**Goal**: Keyboard-only operation with `j/k/?/q/Esc`, on-screen help, and clean termination restoring the terminal.

**Independent Test**: Keyboard-only run — `j`/`k` move, `?` opens help listing `j/k r ? q Esc`, `Esc`/`q` closes help, `q` quits promptly with terminal restored; SIGTERM during refresh also exits cleanly (quickstart §4).

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T027 [P] [US4] TUI test for Vim movement and help open/close in `tests/unit/test_tui_keys.py` (Pilot: `j`/`k` move selection visibly; `?` opens help, `Esc`/`q` closes and returns focus — no daemon needed via `FakeGateway`)
- [x] T028 [P] [US4] TUI test for clean quit and signal handling in `tests/unit/test_shutdown.py` (`q` terminates promptly releasing Docker/background resources and restoring terminal; termination signal during refresh cleans up)

### Implementation for User Story 4

- [x] T029 [US4] Declare baseline bindings in `src/deck/tui/app.py` (`j` down, `k` up, `r` refresh, `?` help, `q` quit, `Esc` close/cancel; resize reflows without overlap at ≥80x24; keyboard-only acceptance, mouse optional)
- [x] T030 [US4] Implement help modal in `src/deck/tui/screens.py` (lists all shortcuts; `Esc`/`q` closes with focus return; depends on T014)

**Checkpoint**: Baseline interaction language complete — every later screen inherits these bindings.

---

## Phase 7: User Story 5 — Persist Minimal Preferences Across Runs (Priority: P3)

**Goal**: Docker endpoint choice (local-only), display preference, and debug flag persist with safe defaults and per-field fallback.

**Independent Test**: Edit config, relaunch, observe retained behavior; corrupt file or bad value falls back per-field with notice and startup continues; `--debug` adds on-screen diagnostics while log file holds complete redacted detail (quickstart §5).

### Tests for User Story 5

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T031 [P] [US5] Unit test for config defaults and persistence in `tests/unit/test_config.py` (no file → defaults; valid edits survive relaunch; schema `[docker] endpoint`, `[display] theme = "dark" | "light"`, `[logging] debug = bool`)
- [x] T032 [P] [US5] Unit test for per-field fallback in `tests/unit/test_config.py` (invalid TOML / bad single value → defaults for that field only, startup continues, user informed; unknown keys ignored; remote endpoint values rejected with notice)
- [x] T033 [P] [US5] Unit test for log redaction filter in `tests/unit/test_logging.py` (values matching `password|token|secret|authorization` rendered `***REDACTED***` on both handlers; raw env/args never logged)

### Implementation for User Story 5

- [x] T034 [US5] Wire config load/merge into startup in `src/deck/cli.py` (apply `--config` override, per-field `dict.get(key, default)` merge, notice on ignored values; depends on T006, T010)
- [x] T035 [US5] Wire debug verbosity in `src/deck/tui/screens.py` (debug shows human-readable cause + endpoint probed + hints with secrets redacted; log file always has complete detail; normal mode stays concise; depends on T021)

**Checkpoint**: All user stories independently functional — config loop closed.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting multiple user stories

- [x] T036 [P] Update user documentation in `README.md` (install via `pip install -e ".[dev]"`, `docker-tui` usage, keyboard table, config path, debug/log behavior — actual implemented behavior only)
- [x] T037 Run full `quickstart.md` validation scenarios in `specs/001-app-foundation-docker-connection/quickstart.md` (launch, unavailable, refresh, keys/help/quit, config/debug, quality gates)
- [x] T038 [P] Harden tiny-terminal and partial-info edge cases in `src/deck/tui/screens.py` (60x15 reflow, resize mid-display, partial Engine payloads → unavailable labels per edge cases)
- [x] T039 Verify quality gates: `pytest tests/unit -q`, `pytest -m "not integration" -q`, `ruff check .`, `ruff format --check .`, `mypy src` (all green; integration suite skipped without daemon)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - Then proceed in priority order (P1 → P2 → P3) or in parallel if staffed
  - Or sequentially in priority order (US1 → US2 → US3 → US4 → US5)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Foundational — no dependencies on other stories
- **User Story 2 (P1)**: Starts after Foundational — integrates with US1 screens (`screens.py`) but independently testable via distinct error states
- **User Story 3 (P2)**: Starts after Foundational — builds on US1 App wiring (`app.py`) but testable as standalone refresh loop
- **User Story 4 (P2)**: Starts after Foundational — builds on US1 screens/App but testable keyboard-only with faked gateway
- **User Story 5 (P3)**: Starts after Foundational — wires into CLI/screens but testable as standalone config loop

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/protocols before services
- Services before UI wiring
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- Phase 1: T003, T004 parallel (different config sections)
- Phase 2: T006, T007 parallel (config vs logging, different files)
- US1 tests T011–T013 all parallel (different files/markers); T014–T015 parallel (screens vs widgets)
- US2 tests T018–T020 all parallel (same file different cases — can split across runs)
- US3 tests T023–T024 parallel; US4 tests T027–T028 parallel; US5 tests T031–T033 parallel
- Across stories (post-Foundational): US1+US2+US3+US4+US5 implementable in parallel by separate developers (shared-file merges at `app.py`/`screens.py` need coordination)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for connection success snapshot in tests/unit/test_docker_gateway.py"
Task: "Unit test for info retrieval field mapping in tests/unit/test_info_mapping.py"
Task: "Integration test for launch-with-Docker-running in tests/integration/test_startup_live.py"

# Launch all UI pieces for User Story 1 together:
Task: "Create status screen layout in src/deck/tui/screens.py"
Task: "Create status/error/loading row widgets in src/deck/tui/widgets.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test US1 independently per quickstart §1 (`docker-tui` shows Engine summary <10s)
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. Add US1 → test independently → demo (MVP!)
3. Add US2 → test independently → demo (trust on broken systems)
4. Add US3 → test independently → demo (live refresh loop)
5. Add US4 → test independently → demo (keyboard language)
6. Add US5 → test independently → demo (config loop)
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (status display) + US3 (refresh loop)
   - Developer B: US2 (error states) + US4 (keys/help/quit)
   - Developer C: US5 (config/debug)
3. Stories complete and integrate independently (coordinate `app.py`/`screens.py` merges)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
- FR-014 guard: no task introduces container/image/network/volume/Compose/AI scope
