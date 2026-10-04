# Contract: Keyboard and View Behavior

**Feature**: `005-sidebar-resource-menu`

## Baseline (unchanged)

| Key | Action |
|-----|--------|
| `j` / `k` | Move highlight down / up within the active list |
| `Enter` | Open selected row (details; actions only in the containers view) |
| `r` | Refresh (re-query Engine for the active view) |
| `?` | Help |
| `Esc` | Close / cancel |
| `q` | Quit (closes help/details first) |

## New

| Key | Action | Context |
|-----|--------|---------|
| `1` | Switch to Containers | Main screen only; suppressed in modals/inputs |
| `2` | Switch to Images | Main screen only; suppressed in modals/inputs |
| `3` | Switch to Volumes | Main screen only; suppressed in modals/inputs |
| `4` | Switch to Networks | Main screen only; suppressed in modals/inputs |

## View semantics

- Sidebar order is fixed: `1 Containers`, `2 Images`, `3 Volumes`, `4 Networks`;
  exactly one entry is highlighted and always matches the main panel title.
- Focus stays in the main list at all times; the sidebar is a non-focusable
  indicator and never captures `j`/`k`/`Enter`.
- Each view keeps its own highlight index; returning restores it (clamped to the
  new row count).
- New views show `loading` during fetch, a named `empty` message for zero rows,
  and an `unavailable` message with retry guidance on failure.
- All bindings appear in the help view and are covered by TUI keybinding tests.
