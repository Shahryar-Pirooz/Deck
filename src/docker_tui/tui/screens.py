"""Status screen layout and help modal."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, LoadingIndicator, Static

from docker_tui.docker_gateway import ConnectionState, DockerSnapshot
from docker_tui.tui.widgets import FieldRow

STATE_LABELS = {
    ConnectionState.CONNECTED: "Connected",
    ConnectionState.UNAVAILABLE: "Unavailable",
    ConnectionState.PERMISSION_DENIED: "Permission denied",
    ConnectionState.CONNECTION_FAILED: "Connection failed",
}

NEXT_STEPS = {
    ConnectionState.UNAVAILABLE: (
        "Check that Docker is running and that the Docker socket exists,\nthen press r to retry."
    ),
    ConnectionState.PERMISSION_DENIED: (
        "Check that the current user has permission to access the Docker socket\n"
        "(e.g. membership in the docker group), then press r to retry."
    ),
    ConnectionState.CONNECTION_FAILED: (
        "Check that Docker is running and reachable, then press r to retry."
    ),
}

SHORTCUTS = (
    ("j / k", "Move down / up"),
    ("r", "Refresh Docker information"),
    ("?", "Show this help"),
    ("Esc", "Close / cancel"),
    ("q", "Quit"),
)


class StatusView(Static):
    """Main Docker status panel with fixed mandatory fields."""

    FIELD_IDS = (
        "connection",
        "version",
        "api",
        "os",
        "arch",
        "containers",
        "running",
        "stopped",
        "images",
        "endpoint",
    )

    LABELS = {
        "connection": "Connection",
        "version": "Docker Version",
        "api": "API Version",
        "os": "Operating System",
        "arch": "Architecture",
        "containers": "Containers",
        "running": "Running",
        "stopped": "Stopped",
        "images": "Images",
        "endpoint": "Endpoint",
    }

    def compose(self) -> ComposeResult:
        yield Static("Docker Status", classes="panel-title")
        for field_id in self.FIELD_IDS:
            yield FieldRow(field_id, self.LABELS[field_id])
        yield Static("", id="detail", classes="detail")
        yield Static("", id="hint", classes="hint")

    def show_snapshot(self, snapshot: DockerSnapshot, debug: bool = False) -> None:
        """Render a snapshot; missing fields show as unavailable."""
        values: dict[str, str | None] = {
            "connection": STATE_LABELS[snapshot.state],
            "endpoint": snapshot.endpoint,
        }
        if snapshot.summary is not None:
            summary = snapshot.summary
            values.update(
                {
                    "version": summary.version,
                    "api": summary.api_version,
                    "os": summary.os,
                    "arch": summary.architecture,
                    "containers": str(summary.containers_total),
                    "running": str(summary.containers_running),
                    "stopped": str(summary.containers_stopped),
                    "images": str(summary.images),
                }
            )
        for field_id in self.FIELD_IDS:
            try:
                row = self.query_one(f"#row-{field_id}", FieldRow)
            except Exception:  # noqa: BLE001 - unmounted in unit tests
                continue
            row.set_value(values.get(field_id))
        try:
            if snapshot.state is ConnectionState.CONNECTED:
                self.query_one("#detail", Static).update(snapshot.detail)
                self.query_one("#hint", Static).update("")
            else:
                guidance = NEXT_STEPS.get(snapshot.state, "")
                text = snapshot.detail
                if debug:
                    text += f"\nEndpoint probed: {snapshot.endpoint}"
                if guidance and guidance not in text:
                    text += f"\n{guidance}"
                self.query_one("#detail", Static).update(text)
                self.query_one("#hint", Static).update("")
        except Exception:  # noqa: BLE001 - unmounted in unit tests
            pass

    def snapshot_values(self) -> dict[str, str]:
        """Current row values keyed by field id (for tests)."""
        values: dict[str, str] = {}
        for field_id in self.FIELD_IDS:
            try:
                values[field_id] = self.query_one(f"#row-{field_id}", FieldRow).value
            except Exception:  # noqa: BLE001 - unmounted
                values[field_id] = ""
        return values


class HelpScreen(ModalScreen[None]):
    """Keyboard shortcut reference. Dismiss with Esc or q."""

    BINDINGS = [
        ("escape", "dismiss_help", "Close"),
        ("q", "dismiss_help", "Close"),
    ]

    def compose(self) -> ComposeResult:
        lines = ["Keyboard Shortcuts", ""]
        lines.extend(f"  {key:<8} {desc}" for key, desc in SHORTCUTS)
        lines.extend(("", "Press Esc or q to close."))
        yield Static("\n".join(lines), id="help-text")

    def action_dismiss_help(self) -> None:
        """Close the help modal."""
        self.dismiss(None)


class LoadingView(Static):
    """Loading indicator shown while a probe is in flight."""

    def compose(self) -> ComposeResult:
        yield LoadingIndicator()


def app_header() -> Header:
    """Application header widget."""
    return Header()


def app_footer() -> Footer:
    """Application footer widget (shows bindings)."""
    return Footer()
