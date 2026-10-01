"""Textual application: render-first startup, worker-thread probes, Vim bindings."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from textual.app import App, ComposeResult
from textual.widgets import Static

from deck import services
from deck.config import ApplicationConfiguration
from deck.docker_gateway import (
    ConnectionState,
    DockerGateway,
    DockerSnapshot,
    ManagedContainer,
)
from deck.tui.screens import (
    ContainerDetailsScreen,
    ContainerListView,
    HelpScreen,
    StatusView,
    app_footer,
    app_header,
)
from deck.tui.widgets import FieldRow

log = logging.getLogger(__name__)


class DockerTUIApp(App[None]):
    """Keyboard-first Docker manager with a compact, responsive layout."""

    CSS = """
    Screen {
        background: $surface;
    }

    Header {
        height: 3;
        dock: top;
    }

    Footer {
        height: 1;
    }

    #status-view {
        height: 16;
        margin: 0 1;
        padding: 0 1;
        border: round $primary;
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 1fr;
        column-span: 2;
    }

    #status-view .panel-title {
        column-span: 2;
        height: 1;
        color: $text-accent;
        text-style: bold;
    }

    #status-view .field-label {
        width: 16;
        color: $text-muted;
    }

    #status-view .field-value {
        color: $text;
    }

    #status-view .detail {
        column-span: 2;
        color: $text-muted;
        height: auto;
    }

    #container-list {
        height: 1fr;
        margin: 0 1;
        padding: 1;
        border: round $secondary;
        overflow-y: auto;
        color: $text;
    }

    #container-list .panel-title {
        color: $text-accent;
        text-style: bold;
    }

    #loading {
        height: 1;
        margin: 0 2;
        color: $text-muted;
    }

    .selected {
        text-style: bold reverse;
    }

    ModalScreen {
        align: center middle;
        background: $background 70%;
    }

    #details-dialog, #confirm-dialog, #help-dialog {
        width: 80%;
        max-width: 100;
        max-height: 80%;
        padding: 2;
        border: round $primary;
        background: $surface;
    }

    #details-text, #confirm-text, #help-text {
        width: 1fr;
    }

    #details-actions, #details-result {
        margin-top: 1;
        color: $text-muted;
    }

    #details-logs {
        height: 1fr;
        margin-top: 1;
        padding: 1;
        border: round $secondary;
        overflow: auto;
    }
    """

    BINDINGS = [
        ("j", "move_down", "Down"),
        ("k", "move_up", "Up"),
        ("down", "move_down", "Down"),
        ("up", "move_up", "Up"),
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
        return self._app_config.logging.debug

    def compose(self) -> ComposeResult:
        yield app_header()
        yield StatusView(id="status-view")
        yield ContainerListView()
        yield Static("Connecting to Docker…", id="loading")
        yield app_footer()

    def on_mount(self) -> None:
        self._start_probe()

    def _start_probe(self) -> None:
        if self._refreshing:
            return
        self._refreshing = True
        try:
            loading = self.query_one("#loading", Static)
            loading.update("Connecting to Docker…")
            loading.display = True
        except Exception:
            pass
        self.run_worker(self._probe_and_update, exclusive=True, thread=True)

    def _probe_and_update(self) -> None:
        try:
            snapshot = services.refresh_snapshot(self._gateway)
            containers = services.list_managed(self._gateway)
        except Exception as exc:
            log.exception("Refresh worker failed: %r", exc)
            self.call_from_thread(self._probe_failed, str(exc))
            return
        self.call_from_thread(self._show_snapshot, snapshot, containers)

    def _probe_failed(self, detail: str) -> None:
        self._refreshing = False
        try:
            self.query_one("#loading", Static).display = False
            self.query_one("#status-view", StatusView).show_snapshot(
                DockerSnapshot(
                    state=ConnectionState.CONNECTION_FAILED,
                    summary=None,
                    detail=f"Refresh failed: {detail}",
                    endpoint=self._gateway.endpoint,
                    probed_at=datetime.now(UTC),
                ),
                debug=self.diagnostics,
            )
        except Exception:
            pass

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
                note = "Docker is unreachable; container actions are unavailable."
            view = self.query_one("#container-list", ContainerListView)
            view.show_containers(rows, note=note)
            self._container_index = view.position
        except Exception:
            pass

    def _move_selection(self, delta: int) -> None:
        try:
            container_view = self.query_one("#container-list", ContainerListView)
        except Exception:
            container_view = None
        if container_view is not None and container_view.row_texts():
            container_view.move_selection(delta)
            self._container_index = container_view.position
            return
        self._selected_index = max(
            0, min(len(StatusView.FIELD_IDS) - 1, self._selected_index + delta)
        )

    def action_move_down(self) -> None:
        self._move_selection(1)

    def action_move_up(self) -> None:
        self._move_selection(-1)

    def action_open_container(self) -> None:
        try:
            selected = self.query_one("#container-list", ContainerListView).selected()
        except Exception:
            return
        if selected is not None:
            self.push_screen(ContainerDetailsScreen(selected, self._gateway), self._after_details)

    def _after_details(self, mutated: bool | None) -> None:
        if mutated:
            self._start_probe()

    def action_refresh(self) -> None:
        self._start_probe()

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_cancel(self) -> None:
        if isinstance(self.screen, HelpScreen):
            self.pop_screen()

    def action_quit_app(self) -> None:
        if isinstance(self.screen, HelpScreen):
            self.pop_screen()
        else:
            self.exit()
