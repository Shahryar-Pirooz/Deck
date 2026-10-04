# Contract: Gateway Resource Reads

**Feature**: `005-sidebar-resource-menu`

Extension of the `DockerGateway` protocol boundary (implemented only in
`docker_sdk.py`; TUI/services never touch Engine details directly).
Container operations from prior features are unchanged.

## Operations

| Operation | Input | Output | Rules |
|-----------|-------|--------|-------|
| `list_images` | view switch / refresh trigger | `ManagedImage[]` (bounded, one query per switch) | Repository tag + id + size + created; skip unparsable rows |
| `list_volumes` | view switch / refresh trigger | `ManagedVolume[]` (bounded, one query per switch) | Name + driver + mountpoint; skip unparsable rows |
| `list_networks` | view switch / refresh trigger | `ManagedNetwork[]` (bounded, one query per switch) | Name + driver + scope; skip unparsable rows |
| `resource_details` | row identity | read-only details record | Same columns as the list plus Engine-reported extras; no actions |

## Error mapping

All failures reuse the four connection states with actionable messages
(what / which operation / likely why / next step); a failed list degrades to an
empty view with retry guidance while the menu stays switchable; no raw
tracebacks in normal mode; full detail preserved for debug mode and logs.

## Invariants

- Every switch/refresh re-queries the Engine; no persistent app-side resource state.
- New reads are strictly read-only; no confirmation or self-action machinery applies.
- `docker` package imports remain isolated to `docker_sdk.py`.
