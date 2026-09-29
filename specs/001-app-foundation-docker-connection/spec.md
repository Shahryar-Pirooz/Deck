# Feature Specification: Application Foundation and Docker Connection

**Feature Branch**: `001-app-foundation-docker-connection`

**Created**: 2026-09-29

**Status**: Draft

**Input**: User description: "Build the initial foundation of the Docker TUI Manager — minimal functional terminal app that starts, connects to local Docker Engine, displays system information and connection status, with config foundation, Vim navigation, error handling, and clean shutdown. No container/image/network/volume/Compose/AI management in this feature."

## Clarifications

### Session 2026-09-29

- Q: What Docker connection targets must the foundation release support? → A: Local socket only
- Q: Should the status screen update automatically on a timer, or only when the user presses refresh? → A: Manual refresh only
- Q: What extra detail must debug mode reveal when Docker fails? → A: Human-readable cause + connection diagnostics plus log file with complete detail
- Q: Which Engine facts are mandatory for the connected status screen to pass acceptance? → A: Version + counts + platform (API version if available)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Launch and See Docker Status (Priority: P1)

A Linux terminal user launches the manager with a single terminal command and immediately
sees whether Docker is available plus basic Engine information.

**Why this priority**: This is the core value of the foundation — without reliable startup
and status display, no future management feature can be built or validated.

**Independent Test**: Can be fully tested by launching the app on a machine with Docker
running and observing connection status and system summary. Delivers a working status
dashboard with no other features.

**Acceptance Scenarios**:

1. **Given** Docker Engine is running and accessible, **When** the user launches the app,
   **Then** the main screen shows connected status with Engine version, OS/arch, container
   counts (total/running/stopped), and image count.
2. **Given** the app is launched, **When** startup completes, **Then** the header, status
   area, and footer with shortcut hints are visible and correctly laid out on an 80x24
   terminal and after resize.

---

### User Story 2 - Understand Docker Problems Without a Crash (Priority: P1)

A user whose Docker daemon is stopped, missing, or permission-restricted launches the app
and gets a clear, actionable explanation instead of a crash or traceback.

**Why this priority**: Reliability when Docker is unavailable is a constitution-level
safety and error-handling requirement; first-run environments frequently lack permission.

**Independent Test**: Can be fully tested by stopping the daemon or revoking socket access,
launching the app, and verifying a usable error screen. Delivers trust on broken systems.

**Acceptance Scenarios**:

1. **Given** Docker is unavailable (daemon stopped / socket missing), **When** the user
   launches the app, **Then** the app stays usable, shows unavailable status with guidance
   to check that Docker is running and socket permissions, and hides raw tracebacks.
2. **Given** the user lacks permission to access Docker, **When** the app probes Docker,
   **Then** it reports permission-denied distinctly from generic connection failure with
   next-step guidance.

---

### User Story 3 - Refresh Docker Information by Keyboard (Priority: P2)

A user presses a single key to re-query Docker and update the display while the interface
stays responsive.

**Why this priority**: Docker state changes externally; manual refresh validates the
non-blocking query loop required by all future live views.

**Independent Test**: Can be fully tested by changing Docker state externally (e.g.,
starting/stopping a container), pressing refresh, and observing updated counts.
Delivers a live-verified status loop.

**Acceptance Scenarios**:

1. **Given** the status screen is shown, **When** the user presses `r`, **Then** the app
   re-queries Docker, shows a loading indication if the query takes noticeable time, and
   updates displayed information or error state.
2. **Given** a refresh fails, **When** the query errors, **Then** the previous display is
   not left in a broken state and a clear, actionable error is shown.

---

### User Story 4 - Navigate, Get Help, and Quit Cleanly (Priority: P2)

A keyboard-first user navigates the status view with Vim keys, opens help, and quits
without leftover processes or broken terminal state.

**Why this priority**: Establishes the keyboard-first, TUI-first contract (constitution
Principles IV–V) for every later screen.

**Independent Test**: Can be fully tested with keyboard only: move, open help, close help,
quit. Delivers the baseline interaction language.

**Acceptance Scenarios**:

1. **Given** the main screen is focused, **When** the user presses `j`/`k`, **Then**
   selection/focus moves down/up visibly.
2. **Given** the main screen is shown, **When** the user presses `?`, **Then** a help view
   listing `j/k`, `r`, `?`, `q`, `Esc` appears; **When** the user presses `Esc` or `q`,
   **Then** help closes and focus returns.
3. **Given** the app is running, **When** the user presses `q`, **Then** the app terminates
   promptly, restores the terminal, and releases Docker/background resources.

---

### User Story 5 - Persist Minimal Preferences Across Runs (Priority: P3)

A returning user has their Docker endpoint choice, display preference, and debug flag
remembered with safe defaults on first run.

**Why this priority**: Configuration foundation unblocks future themes, keybindings, and
multi-endpoint support without overbuilding now.

**Independent Test**: Can be fully tested by editing config, relaunching, and observing
retained behavior; invalid config falls back to defaults with a message. Delivers a
validated config loop.

**Acceptance Scenarios**:

1. **Given** no config exists, **When** the user launches the app, **Then** sensible
   defaults are used and startup succeeds.
2. **Given** config contains an invalid value, **When** the app starts, **Then** it uses
   defaults for the invalid part, continues startup, and informs the user what was
   ignored.

### Edge Cases

- Docker daemon stops after successful startup — next refresh shows unavailable state
  without crash or freeze.
- Docker socket exists but permission denied mid-session — refresh reports
  permission-denied distinctly.
- Very slow Docker response — UI shows loading state and remains navigable; user can
  cancel/quit.
- Tiny terminal (e.g., 60x15) or resize during display — layout reflows without overlap
  or crash; content remains reachable.
- Invalid or missing config file — defaults apply, startup continues, user is informed.
- Termination signal during startup or refresh — app cleans up connections/background
  work and restores terminal.
- Docker reports partial info (e.g., version but no counts) — available fields display,
  missing fields show as unavailable rather than blank/crash.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a single terminal command that launches the status
  interface.
- **FR-002**: System MUST initialize user configuration, establish Docker connectivity,
  and render the main screen on launch without requiring extra setup steps.
- **FR-003**: System MUST detect and display Docker connection state as one of:
  connected, unavailable, permission-denied, or connection-failed.
- **FR-004**: System MUST display Engine summary when connected; mandatory fields for
  acceptance are Engine version, OS/platform, architecture, container counts (total,
  running, stopped), and image count; API version MUST be shown if reliably available
  and otherwise shown as unavailable without blocking the view.
- **FR-005**: System MUST remain usable when Docker is unreachable, showing status,
  cause category, and next-step guidance without raw tracebacks in normal mode.
- **FR-006**: System MUST isolate all Docker communication behind a service/adapter
  boundary so interface components never communicate with the Engine directly.
- **FR-007**: System MUST support manual-only refresh via the `r` key that re-queries
  Docker and updates status, loading, and error displays; no automatic/timed refresh is
  in scope for this release.
- **FR-008**: System MUST keep the interface responsive during Docker queries (no frozen
  input/rendering while waiting).
- **FR-009**: System MUST support baseline keyboard controls: `j` move down, `k` move up,
  `r` refresh, `?` help, `q` quit, `Esc` close/cancel.
- **FR-010**: System MUST provide an on-screen help view documenting available shortcuts.
- **FR-011**: System MUST provide validated application configuration with sensible
  defaults covering at minimum local Docker endpoint selection (local socket/environment
  only; remote TCP/SSH endpoints are out of scope for this release), display preferences,
  and debug/diagnostic verbosity; invalid values MUST NOT prevent startup.
- **FR-012**: System MUST terminate cleanly on `q`, on terminal termination signals, and
  on fatal initialization errors, releasing Docker connections and background work and
  restoring terminal state.
- **FR-013**: System MUST provide a diagnostic/debug mode that reveals human-readable
  error cause plus connection diagnostics (endpoint probed, remediation hints, secrets
  redacted) on demand, plus a log file with complete detail, while normal mode stays
  concise.
- **FR-014**: System MUST NOT include container/image/network/volume/Compose/registry/
  event/monitoring/cleanup/AI/plugin management in this feature.

### Key Entities *(include if feature involves data)*

- **Docker Connection Status**: Current Engine reachability — connected, unavailable,
  permission-denied, connection-failed — plus user-facing guidance for the failure case.
- **Docker System Summary**: Point-in-time Engine facts shown on the status screen —
  version, API version if available, OS, architecture, container totals
  (total/running/stopped), image count.
- **Application Configuration**: Validated user preferences — local Docker endpoint
  (socket/environment only), display options, debug verbosity — with defaults and
  per-field fallback on invalid values.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can launch the app and determine Docker availability plus Engine
  summary in under 10 seconds on a typical Linux machine with Docker running.
- **SC-002**: 100% of Docker-unavailable launches (stopped daemon, missing access, denied
  permission) remain usable and show an actionable explanation with zero crashes or raw
  tracebacks in normal mode.
- **SC-003**: 90% of first-time users can refresh status, open help, and quit using
  keyboard hints alone without external documentation.
- **SC-004**: Interface stays navigable during slow Docker responses — keypresses are
  acknowledged within 1 second and the app never requires force-kill for refresh or quit.
- **SC-005**: Configuration survives relaunch — valid user preferences persist and invalid
  values fall back to defaults without blocking startup in 100% of trials.

## Assumptions

- Users run on Linux with a terminal of at least 80x24; resizing and SSH use are
  supported per constitution TUI-first principle.
- Local Docker Engine access follows the platform-standard local socket/environment
  already available to the user; no new authentication scheme is introduced and remote
  TCP/SSH endpoints are deferred to later specifications.
- Exact Engine summary fields shown depend on what the Engine reliably reports; missing
  fields display as unavailable rather than blocking the view.
- Terminal command name defaults to `docker-tui` unless a package/command conflict found
  during planning requires a rename.
- Mouse support is optional; keyboard-only operation is the acceptance bar.
- Advanced Docker management, events streaming, and AI assistance are explicitly out of
  scope and will be separate specifications.
