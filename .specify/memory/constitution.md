<!-- Sync Impact Report
Version change: unversioned template → 1.0.0 (initial adoption)
Modified principles: [none — initial adoption from template placeholders]
Added sections:
- Core Principles: I. Docker Is the Source of Truth, II. AI Is an Interface Not Infrastructure,
  III. Safety Over Convenience (NON-NEGOTIABLE), IV. Keyboard First (NON-NEGOTIABLE),
  V. TUI First, VI. Simple Operations Must Stay Simple
- Architecture, Engineering & Product Standards (covers: layered architecture, Docker adapter,
  command system, events, Python standards, TUI standards, Vim interaction, Docker features,
  AI tools, security, error handling, testing, performance, configuration, observability,
  dependencies, documentation)
- Development Workflow, Quality Gates & Vision (covers: git practices, spec-driven development,
  definition of done, MVP constraint, long-term vision)
- Governance (amendment procedure, versioning policy, compliance review)
Removed sections: [none — template placeholders replaced]
Follow-up TODOs: [none]
-->

# Docker TUI Manager Constitution

## Core Principles

### I. Docker Is the Source of Truth

Docker Engine MUST be the authoritative source for Docker state.

The application MUST NOT maintain a competing persistent representation of Docker
resources unless explicitly required for application functionality.

The application MUST query Docker rather than reconstructing Docker state from local
assumptions.

Rationale: Prevents drift, stale actions, and unsafe decisions in large environments.

### II. AI Is an Interface, Not the Infrastructure

AI MUST interact with Docker only through the application's service and tool layers.

AI MUST NEVER directly execute arbitrary shell commands or manipulate the Docker socket
without going through defined application tools.

Required layering:

TUI / AI → Application Commands → Application Services → Docker Adapter → Docker Engine

Rationale: Makes AI behavior auditable, testable, permission-checked, and replaceable.

### III. Safety Over Convenience (NON-NEGOTIABLE)

Docker operations can be destructive. Destructive operations MUST have explicit safety
semantics and MUST support confirmation before execution.

AI-initiated destructive operations MUST require explicit user approval unless the user
has intentionally configured an appropriate automation policy.

The application MUST NEVER silently execute arbitrary commands suggested by an AI model.

Rationale: Safety failures destroy data. Convenience MUST NOT bypass approval.

### IV. Keyboard First (NON-NEGOTIABLE)

The application MUST be fully operable keyboard-only. Every important operation MUST be
accessible without a mouse.

Vim-style navigation is REQUIRED, not optional. Baseline MUST include:

- `j`/`k`: move, `h`/`l`: horizontal navigation where applicable
- `gg`: first item, `G`: last item
- `Ctrl+d` / `Ctrl+u`: page down / up
- `Enter`: open/select, `Space`: toggle selection
- `/`: search, `:`: command mode, `?`: help, `Esc`: cancel/back, `q`: quit/back, `r`: refresh

The application MUST avoid excessive arbitrary shortcuts when a conventional Vim binding
exists. Keybindings SHOULD be configurable.

### V. TUI First

The primary interface MUST be a terminal UI that remains usable over SSH and without a
graphical desktop.

The application MUST NOT depend on graphical UI capabilities for core functionality.

UI state MUST be separated from Docker infrastructure state.

### VI. Simple Operations Must Stay Simple

Common operations MUST require minimal interaction: start/stop/restart container,
view logs, exec, pull image, inspect resource.

The UI MUST expose advanced functionality without complicating basic Docker management.

## Architecture, Engineering & Product Standards

### Layered Architecture

The application MUST maintain clear separation between presentation, application, domain,
and infrastructure.

Rules:

- TUI MUST NOT directly call the Docker SDK.
- AI tools MUST NOT directly manipulate TUI state.
- Docker-specific details MUST remain isolated behind an adapter/service boundary.
- Dependencies MUST point inward: TUI → Application, AI → Application,
  Application → Domain, Infrastructure → Domain/Application abstractions.
- Domain/application layers MUST NOT depend on terminal rendering libraries.

### Docker Adapter

All Docker Engine communication MUST be isolated behind a dedicated abstraction.
The implementation MAY use the official Docker Python SDK or another maintained Docker
API client. Docker API details MUST NOT leak throughout the application.

### Command System

Operations SHOULD be represented through a reusable command system usable by TUI
keybindings, command palette, AI tools, future CLI, and automated workflows.
This prevents duplicate Docker logic across interfaces.

### Event-Driven Updates

Where practical, Docker events SHOULD be used to update state rather than aggressive
polling. Long-running streams MUST NOT block the TUI event loop.

### Python Engineering Standards

Target a currently supported Python version and pin the minimum supported version
explicitly. Public interfaces MUST have type hints. Strict or appropriately configured
static type checking, automated linting, and automated formatting are REQUIRED.

Additional rules:

- Small, cohesive modules; explicit error handling; no unnecessary global state.
- No hidden side effects; no unnecessary dependencies.
- Prefer standard library when an external dependency provides no meaningful value.
- Use async only where it provides clear benefit: event streams, log streaming,
  background operations, AI requests, long-running Docker operations.

### TUI Engineering Standards

The TUI MUST start quickly, remain responsive during Docker operations, and MUST NOT
block rendering on Docker API calls, pulls, builds, log streams, or AI requests.

The TUI MUST provide clear loading, error, and empty states; support terminal resizing;
work over SSH; provide discoverable shortcuts, a command palette, and contextual help.

### Vim Interaction Principles

Vim conventions MUST be preferred when intuitive. The baseline in Core Principle IV is
REQUIRED and MUST be tested.

### Docker Feature Scope

Docker functionality MUST be implemented incrementally. Core categories: containers,
images, networks, volumes, compose projects, system information, events.

The application MUST expose both resource-oriented operations (e.g., restart container)
and higher-level workflows (e.g., diagnose why a container keeps restarting).
Workflows MAY combine multiple Docker operations.

### AI Principles

AI is a first-class interface and MUST use structured tools with explicit name, typed
arguments, validation, permission classification, structured result, and structured error.

AI MUST distinguish observed facts, inferences, recommendations, and actions.
AI responses MUST NOT claim an action was performed unless the corresponding tool
actually succeeded.

Permission classes REQUIRED:

- SAFE: list/inspect containers, view logs, inspect image.
- CAUTION: restart/stop container, pull image.
- DESTRUCTIVE: remove container/image/volume, prune resources.

The user MUST be able to understand what an AI action will do before a destructive
operation occurs.

### Security Principles

Docker access MUST be treated as privileged system access.

The application MUST detect permission problems, avoid exposing secrets unnecessarily,
avoid logging credentials, redact sensitive env vars where appropriate, clearly
communicate privileged operations, protect destructive operations, validate AI tool
arguments, and provide an audit trail for important operations where practical.

### Error Handling

Errors MUST be actionable and MUST state what happened, which operation failed, why it
likely failed when known, and what the user can do next.

Example: prefer "Cannot remove container 'postgres-db' because it is still running.
Stop the container first." over "APIError: 409 Conflict".

Raw stack traces MUST NOT be shown to normal users unless explicitly requested, but raw
technical details MUST remain available for debugging.

### Testing Requirements

Important behavior MUST be testable without a live Docker daemon whenever practical.

- Unit: domain logic, command parsing, config, validation, permission rules, AI tool
  schemas, state transformations.
- Integration (real Engine): container lifecycle, image, network, volume, compose,
  events.
- TUI: navigation, keybindings, command execution, selection, search, modals,
  error states.
- AI: tool selection/arguments, invalid calls, destructive confirmation, context
  handling, failure handling, hallucinated-action prevention.

No feature is complete without appropriate tests.

### Performance Requirements

Normal navigation MUST feel instantaneous. TUI rendering MUST NOT be blocked by Docker,
network, pull/build, log, or AI work.

Large environments MUST remain usable via lazy loading, pagination, streaming, or
virtualization where appropriate. Unnecessarily large datasets MUST NOT be loaded into
memory. Optimizations SHOULD be evidence-driven.

### Configuration Principles

Configuration MUST be human-readable, explicit, validated, versionable, and
backward-compatible where practical.

It SHOULD support Docker endpoint, TUI preferences, theme, keybindings, refresh
intervals, AI config, and confirmation policies. Env vars MAY override config.
Secrets MUST NOT be stored in plain-text config unless explicitly required and
clearly documented.

### Observability

The application MUST provide structured logs, Docker operation errors, AI tool errors,
debug mode, version info, and Docker Engine info.

Normal operation SHOULD remain quiet. Debug logging MUST be detailed enough to diagnose
problems without exposing secrets.

### Dependency Principles

Every dependency MUST have clear justification. Prefer mature, actively maintained
libraries. Avoid dependencies for convenience when stdlib suffices. The graph MUST
remain small. Candidate majors: Docker SDK, TUI framework, config/validation library,
AI SDK — selected during implementation, not assumed here.

### Documentation

Every major feature MUST document purpose, user behavior, config, shortcuts, failure
modes, and security implications.

The project MUST maintain README, installation guide, user guide, keyboard reference,
configuration reference, AI docs, architecture docs, development guide, and contribution
guide. Docs MUST describe implemented behavior, not intended future behavior.

## Development Workflow, Quality Gates & Vision

### Git and Development Practices

Use small, focused commits with clear messages. Avoid mixing unrelated changes.

Features MUST follow: Specification → Plan → Tasks → Implementation → Tests → Review
→ Documentation. Significant features MUST NOT be implemented without a corresponding
specification or task.

### Spec-Driven Development

GitHub Spec Kit is the authoritative planning workflow. Each significant feature MUST
have user, functional, and non-functional requirements, constraints, acceptance
criteria, edge cases, security considerations, and testing requirements.
Specs MUST be implementation-independent where possible; details belong in the plan
unless architectural constraints.

### Definition of Done

A feature is complete only when requirements are implemented, edge cases considered,
errors handled, security addressed, tests exist and pass, type checking and linting
pass, docs updated, TUI behavior usable, AI integration uses defined tools where
applicable, and no known regression is introduced.

### MVP Constraint

Do NOT implement the complete Docker API before validating core UX. MVP MUST prioritize:
containers, images, networks, volumes, system info, logs, exec, Vim navigation, search,
command palette, basic AI inspection/explanation. Advanced functionality MUST be added
incrementally after core architecture validation.

### Long-Term Vision

Evolve toward a general-purpose, AI-assisted Docker control plane for Linux, leaving
room for Compose, registries, contexts, BuildKit, Swarm, rootless, GPU, Kubernetes,
Podman, plugins, automated diagnostics, and AI remediation — without adding
unnecessary MVP complexity.

Optimize for reliability, safety, speed, discoverability, keyboard efficiency,
extensibility, and AI tool reliability over feature count.

## Governance

This constitution supersedes all other development practices for this project.

Amendments REQUIRE documentation of the change, rationale, version bump per semantic
versioning (MAJOR: incompatible governance/principle removals or redefinitions; MINOR:
new principle/section or materially expanded guidance; PATCH: clarifications/wording),
and a migration plan if behavior or contracts change.

Compliance review: all specs, plans, tasks, PRs, and reviews MUST verify compliance
with this constitution. Complexity MUST be justified. Violations MUST be explicitly
flagged with rationale or rejected.

Runtime development guidance lives in project docs; where conflict exists, this
constitution governs.

**Version**: 1.0.0 | **Ratified**: 2026-09-29 | **Last Amended**: 2026-09-29
