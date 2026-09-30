"""Textual application: render-first startup, worker-thread probes, Vim bindings."""

from __future__ import annotations

import logging

from textual.app import App, ComposeResult
from textual.widgets import Static

from docker_tui import services
from docker_tui.config import ApplicationConfiguration
from docker_tui.docker_gateway import (
    ConnectionState,
    DockerGateway,
    DockerSnapshot,
    ManagedContainer,
)
from docker_tui.tui.screens import (
    ContainerDetailsScreen,
    ContainerListView,
    HelpScreen,
    StatusView,
    app_footer,
    app_header,
)
from docker_tui.tui.widgets import FieldRow

log = logging.getLogger(__name__)


class DockerTUIApp(App[None]):
    """Single-screen Docker status TUI with manual-only refresh."""

    BINDINGS = [
        ("j", "move_down", "Down"),
        ("k", "move_up", "Up"),
        ("enter", "open_container", "Open"),
        ("r", "refresh", "Refresh"),
        ("question_mark", "help", "Help"),
        ("q", "quit_app", "Quit"),
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        gateway: DockerGateway,
        config: ApplicationConfiguration | None = None,
    ) -> None:
        super().__init__()
        self._gateway = gateway
        self._app_config = config or ApplicationConfiguration()
        self._selected_index = 0
        self._container_index = 0
        self._refreshing = False

    @property
    def diagnostics(self) -> bool:
        """Whether diagnostic detail is shown on screen."""
        return self._app_config.logging.debug

    def compose(self) -> ComposeResult:
        yield app_header()
        yield StatusView(id="status-view")
        yield ContainerListView()
        yield Static("Probing Docker…", id="loading")
        yield app_footer()

    def on_mount(self) -> None:
        """Render first, then probe Docker off the render loop."""
        self._start_probe()

    def _start_probe(self) -> None:
        if self._refreshing:
            return
        self._refreshing = True
        try:
            loading = self.query_one("#loading", Static)
            loading.update("Probing Docker…")
            loading.display = True
        except Exception:  # noqa: BLE001 - headless/test contexts
            pass
        self.run_worker(self._probe_and_update, exclusive=True, thread=True)

    def _probe_and_update(self) -> None:
        try:
            snapshot = services.refresh_snapshot(self._gateway)
            containers = services.list_managed(self._gateway)
        except Exception as exc:  # noqa: BLE001 - never crash the worker
            log.debug("Refresh worker failed: %r", exc)
            return
        self.call_from_thread(self._show_snapshot, snapshot, containers)

    def _show_snapshot(
        self, snapshot: DockerSnapshot, containers: list[ManagedContainer] | None = None
    ) -> None:
        self._refreshing = False
        rows = containers if containers is not None else []
        try:
            self.query_one("#loading", Static).display = False
            self.query_one("#status-view", StatusView).show_snapshot(
                snapshot, debug=self.diagnostics
            )
            note = ""
            if not rows and snapshot.state is not ConnectionState.CONNECTED:
                note = "No container data while the Engine is unreachable."
            self.query_one("#container-list", ContainerListView).show_containers(rows, note=note)
            self._container_index = self.query_one("#container-list", ContainerListView).position
        except Exception:  # noqa: BLE001 - shutting down
            pass

    def _move_selection(self, delta: int) -> None:
        # Prefer the container list when it has rows; else move status rows.
        try:
            container_view = self.query_one("#container-list", ContainerListView)
        except Exception:  # noqa: BLE001 - headless/test contexts
            container_view = None
        if container_view is not None and container_view.row_texts():
            container_view.move_selection(delta)
            self._container_index = container_view.position
            return
        # Move highlight across the fixed status rows.
        self._selected_index = max(
            0, min(len(StatusView.FIELD_IDS) - 1, self._selected_index + delta)
        )
        try:
            view = self.query_one("#status-view", StatusView)
            for position, field_id in enumerate(StatusView.FIELD_IDS):
                row = view.query_one(f"#row-{field_id}", FieldRow)
                if position == self._selected_index:
                    row.add_class("selected")
                else:
                    row.remove_class("selected")
        except Exception:  # noqa: BLE001 - headless/test contexts
            pass

    def action_move_down(self) -> None:
        """Move selection down (j)."""
        self._move_selection(1)

    def action_move_up(self) -> None:
        """Move selection up (k)."""
        self._move_selection(-1)

    def action_open_container(self) -> None:
        """Open details for the highlighted container (Enter)."""
        try:
            selected = self.query_one("#container-list", ContainerListView).selected()
        except Exception:  # noqa: BLE001 - headless/test contexts
            return
        if selected is not None:
            self.push_screen(ContainerDetailsScreen(selected, self._gateway), self._after_details)

    def _after_details(self, mutated: bool | None) -> None:
        """Refresh the list after a mutating details session."""
        if mutated:
            self._start_probe()

    def action_refresh(self) -> None:
        """Manually re-probe Docker (r). No timers; manual-only."""
        self._start_probe()

    def action_help(self) -> None:
        """Open the keyboard help modal (?)."""
        self.push_screen(HelpScreen())

    def action_cancel(self) -> None:
        """Close help or cancel (Esc)."""
        if isinstance(self.screen, HelpScreen):
            self.pop_screen()

    def action_quit_app(self) -> None:
        """Quit cleanly, closing help first when open (q)."""
        if isinstance(self.screen, HelpScreen):
            self.pop_screen()
        else:
            self.exit()
