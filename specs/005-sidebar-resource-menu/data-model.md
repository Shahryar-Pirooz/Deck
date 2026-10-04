# Data Model: Sidebar Resource Menu

**Feature**: `005-sidebar-resource-menu` | **Date**: 2026-10-02

Derived from spec Key Entities plus clarification outcomes. All resource rows are
point-in-time views re-queried from the Engine (Constitution I); nothing here is
persisted by the app. Highlight positions are in-memory UI state only.

## SidebarMenu

Persistent left-side indicator; never focusable, never captures `j`/`k`/`Enter`.

| Field | Type | Rules |
|-------|------|-------|
| `entries` | fixed ordered list of 4 | Exactly `1 Containers`, `2 Images`, `3 Volumes`, `4 Networks` in that order |
| `active` | `containers` \| `images` \| `volumes` \| `networks` | Exactly one; always matches the visible resource view |

## ResourceType

Selection value shared by the menu, main panel, and keybindings.

| Field | Type | Rules |
|-------|------|-------|
| `current` | `containers` \| `images` \| `volumes` \| `networks` | Defaults to `containers`; changes only via `1`-`4` from the main screen |
| `positions` | map of ResourceType → highlight index | One non-negative index per view; clamped to `len(rows) - 1` on new data; restored on return |

**State transitions**: `containers` ⇄ `images` ⇄ `volumes` ⇄ `networks` via `1`-`4`
(main screen only); modal/input focus suppresses transitions; rapid presses
resolve to the last requested type.

## ManagedImage (new)

One image row from the Engine.

| Field | Type | Rules |
|-------|------|-------|
| `image_id` | non-empty string | Opaque Engine identity; used for details, never the primary label |
| `repository_tag` | non-empty string | First repo tag, else short id digest; primary display identity |
| `size_bytes` | non-negative int | As reported; display formatting is a TUI concern |
| `created` | string | Human-readable creation marker as reported; never empty in display (`unknown` fallback) |

## ManagedVolume (new)

One volume row from the Engine.

| Field | Type | Rules |
|-------|------|-------|
| `name` | non-empty string | Primary display identity; unique per Engine |
| `driver` | string | Driver name as reported (`unknown` fallback) |
| `mountpoint` | string | Mount path as reported (`unknown` fallback) |

## ManagedNetwork (new)

One network row from the Engine.

| Field | Type | Rules |
|-------|------|-------|
| `network_id` | non-empty string | Opaque Engine identity; used for details |
| `name` | non-empty string | Primary display identity |
| `driver` | string | Driver name as reported (`unknown` fallback) |
| `scope` | string | Scope as reported (`unknown` fallback) |

## ResourceView (per type)

Main content panel for the active type.

| Field | Type | Rules |
|-------|------|-------|
| `type` | ResourceType | Matches `SidebarMenu.active` at all times |
| `title` | string | Names the active type; never shows another type's items |
| `rows` | per-type row list | Re-queried per switch/refresh; unparsable rows skipped |
| `state` | `ready` \| `loading` \| `empty` \| `unavailable` | `loading` during fetch; `empty` shows a named empty message; `unavailable` shows retry guidance |
| `highlight` | non-negative int | `j`/`k` position within this view's rows; `Enter` opens a read-only details panel |

## Relationships

- One `SidebarMenu` reflects one `ResourceType.current`.
- One `ResourceType` scopes four `ResourceView` states (one per type), each with
  its own rows and highlight.
- `ManagedContainer` (existing, unchanged) backs the containers `ResourceView`;
  `ManagedImage` / `ManagedVolume` / `ManagedNetwork` back the other three.
- Details panels reference their row identity read-only; no lifecycle transitions
  exist for the three new types in this feature.
