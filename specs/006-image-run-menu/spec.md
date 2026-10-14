# Feature Specification: Image Run Menu

**Feature Branch**: `006-image-run-menu`

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "add a menu in images that user can pull and run new container. this menu must have all option that a container needs to run like:
1. port mapping ( must a list)
2. volumes ( must a list)
3. network
4. name
5. envs ( must a list )"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Launch a Container with Basic Options (Priority: P1)

As a user, I want to launch a new container from an image listed in the Images view, providing a name and basic configuration, so that I can run a container without leaving the TUI.

**Why this priority**: This is the primary use case — the ability to provision a container from an image is the core value of the feature. Without it, users must use an external terminal to run containers, defeating the purpose of the TUI.

**Independent Test**: Can be tested by opening the Images view, selecting an image, entering a name, confirming the launch, and verifying that a new container appears in the Containers view.

**Acceptance Scenarios**:

1. **Given** the user is viewing the Images list with at least one image, **When** the user presses Enter on a selected image, **Then** a configuration menu is displayed with fields for name, ports, volumes, network, and environment variables
2. **Given** the configuration menu is open with a name entered, **When** the user confirms launch, **Then** a new container is created and started using the selected image and provided configuration
3. **Given** the user is in the configuration menu, **When** the user presses Esc, **Then** the menu closes without creating a container

### User Story 2 - Configure Port Mappings (Priority: P2)

As a user, I want to add one or more port mappings to the container I am launching, so that I can expose container services to the host.

**Why this priority**: Port mapping is essential for most container use cases (web servers, databases, APIs) but is secondary to just launching a container with a name.

**Independent Test**: Can be tested by adding port mappings in the configuration menu, launching the container, and verifying the container is running with the specified port mappings.

**Acceptance Scenarios**:

1. **Given** the configuration menu is open, **When** the user adds a port mapping entry (e.g., "8080:80"), **Then** the entry appears in the ports list field
2. **Given** the user has added multiple port mappings, **When** the user confirms launch, **Then** the container is created with all specified port mappings
3. **Given** no port mappings are added, **When** the user confirms launch, **Then** the container is created without any port mappings (default behavior)

### User Story 3 - Configure Volumes and Environment Variables (Priority: P3)

As a user, I want to mount volumes and set environment variables for the container I am launching, so that I can persist data and configure container behavior.

**Why this priority**: Volume and environment configuration are important for production-like deployments but are not needed for basic container launches.

**Independent Test**: Can be tested by adding volume mounts and environment variables in the configuration menu, launching the container, and verifying the container is running with the specified volumes and environment variables.

**Acceptance Scenarios**:

1. **Given** the configuration menu is open, **When** the user adds volume entries (e.g., "/data:/app/data") and environment variable entries (e.g., "DEBUG=true"), **Then** each entry appears in its respective list field
2. **Given** the user has specified volumes and env vars, **When** the user confirms launch, **Then** the container is created with all specified volumes and environment variables
3. **Given** the user has added an environment variable containing sensitive data, **When** the configuration menu is displayed, **Then** the environment variable value is shown so the user can verify before committing

### User Story 4 - Select a Network (Priority: P3)

As a user, I want to attach the container I am launching to a specific Docker network, so that I can control container networking topology.

**Why this priority**: Network selection is useful for advanced deployments but is not required for basic container creation (Docker defaults to the bridge network).

**Independent Test**: Can be tested by selecting a network in the configuration menu (or leaving it blank), launching the container, and verifying the container is running on the specified or default network.

**Acceptance Scenarios**:

1. **Given** the configuration menu is open, **When** the user selects or types a network name, **Then** that network name appears in the network field
2. **Given** the user has specified a network, **When** the user confirms launch, **Then** the container is created attached to the specified network
3. **Given** no network is specified, **When** the user confirms launch, **Then** the container is created on the default Docker network

---

### Edge Cases

- What happens when the user provides a name that is already in use by another container?
- How does the system handle invalid port mapping syntax (e.g., "abc:80")?
- What happens when the selected image cannot be found or is not available locally?
- How does the system handle an empty or whitespace-only container name?
- What happens if the Docker daemon is unavailable while the user is configuring the container?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: The Images view MUST provide a way to launch a new container from a selected image via a dedicated "Run" or "Create" action
- **FR-002**: The configuration menu MUST accept a container name as a text input
- **FR-003**: The configuration menu MUST accept one or more port mappings as a list input, where each entry follows the host:container port format
- **FR-004**: The configuration menu MUST accept one or more volume mounts as a list input, where each entry follows the source:destination path format
- **FR-005**: The configuration menu MUST accept a single network name as a text input
- **FR-006**: The configuration menu MUST accept one or more environment variables as a list input, where each entry follows the KEY=value format
- **FR-007**: The configuration menu MUST display a "start" or "confirm" action that opens a confirmation review screen summarizing the name, ports, volumes, network, and env vars before creating and starting the container
- **FR-008**: The configuration menu MUST display a "cancel" action that closes the menu without creating a container
- **FR-009**: After a container is successfully created, the user MUST be returned to the Containers view (or the view is refreshed) to see the new container
- **FR-010**: The user MUST be able to add, remove, or edit items in each list field (ports, volumes, envs) before confirming
- **FR-011**: The configuration menu MUST validate that a container name is provided before allowing the start action to be enabled

### Key Entities *(include if feature involves data)*

- **Container Configuration**: A set of options for creating a container, including name (text), ports (list of port mappings), volumes (list of bind mounts), network (text), and environment variables (list of key-value pairs)
- **Image**: A Docker image selected from the Images list, which serves as the base for the new container
- **Port Mapping**: A pair of host and container ports that define how network traffic is routed to the container
- **Volume Mount**: A mapping between a host path and a container path for persistent data storage
- **Environment Variable**: A key-value pair that configures runtime behavior inside the container

## Clarifications

- **Confirmation Step**: The feature must include a confirmation review screen before creating a container. The user must explicitly confirm the container name, port mappings, volume mounts, network, and environment variables before the container is created and started. Upon confirmation, the system MUST create and start the container in a detached mode, making it running immediately. A notification MUST be displayed on successful launch.
- **Image Pull Handling**: When the selected image is not available locally, the system MUST attempt to pull the image from the configured registry in a background mode. The pull should not block the TUI event loop. When complete, a notification MUST be displayed to the user showing success or failure.
- **Name Collision Handling**: If the user provides a container name that already exists, the system MUST reject the name with a clear error message and suggest a unique alternative (e.g., appending a numeric suffix like "myapp-2").
- **Images View Scope**: The Images view MUST only display images that are already pulled locally. Images unavailable locally MUST NOT be requested from registries while rendering the view, preserving TUI responsiveness.
- **Container Start Behavior**: Upon successful creation, the container MUST start automatically in detached mode (equivalent to Docker's default `docker run` behavior). The user MUST see the new container appear in the Containers view once it transitions to the running state.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: Users can launch a new container from the Images view in under 30 seconds (excluding any image pull time)
- **SC-002**: 95% of users can successfully launch a container with a custom name on their first attempt
- **SC-003**: Users can add at least 5 port mappings, 5 volume mounts, and 10 environment variables to a single container launch
- **SC-004**: All configuration fields are navigable using keyboard-only input
- **SC-005**: 100% of the core functionality (name, ports, volumes, network, envs, start, cancel) is covered by automated tests

## Assumptions

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right assumptions based on reasonable defaults
  chosen when the feature description did not specify certain details.
-->

- Users have a working Docker daemon accessible from the TUI
- Users have the necessary permissions to create and start containers
- Image names in the Images view represent locally available images that can be used to start containers
- Port mapping entries follow the Docker convention of host_port:container_port
- Volume mount entries follow the Docker convention of host_path:container_path
- Environment variable entries follow the KEY=value convention
- The container starts automatically after creation (equivalent to running with default detach mode)
- Keyboard-first interaction is the primary mode (per the project constitution), with navigation using standard Vim-style keys
