# Feature Specification: Docker Container Management

**Feature Branch**: `004-docker-container-management`

**Created**: 2026-09-29

**Status**: Draft

**Input**: User description: "this app need run as a docker container and manage other docker containers"

## Clarifications

### Session 2026-09-29

- Q: How should the manager container reach the Docker Engine it manages? → A: Share the host Engine access into the app container (sibling containers visible).
- Q: What safety posture must the documented run configuration enforce for the shared Engine access? → A: Warn of full host control and require confirmation for destructive actions.
- Q: Which container states must the sibling list display beyond running and stopped? → A: Running, stopped, and other, with exact status in details.
- Q: Must stopping or removing the manager's own container be blocked entirely or allowed with an override? → A: Blocked entirely with an explanatory message.
- Q: What is the target number of sibling containers the list must handle smoothly? → A: 100 containers.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run the Manager as a Container and See Other Containers (Priority: P1)

A host operator starts the terminal manager itself as a container with access to the host
Engine shared in, then immediately sees Engine connection status plus the list of other
containers on that Engine.

**Why this priority**: This is the core of the request — without a shippable container
form plus a working Engine connection from inside the container, no container
management is possible.

**Independent Test**: Can be fully tested by following the documented run steps on a host
with the Engine running, launching the manager container with an interactive terminal,
and observing connection status and the sibling container list. Delivers a working
containerized status view with no lifecycle actions.

**Acceptance Scenarios**:

1. **Given** the Engine is running and accessible to the app container, **When** the
   operator starts the manager container per the documented run steps, **Then** the main
   screen shows connected status with Engine summary and a list of sibling containers
   including name, image reference, and running/stopped/other state.
2. **Given** Engine access was not shared into the app container, **When** the manager
   starts, **Then** it stays usable, shows unavailable status with guidance explaining
   that Engine access must be shared in, and shows no raw tracebacks in normal mode.

---

### User Story 2 - Start, Stop, and Restart Sibling Containers Safely (Priority: P2)

An operator selects a sibling container with the keyboard and starts, stops, or
restarts it, with explicit confirmation required before anything destructive.

**Why this priority**: Lifecycle control is the primary management value; safety guards
make it trustworthy, especially when the manager itself is one of the containers.

**Independent Test**: Can be fully tested by starting a stopped test container, then
stopping it again, and observing state updates after each action. Delivers verified
lifecycle control.

**Acceptance Scenarios**:

1. **Given** a stopped sibling container is selected, **When** the user invokes start,
   **Then** the container starts and the list updates to show the running state.
2. **Given** a running sibling container is selected, **When** the user invokes stop,
   **Then** the container stops gracefully and the list updates to show the stopped
   state.
3. **Given** any container selected for removal, **When** the user invokes remove,
   **Then** the system asks for explicit confirmation first and only removes on
   confirmation.

---

### User Story 3 - Inspect a Container and Read Its Logs (Priority: P3)

An operator selects a container to view its basic details and recent log output when
diagnosing why something is unhealthy or stopped.

**Why this priority**: Read-only inspection is the safe diagnostic path and unblocks
troubleshooting without requiring any state change.

**Independent Test**: Can be fully tested by opening the details/logs view for a running
container and reading its output. Delivers a validated diagnostic loop.

**Acceptance Scenarios**:

1. **Given** a container is selected, **When** the user opens details, **Then** basic
   facts (name, image reference, state, and status) are shown.
2. **Given** a container with log output is selected, **When** the user opens logs,
   **Then** recent log content is shown with a loading indication while it is fetched.

---

### Edge Cases

- Engine access not shared into the app container — status shows unavailable with
  guidance on the documented run configuration instead of crashing.
- Engine permission denied from inside the container — reported distinctly from generic
  connection failure with next-step guidance.
- The manager's own container appears in the list — it is clearly identified, and
  stopping or removing it is blocked with an explanatory message.
- Engine stops mid-session — next refresh shows unavailable state without freeze.
- Terminal is not interactive (no display attached) — manager reports that an
  interactive terminal is required instead of rendering incorrectly.
- Up to 100 sibling containers — the list stays navigable without loading everything
  into a blocking view.
- Slow Engine response from inside the container — interface shows loading state and
  stays navigable; the user can cancel or quit.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a shippable container image definition that packages
  the terminal manager so it can be deployed as a container.
- **FR-002**: System MUST document a supported run configuration that shares host Engine
  access into the app container (single shared Engine scope; a private Engine inside
  the container is out of scope), MUST warn that shared Engine access grants full
  control of the host, and attaches an interactive terminal.
- **FR-003**: System MUST detect and display Engine connection state from inside the
  container as one of: connected, unavailable, permission-denied, or
  connection-failed, with next-step guidance and no raw tracebacks in normal mode.
- **FR-004**: Users MUST be able to list sibling containers showing at minimum name,
  image reference, and state grouped as running, stopped, or other, with the exact
  status available in details.
- **FR-005**: Users MUST be able to start, stop, and restart a selected sibling
  container via keyboard.
- **FR-006**: System MUST require explicit confirmation before removing a container
  and MUST only remove on confirmation.
- **FR-007**: System MUST clearly identify its own container in the list and MUST block
  stopping or removing itself, showing an explanatory message instead.
- **FR-008**: Users MUST be able to view basic details and recent logs for a selected
  container.
- **FR-009**: System MUST keep the interface responsive during container operations,
  showing loading state for slow operations without frozen input.
- **FR-010**: System MUST reuse the existing configuration approach (endpoint, display,
  debug verbosity) inside the container with safe defaults; invalid values MUST NOT
  prevent startup.
- **FR-011**: System MUST isolate all Engine communication behind the existing
  service/adapter boundary so interface components never communicate with the Engine
  directly.
- **FR-012**: System MUST NOT include multi-host orchestration, registry management,
  or image building in this feature.

### Key Entities

- **Containerized App Package**: The shippable image plus its documented run
  configuration (Engine access sharing, interactive terminal, configuration).
- **Managed Container**: A sibling container on the same Engine with identity (name),
  image reference, state (running, stopped, or other with exact status in details),
  and recent logs.
- **Engine Connection from Container**: Reachability of the host Engine from inside the
  app container, including failure category and user-facing guidance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operators can start the manager as a container and determine Engine
  availability plus the sibling container list in under 2 minutes following the
  documented run steps.
- **SC-002**: 100% of lifecycle trials (start, stop, restart) on a test container
  complete with a visible state update and zero crashes.
- **SC-003**: 100% of remove attempts show a confirmation step first; zero unconfirmed
  removals occur in testing.
- **SC-004**: Users can open logs for a running container in under 10 seconds.
- **SC-005**: 90% of first-time users can run the containerized manager, refresh the
  list, manage one container, and quit using on-screen hints alone.

## Assumptions

- Host runs a local Engine and the operator is permitted to share Engine access into
  the app container through the platform-standard local mechanism; remote Engines are
  deferred.
- Operator attaches an interactive terminal when running the app container.
- Single-host scope; multi-host orchestration is out of scope for this release.
- Foundation behavior is reused: status display, manual refresh, Vim keyboard
  controls, help view, error handling without tracebacks, clean shutdown, and
  validated configuration with safe defaults.
- Self-container identification is best-effort (for example via container identity
  visible from inside); when it cannot be determined, destructive guards apply broadly
  with warnings.
- Image distribution uses versioned releases through a container registry.
