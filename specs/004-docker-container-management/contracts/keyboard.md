# Contract: Keyboard Behavior for Container Management

**Feature**: `004-docker-container-management`

## Baseline (unchanged, foundation)

| Key | Action |
|-----|--------|
| `j` / `k` | Move down / up |
| `r` | Refresh (re-query Engine) |
| `?` | Help |
| `Esc` | Close / cancel |
| `q` | Quit (closes help first) |

## New

| Key | Action | Context |
|-----|--------|---------|
| `Enter` | Open selected container (details + actions) | Container list |
| `Space` | Toggle selection where multi-select applies | Container list |
| documented action keys | Start / stop / restart / logs / remove | Details view; remove always confirms first |

## Semantics

- Every management action is reachable keyboard-only; no mouse dependency.
- `Esc` cancels an in-flight confirmation; `q` never confirms a destructive action.
- All bindings appear in the help view; new keys follow Vim conventions and are
  covered by TUI keybinding tests.
