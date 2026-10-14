"""Textual application: keyboard-first Docker resource manager."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from deck import services
from deck.config import ApplicationConfiguration
from deck.docker_gateway import (
    ConnectionState,
    DockerGateway,
    DockerSnapshot,
    ManagedContainer,
    ManagedImage,
    ManagedNetwork,
    ManagedVolume,
    ResourceType,
)
from deck.tui.run_config import RunConfigScreen
from deck.tui.screens import (
    ContainerDetailsScreen,
    HelpScreen,
    ResourceDetailsScreen,
    ResourceListView,
    StatusView,
    app_footer,
    app_header,
)
from deck.tui.widgets import SidebarView

log = logging.getLogger(__name__)


class DeckApp(App[None]):
    """Keyboard-first Docker manager with a persistent resource sidebar."""

    CSS = """
    Screen { background: $surface; }

    Header { height: 3; dock: top; }
    Footer { height: 1; }

    #main-layout { height: 1fr; width: 100%; }
    #content { width: 1fr; height: 1fr; }

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

    #status-view .field-label { width: 16; color: $text-muted; }
    #status-view .field-value { color: $text; }
    #status-view .detail { column-span: 2; color: $text-muted; height: auto; }

    #container-list {
        height: 1fr;
        margin: 0 1;
        padding: 1;
        border: round $secondary;
        overflow-y: auto;
        color: $text;
    }

    #container-list DataTable {
        height: 1fr;
        width: 100%;
        overflow-y: auto;
    }

    #loading {
        height: 1;
        margin: 0 2;
        color: $text-muted;
    }

    ModalScreen {
        align: center middle;
        background: $background 70%;
    }

    #details-dialog, #confirm-dialog, #help-dialog, #resource-details-text {
        width: 80%;
        max-width: 100;
        max-height: 80%;
        padding: 2;
        border: round $primary;
        background: $surface;
    }

    #details-text, #confirm-text, #help-text, #resource-details-text { width: 1fr; }
    #details-actions, #details-result { margin-top: 1; color: $text-muted; }
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
        # Enter reaches the focused widget first (e.g. Buttons in modals);
        # the DataTable emits RowSelected which calls action_open_selected.
        Binding("enter", "open_selected", "Open"),
        ("1", "switch_containers", "Containers"),
        ("2", "switch_images", "Images"),
        ("3", "switch_volumes", "Volumes"),
        ("4", "switch_networks", "Networks"),
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
        self.current_resource_type = ResourceType.CONTAINERS
        self._positions: dict[ResourceType, int] = dict.fromkeys(ResourceType, 0)
        self._load_generation = 0
        self._refreshing = False
        # Kept for compatibility with the original container-list tests.
        self._selected_index = 0

    @property
    def diagnostics(self) -> bool:
        return self._app_config.logging.debug

    def compose(self) -> ComposeResult:
        yield app_header()
        with Horizontal(id="main-layout"):
            yield SidebarView()
            with Vertical(id="content"):
                yield StatusView(id="status-view")
                yield ResourceListView(id="container-list")
                yield Static("Connecting to Docker…", id="loading")
        yield app_footer()

    def on_mount(self) -> None:
        # Honor display.theme from the config file (it was parsed but never applied).
        theme = "textual-light" if self._app_config.display.theme == "light" else "textual-dark"
        try:
            self.theme = theme
        except Exception:  # noqa: BLE001 - unknown theme name must not block startup
            log.debug("Could not apply theme %s", theme)
        self._start_resource_load(ResourceType.CONTAINERS)

    # ------------------------------------------------------------------
    # Resource switching/loading
    # ------------------------------------------------------------------

    def _switch_to(self, resource_type: ResourceType) -> None:
        """Switch immediately, then load only the requested resource type."""
        # Number shortcuts belong to the main screen, never to modal contexts.
        if len(self.screen_stack) > 1:
            return
        self._save_current_position()
        self.current_resource_type = resource_type
        self.query_one(SidebarView).update_highlight(resource_type)
        self._start_resource_load(resource_type)

    def action_switch_containers(self) -> None:
        self._switch_to(ResourceType.CONTAINERS)

    def action_switch_images(self) -> None:
        self._switch_to(ResourceType.IMAGES)

    def action_switch_volumes(self) -> None:
        self._switch_to(ResourceType.VOLUMES)

    def action_switch_networks(self) -> None:
        self._switch_to(ResourceType.NETWORKS)

    def _save_current_position(self) -> None:
        try:
            view = self.query_one("#container-list", ResourceListView)
            view.sync_selection()
            self._positions[self.current_resource_type] = view.position
        except Exception:  # noqa: BLE001 - safe during startup/tests
            pass

    def _start_resource_load(self, resource_type: ResourceType) -> None:
        self._load_generation += 1
        generation = self._load_generation
        self._refreshing = True
        view = self.query_one("#container-list", ResourceListView)
        loading_message = f"Loading {resource_type.value}…"
        view.show_resource(resource_type, [], state="loading", message=loading_message)
        loading = self.query_one("#loading", Static)
        loading.update(f"Loading {resource_type.value}…")
        loading.display = True
        self.run_worker(
            lambda: self._load_resource(resource_type, generation),
            name=f"load-{resource_type.value}",
            exclusive=True,
            thread=True,
        )

    def _load_resource(self, resource_type: ResourceType, generation: int) -> None:
        try:
            snapshot = services.refresh_snapshot(self._gateway)
            if resource_type is ResourceType.CONTAINERS:
                rows: list[ManagedContainer | ManagedImage | ManagedVolume | ManagedNetwork] = (
                    services.list_managed(self._gateway)
                )
            elif resource_type is ResourceType.IMAGES:
                rows = services.list_managed_images(self._gateway)
            elif resource_type is ResourceType.VOLUMES:
                rows = services.list_managed_volumes(self._gateway)
            else:
                rows = services.list_managed_networks(self._gateway)
        except Exception as exc:  # noqa: BLE001 - workers must never crash the TUI
            log.exception("Resource load failed: %r", exc)
            self.call_from_thread(self._resource_load_failed, resource_type, generation, str(exc))
            return
        self.call_from_thread(self._resource_loaded, resource_type, generation, snapshot, rows)

    def _resource_loaded(
        self,
        resource_type: ResourceType,
        generation: int,
        snapshot: DockerSnapshot,
        rows: list[ManagedContainer | ManagedImage | ManagedVolume | ManagedNetwork],
    ) -> None:
        if generation != self._load_generation or resource_type is not self.current_resource_type:
            return
        self._refreshing = False
        self.query_one("#loading", Static).display = False
        self.query_one("#status-view", StatusView).show_snapshot(snapshot, debug=self.diagnostics)
        view = self.query_one("#container-list", ResourceListView)
        position = self._positions[resource_type]

        if snapshot.state is not ConnectionState.CONNECTED:
            message = (
                f"{resource_type.value.title()} unavailable.\n\n"
                f"{snapshot.detail}\n\nPress r to retry."
            )
            view.show_resource(resource_type, [], state="unavailable", message=message)
            self._positions[resource_type] = 0
            return

        if resource_type is ResourceType.CONTAINERS:
            containers = [row for row in rows if isinstance(row, ManagedContainer)]
            view.show_containers(containers)
            view.select_row(position)
            self._selected_index = view.position
        else:
            row_types = (ManagedImage, ManagedVolume, ManagedNetwork)
            resources = [row for row in rows if isinstance(row, row_types)]
            view.show_resource(resource_type, resources, position=position)
        self._positions[resource_type] = view.position

    def _resource_load_failed(
        self, resource_type: ResourceType, generation: int, detail: str
    ) -> None:
        if generation != self._load_generation or resource_type is not self.current_resource_type:
            return
        self._refreshing = False
        self.query_one("#loading", Static).display = False
        self.query_one("#container-list", ResourceListView).show_resource(
            resource_type,
            [],
            state="unavailable",
            message=f"{resource_type.value.title()} unavailable.\n\n{detail}\n\nPress r to retry.",
        )

    # ------------------------------------------------------------------
    # Keyboard navigation
    # ------------------------------------------------------------------

    def _move_selection(self, delta: int) -> None:
        # j/k belong to the main list, never to an open modal.
        if len(self.screen_stack) > 1:
            return
        try:
            view = self.query_one("#container-list", ResourceListView)
        except Exception:  # noqa: BLE001
            return
        if self.current_resource_type is ResourceType.CONTAINERS and not view.row_texts():
            self._selected_index = max(0, self._selected_index + delta)
            return
        view.move_selection(delta)
        self._positions[self.current_resource_type] = view.position
        self._selected_index = view.position

    def action_move_down(self) -> None:
        self._move_selection(1)

    def action_move_up(self) -> None:
        self._move_selection(-1)

    def action_open_selected(self) -> None:
        # Enter must not stack another details modal on top of an open one.
        if len(self.screen_stack) > 1:
            return
        view = self.query_one("#container-list", ResourceListView)
        view.sync_selection()
        if self.current_resource_type is ResourceType.CONTAINERS:
            selected = view.selected()
            if selected is not None:
                self.push_screen(
                    ContainerDetailsScreen(selected, self._gateway), self._after_details
                )
            return
        selected_resource = view.selected_resource()
        if selected_resource is None:
            return
        if self.current_resource_type is ResourceType.IMAGES and isinstance(
            selected_resource, ManagedImage
        ):
            self.push_screen(RunConfigScreen(selected_resource, self._gateway), self._after_run)
            return
        self.push_screen(ResourceDetailsScreen(selected_resource))

    # ------------------------------------------------------------------
    # Existing container lifecycle behavior
    # ------------------------------------------------------------------

    def _after_details(self, mutated: bool | None) -> None:
        if mutated:
            self._save_current_position()
            self._start_resource_load(ResourceType.CONTAINERS)

    def _after_run(self, mutated: bool | None) -> None:
        """After a successful launch, show the new container in Containers view."""
        if mutated:
            self._save_current_position()
            self._switch_to(ResourceType.CONTAINERS)

    def action_refresh(self) -> None:
        if len(self.screen_stack) > 1:
            return
        self._save_current_position()
        self._start_resource_load(self.current_resource_type)

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_cancel(self) -> None:
        if isinstance(self.screen, HelpScreen):
            self.pop_screen()

    def action_quit_app(self) -> None:
        if isinstance(self.screen, HelpScreen):
            self.pop_screen()
        elif len(self.screen_stack) == 1:
            self.exit()


def build_failed_snapshot(gateway: DockerGateway, detail: str) -> DockerSnapshot:
    """Build a safe snapshot for unexpected UI-worker failures."""
    return DockerSnapshot(
        state=ConnectionState.CONNECTION_FAILED,
        summary=None,
        detail=f"Refresh failed: {detail}",
        endpoint=gateway.endpoint,
        probed_at=datetime.now(UTC),
    )
