"""Small reusable row widgets for the status screen and sidebar."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label

from deck.docker_gateway import ResourceType


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
        yield Label(self._value, id=f"val-{self._field_id}", classes="field-value")

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
