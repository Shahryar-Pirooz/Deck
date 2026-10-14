"""Small reusable row widgets for the status screen and sidebar."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Input, Label, Static

from deck.docker_gateway import ContainerRunError, ResourceType

UNAVAILABLE = "unavailable"


class FieldRow(Horizontal):
    """One label/value line. Missing values render as unavailable, never blank."""

    def __init__(self, field_id: str, label: str, value: str = "…") -> None:
        super().__init__(id=f"row-{field_id}")
        self._field_id = field_id
        self._label = label
        self._value = value

    def compose(self) -> ComposeResult:
        yield Label(self._label, classes="field-label")
        yield Label(self._value, id=f"val-{self._field_id}", classes="field-value", markup=False)

    def set_value(self, value: str | None) -> None:
        """Update the value; None renders as unavailable."""
        text: str = value if value else UNAVAILABLE
        self._value = text
        try:
            self.query_one(f"#val-{self._field_id}", Label).update(text)
        except Exception:  # noqa: BLE001 - widget not yet mounted in tests
            pass

    @property
    def value(self) -> str:
        """Current value (for tests)."""
        return self._value


class SidebarView(Vertical):
    """Persistent, non-focusable Docker resource selector."""

    can_focus = False

    DEFAULT_CSS = """
    SidebarView {
        width: 16;
        min-width: 14;
        max-width: 20;
        height: 1fr;
        margin: 0 1;
        padding: 1;
        border: round $secondary;
        background: $surface;
    }

    SidebarView .entry {
        height: 2;
        padding: 0 1;
        color: $text-muted;
    }

    SidebarView .entry.--active {
        color: $text;
        text-style: bold reverse;
    }
    """

    ORDER = (
        ("1 Containers", ResourceType.CONTAINERS),
        ("2 Images", ResourceType.IMAGES),
        ("3 Volumes", ResourceType.VOLUMES),
        ("4 Networks", ResourceType.NETWORKS),
    )

    def __init__(self) -> None:
        super().__init__()
        self.entries = [SidebarEntry(label, resource_type) for label, resource_type in self.ORDER]
        self.active = ResourceType.CONTAINERS
        self._apply_highlight()

    def compose(self) -> ComposeResult:
        yield from self.entries

    def update_highlight(self, new_active: ResourceType) -> None:
        """Highlight exactly one resource without taking focus."""
        if new_active not in ResourceType:
            return
        self.active = new_active
        self._apply_highlight()

    def _apply_highlight(self) -> None:
        for entry in self.entries:
            entry.set_class(entry.type is self.active, "--active")


class SidebarEntry(Label):
    """One immutable sidebar indicator entry."""

    def __init__(self, label: str, entry_type: ResourceType) -> None:
        super().__init__(label, classes="entry")
        self.type = entry_type


class ListField(Vertical):
    """Keyboard-only list of raw string entries (ports, volumes, env vars).

    ``n`` adds via the entry input, ``d`` removes the selected entry, ``e``
    edits it, ``j``/``k`` move the selection. Entries are validated by the
    optional ``parser`` callable, which must raise ``ContainerRunError`` on
    invalid input.
    """

    can_focus = True

    BINDINGS = [
        ("n", "add_entry", "Add"),
        ("space", "add_entry", "Add"),
        ("d", "remove_entry", "Remove"),
        ("e", "edit_entry", "Edit"),
        ("j", "move_down", "Down"),
        ("k", "move_up", "Up"),
    ]

    DEFAULT_CSS = """
    ListField {
        height: auto;
        margin: 0 0 1 0;
    }
    ListField .list-field-title {
        color: $text-muted;
    }
    ListField .list-field-items {
        height: auto;
        color: $text;
    }
    """

    class Changed(Message):
        """Posted after the entry list changes."""

        def __init__(self, field: ListField) -> None:
            super().__init__()
            self.field = field

    class EntryRejected(Message):
        """Posted when a submitted entry fails validation."""

        def __init__(self, field: ListField, text: str) -> None:
            super().__init__()
            self.field = field
            self.text = text

    def __init__(
        self,
        title: str,
        placeholder: str,
        field_id: str,
        parser: Callable[[str], Any] | None = None,
    ) -> None:
        super().__init__(id=field_id)
        self._title = title
        self._placeholder = placeholder
        self._parser = parser
        self._items: list[str] = []
        self._selected = 0

    def compose(self) -> ComposeResult:
        yield Label(self._title, classes="list-field-title")
        yield Input(placeholder=self._placeholder, id=f"{self._id}-input")
        yield Static(self._items_text(), id=f"{self._id}-items", classes="list-field-items")

    def _items_text(self) -> str:
        if not self._items:
            return "(empty)"
        lines: list[str] = []
        for index, item in enumerate(self._items):
            marker = "> " if index == self._selected else "  "
            lines.append(f"{marker}{item}")
        return "\n".join(lines)

    def _refresh(self) -> None:
        try:
            self.query_one(f"#{self._id}-items", Static).update(self._items_text())
        except Exception:  # noqa: BLE001 - unmounted in unit tests
            pass

    def values(self) -> list[str]:
        """Current entries in insertion order."""
        return list(self._items)

    def action_add_entry(self) -> None:
        """Focus the entry input to type a new value (n)."""
        try:
            self.query_one(f"#{self._id}-input", Input).focus()
        except Exception:  # noqa: BLE001 - unmounted in unit tests
            pass

    def action_remove_entry(self) -> None:
        """Remove the selected entry (d)."""
        if not self._items:
            return
        self._items.pop(self._selected)
        self._selected = max(0, min(self._selected, max(len(self._items) - 1, 0)))
        self._refresh()
        self.post_message(self.Changed(self))

    def action_edit_entry(self) -> None:
        """Move the selected entry back into the input for editing (e)."""
        if not self._items:
            return
        raw = self._items.pop(self._selected)
        self._selected = max(0, min(self._selected, max(len(self._items) - 1, 0)))
        try:
            entry_input = self.query_one(f"#{self._id}-input", Input)
            entry_input.value = raw
            entry_input.focus()
        except Exception:  # noqa: BLE001 - unmounted in unit tests
            pass
        self._refresh()
        self.post_message(self.Changed(self))

    def action_move_down(self) -> None:
        """Move the selection down (j)."""
        if not self._items:
            return
        self._selected = min(len(self._items) - 1, self._selected + 1)
        self._refresh()

    def action_move_up(self) -> None:
        """Move the selection up (k)."""
        if not self._items:
            return
        self._selected = max(0, self._selected - 1)
        self._refresh()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Validate and append the submitted entry."""
        event.stop()
        raw = event.value.strip()
        if not raw:
            return
        if self._parser is not None:
            try:
                self._parser(raw)
            except ContainerRunError as exc:
                self.post_message(self.EntryRejected(self, exc.user_text()))
                return
        self._items.append(raw)
        self._selected = len(self._items) - 1
        try:
            entry_input = self.query_one(f"#{self._id}-input", Input)
            entry_input.value = ""
        except Exception:  # noqa: BLE001 - unmounted in unit tests
            pass
        self._refresh()
        self.post_message(self.Changed(self))
