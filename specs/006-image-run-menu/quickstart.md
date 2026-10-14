# Quickstart: Image Run Menu Validation

## Prerequisites

- `deck` CLI installed (or `pip install -e .` from repo root)
- Docker daemon running and accessible
- Python 3.11+ installed

## Setup

1. Ensure the TUI can connect to Docker:
   ```bash
   deck info
   ```
   Should show Docker version and container counts.

2. Load some images locally (optional, or pull one):
   ```bash
   docker pull nginx
   ```

## Validation Scenarios

### Scenario 1: Launch Container with Name Only (P1)

1. Open Images view (`deck images`)
2. Select an image (e.g., `nginx`)
3. Enter container name: `my-web`
4. Leave ports, volumes, network, env vars blank
5. Press Enter/Confirm
6. Observe:
   - Confirmation review screen appears summarizing inputs
   - Container is created and started
   - Notification: "Container my-web started successfully"
   - Container appears in Containers view

### Scenario 2: Launch Container with Port Mapping (P2)

1. Open Images view
2. Select an image (e.g., `nginx`)
3. Enter container name: `my-web-http`
4. Add port mapping: `8080:80`
5. Confirm
6. Observe:
   - Notification shows port mapping included
   - Container accessible on host `127.0.0.1:8080`

### Scenario 3: Launch Container with Volume (P3)

1. Open Images view
2. Select an image
3. Enter name: `my-data`
4. Add volume: `/home/user/data:/app/data`
5. Confirm
6. Observe:
   - Container started with volume mount
   - Data persists across container restarts

### Scenario 4: Launch Container with Environment Variable

1. Open Images view
2. Select an image
3. Enter name: `my-app`
4. Add env var: `DEBUG=true`
5. Confirm
6. Observe:
   - Container starts with `DEBUG=true` environment

### Scenario 5: Name Collision Handling

1. Run a test container: `docker run -d --name nginx-test nginx`
2. Open Images view
3. Try to create container with name `nginx-test`
4. Observe:
   - Error: "Container name 'nginx-test' already exists"
   - Suggestion: `nginx-test-1`
   - Form remains open for correction

### Scenario 6: Invalid Port Mapping Syntax

1. Select an image
2. Enter name: `test`
3. Add port mapping: `abc:80` (invalid)
4. Confirm
5. Observe:
   - Error: "Invalid port mapping format: 'abc:80'. Use host_port:container_port"
   - Form stays open for correction

### Scenario 7: Image Not Locally Available (Background Pull)

1. Select an image not locally available (e.g., `busybox:latest` if not pulled)
2. Enter name: `my-pulled`
3. Confirm
4. Observe:
   - Image pull starts in background
   - TUI remains responsive (not blocked)
   - Notification on completion: "Image busybox:latest pulled successfully"
   - Container created and started with the pulled image
   - OR: Notification on failure: "Failed to pull image busybox:latest. Check network."

## Run Validation Commands

```bash
# Start the TUI
deck

# In the TUI:
# 1. Go to Images view
# 2. Select an image
# 3. Fill the run configuration
# 4. Confirm
# 5. Verify the container appears in Containers view
```

## Expected Outcomes (Success Criteria)

| SC | Outcome |
|---|---|
| SC-001 | Container launched in under 30 seconds (image pull excluded) |
| SC-002 | Custom name accepted on first attempt with unique name |
| SC-003 | At least 5 port mappings, 5 volume mounts, 10 env vars supported |
| SC-004 | All fields navigable via keyboard-only (j/k/Enter/Space/Escape) |
| SC-005 | Automated test coverage exists (see tasks.md) |