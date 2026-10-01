"""Small reusable row widgets for the status screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Label

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
