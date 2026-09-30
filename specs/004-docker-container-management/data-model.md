# Data Model: Docker Container Management

**Feature**: `004-docker-container-management` | **Date**: 2026-09-29

Derived from spec Key Entities plus clarification outcomes. All state is a
point-in-time view re-queried from the Engine (Constitution I); nothing here is
persisted by the app.

## ManagedContainer

A sibling container on the shared host Engine.

| Field | Type | Rules |
|-------|------|-------|
| `name` | non-empty string | Primary display identity; unique per Engine |
| `container_id` | non-empty string | Opaque Engine identity; used for actions, never shown as the primary label |
| `image_ref` | non-empty string | Image name/tag or digest as reported |
| `state_bucket` | `running` \| `stopped` \| `other` | Derived from exact status via the bucket mapping below |
| `exact_status` | string | Verbatim Engine status; always available in details |
| `is_self` | boolean | True when identified as the manager's own container (best-effort) |

**Bucket mapping**: `running` ← running, restarting; `stopped` ← exited, created,
dead, removing; `other` ← paused and anything unrecognized.

**State transitions**:
- `running` → `stopped` via stop (graceful)
- `stopped` → `running` via start
- `running` ⇄ `running` via restart
- any → `removed` via remove (terminal; requires explicit confirmation; `is_self`
  transitions are blocked with an explanatory message instead)

## ContainerizedAppPackage

The shippable image plus its supported run configuration.

| Field | Type | Rules |
|-------|------|-------|
| `image` | name + versioned tag | Versioned releases; `latest` never the only tag |
| `engine_access` | shared host Engine | Single shared scope; private in-container Engines out of scope |
| `terminal` | interactive terminal attached | Required; absent terminal reported, not rendered into |
| `config_override` | optional config path | Same validated TOML semantics as host runs |

## EngineConnectionFromContainer

Reachability of the host Engine from inside the app container.

| Field | Type | Rules |
|-------|------|-------|
| `state` | `connected` \| `unavailable` \| `permission-denied` \| `connection-failed` | Exactly one; same four states as the foundation |
| `guidance` | user-facing text | Actionable next step; includes the full-host-control warning context for run misconfiguration |
| `endpoint_label` | string | Human-readable endpoint; never a secret |

## ContainerLogView

On-demand diagnostic view for one container.

| Field | Type | Rules |
|-------|------|-------|
| `container_id` | string | References `ManagedContainer.container_id` |
| `lines` | bounded text | Bounded tail (never unbounded load); loading state while fetching |
| `fetched_at` | timestamp | Point-in-time marker; refresh re-queries |

## Relationships

- One `EngineConnectionFromContainer` scopes many `ManagedContainer` rows.
- One `ManagedContainer` has zero-or-one open `ContainerLogView`.
- `ContainerizedAppPackage` is the deployment form of the app itself and may appear
  as a `ManagedContainer` row with `is_self = true`.
