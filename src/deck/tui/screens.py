"""Status screen layout, container views, and help modal."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, LoadingIndicator, Static

from deck import services
from deck.docker_gateway import (
    ConnectionState,
    ContainerOperationError,
    ContainerStateBucket,
    DockerGateway,
    DockerSnapshot,
    ManagedContainer,
    ManagedImage,
    ManagedNetwork,
    ManagedVolume,
    ResourceType,
)
from deck.tui.widgets import FieldRow, SidebarView

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
    ("1-4", "Containers / Images / Volumes / Networks"),
    ("Enter", "Open selected resource"),
    ("s/t/r/d/l", "Start / stop / restart / remove / logs (in details)"),
    ("y / n", "Confirm / cancel removal"),
    ("r", "Refresh Docker information"),
    ("?", "Show this help"),
    ("Esc", "Close / cancel"),
    ("q", "Quit"),
)

CONTAINER_BUCKET_LABELS = {
    ContainerStateBucket.RUNNING: "Running",
    ContainerStateBucket.STOPPED: "Stopped",
    ContainerStateBucket.OTHER: "Other",
}

CONTAINER_ENGINE_HINT = (
    "Running as a container: share the host Engine access into this container,\n"
    "then press r to retry."
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
                if (
                    snapshot.state is ConnectionState.UNAVAILABLE
                    and services.is_running_in_container()
                ):
                    guidance = (
                        f"{CONTAINER_ENGINE_HINT}\n{guidance}"
                        if guidance
                        else CONTAINER_ENGINE_HINT
                    )
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


class ContainerListView(Static):
    """Sibling container rows with keyboard selection."""

    def __init__(self, container_id: str = "container-list", **kwargs) -> None:
        if "id" in kwargs:
            container_id = kwargs.pop("id")
        super().__init__(id=container_id, **kwargs)
        self._containers: list[ManagedContainer] = []
        self._selected = 0
        self._note = ""

    @staticmethod
    def row_text(container: ManagedContainer) -> str:
        """One plain-text row (for display and tests)."""
        bucket = CONTAINER_BUCKET_LABELS.get(container.state_bucket, container.exact_status)
        text = f"{container.name}  {container.image_ref}  [{bucket}]"
        if container.is_self:
            text += "  ← this container"
        return text

    def show_containers(self, containers: list[ManagedContainer], note: str = "") -> None:
        """Replace rows; empty lists render a note instead of blanks."""
        self._containers = list(containers)
        self._note = note
        self._selected = max(0, min(self._selected, max(len(self._containers) - 1, 0)))
        try:
            self.update(self._render_rows())
        except Exception:  # noqa: BLE001 - unmounted in unit tests
            pass

    def move_selection(self, delta: int) -> None:
        """Move highlight; no-op on an empty list."""
        if not self._containers:
            return
        self._selected = max(0, min(len(self._containers) - 1, self._selected + delta))
        try:
            self.update(self._render_rows())
        except Exception:  # noqa: BLE001 - unmounted in unit tests
            pass

    def selected(self) -> ManagedContainer | None:
        """Currently highlighted row, if any."""
        if not self._containers:
            return None
        return self._containers[self._selected]

    @property
    def position(self) -> int:
        """Current highlight index (for tests and app wiring)."""
        return self._selected

    def row_texts(self) -> list[str]:
        """Current row strings (for tests)."""
        return [self.row_text(container) for container in self._containers]

    def _render_rows(self) -> Text:
        rendered = Text()
        if not self._containers:
            rendered.append("No containers found.")
            if self._note:
                rendered.append(f"\n{self._note}")
            return rendered
        for position, container in enumerate(self._containers):
            prefix = "> " if position == self._selected else "  "
            style = "reverse" if position == self._selected else ""
            rendered.append(f"{prefix}{self.row_text(container)}\n", style=style)
        return rendered


class ResourceListView(ContainerListView):
    """Unified selectable list for all Docker resource types.

    Container-specific methods remain available so existing container behavior
    and tests continue to work.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._resource_type = ResourceType.CONTAINERS
        self._resources: list[
            ManagedImage | ManagedVolume | ManagedNetwork
        ] = []
        self._state = "ready"
        self._state_message = ""

    @staticmethod
    def format_image(image: ManagedImage) -> str:
        size = _format_size(image.size_bytes)
        return f"{image.repository_tag}  {image.image_id}  {size}  {image.created}"

    @staticmethod
    def format_volume(volume: ManagedVolume) -> str:
        return f"{volume.name}  {volume.driver}  {volume.mountpoint}"

    @staticmethod
    def format_network(network: ManagedNetwork) -> str:
        return f"{network.name}  {network.driver}  {network.scope}"

    def show_resource(
        self,
        resource_type: ResourceType,
        rows: list[ManagedImage | ManagedVolume | ManagedNetwork],
        *,
        state: str = "ready",
        message: str = "",
        position: int = 0,
    ) -> None:
        self._resource_type = resource_type
        self._resources = list(rows)
        self._state = state
        self._state_message = message
        self._selected = max(0, min(position, max(len(self._resources) - 1, 0)))
        try:
            self.update(self._render_resource_rows())
        except Exception:  # noqa: BLE001 - unmounted in unit tests
            pass

    def move_selection(self, delta: int) -> None:
        if self._resource_type is ResourceType.CONTAINERS:
            super().move_selection(delta)
            return
        if not self._resources:
            return
        self._selected = max(0, min(len(self._resources) - 1, self._selected + delta))
        try:
            self.update(self._render_resource_rows())
        except Exception:  # noqa: BLE001
            pass

    def selected_resource(self) -> ManagedImage | ManagedVolume | ManagedNetwork | None:
        if self._resource_type is ResourceType.CONTAINERS or not self._resources:
            return None
        return self._resources[self._selected]

    @property
    def resource_position(self) -> int:
        return self._selected

    def resource_rows(self) -> list[str]:
        if self._resource_type is ResourceType.CONTAINERS:
            return self.row_texts()
        formatter = {
            ResourceType.IMAGES: self.format_image,
            ResourceType.VOLUMES: self.format_volume,
            ResourceType.NETWORKS: self.format_network,
        }.get(self._resource_type)
        return [formatter(row) for row in self._resources] if formatter else []

    def _render_resource_rows(self) -> Text:
        rendered = Text()
        labels = {
            ResourceType.CONTAINERS: "Containers",
            ResourceType.IMAGES: "Images",
            ResourceType.VOLUMES: "Volumes",
            ResourceType.NETWORKS: "Networks",
        }
        rendered.append(labels[self._resource_type], style="bold")
        rendered.append("\n\n")
        if self._state != "ready":
            rendered.append(self._state_message or "Loading…")
            return rendered
        rows = self.resource_rows()
        if not rows:
            rendered.append(f"No {labels[self._resource_type].lower()} found.")
            return rendered
        for position, row in enumerate(rows):
            prefix = "> " if position == self._selected else "  "
            rendered.append(f"{prefix}{row}\n", style="reverse" if position == self._selected else "")
        return rendered


def _format_size(size_bytes: int) -> str:
    value = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size_bytes} B"


class ResourceDetailsScreen(ModalScreen[None]):
    """Read-only details for an image, volume, or network."""

    BINDINGS = [
        ("escape", "close_details", "Close"),
        ("q", "close_details", "Close"),
    ]

    def __init__(self, resource: ManagedImage | ManagedVolume | ManagedNetwork) -> None:
        super().__init__()
        self._resource = resource

    def compose(self) -> ComposeResult:
        yield Static(self._details_text(), id="resource-details-text")

    def _details_text(self) -> str:
        resource = self._resource
        if isinstance(resource, ManagedImage):
            return "\n".join((
                "Image Details",
                "",
                f"Repository / tag: {resource.repository_tag}",
                f"ID: {resource.image_id}",
                f"Size: {_format_size(resource.size_bytes)}",
                f"Created: {resource.created}",
                "",
                "Read-only. Press Esc or q to close.",
            ))
        if isinstance(resource, ManagedVolume):
            return "\n".join((
                "Volume Details",
                "",
                f"Name: {resource.name}",
                f"Driver: {resource.driver}",
                f"Mountpoint: {resource.mountpoint}",
                "",
                "Read-only. Press Esc or q to close.",
            ))
        return "\n".join((
            "Network Details",
            "",
            f"Name: {resource.name}",
            f"ID: {resource.network_id}",
            f"Driver: {resource.driver}",
            f"Scope: {resource.scope}",
            "",
            "Read-only. Press Esc or q to close.",
        ))

    def action_close_details(self) -> None:
        self.dismiss(None)


class ConfirmScreen(ModalScreen[bool]):
    """Explicit confirmation gate for destructive actions.

    Dismisses with True on confirmation, False otherwise. ``q``/``Esc``/``n``
    never confirm.
    """

    BINDINGS = [
        ("y", "confirm", "Confirm"),
        ("n", "cancel_confirm", "Cancel"),
        ("escape", "cancel_confirm", "Cancel"),
        ("q", "cancel_confirm", "Cancel"),
    ]

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        yield Static(f"{self._message}\n\nPress y to confirm, n to cancel.", id="confirm-text")

    def action_confirm(self) -> None:
        """Confirm the destructive action."""
        self.dismiss(True)

    def action_cancel_confirm(self) -> None:
        """Cancel without confirming."""
        self.dismiss(False)


class ContainerDetailsScreen(ModalScreen[bool]):
    """Details for one container with lifecycle actions.

    Dismisses with True when a mutation succeeded (caller should refresh),
    False/None on plain close. Dismiss with Esc or q.
    """

    BINDINGS = [
        ("s", "start_it", "Start"),
        ("t", "stop_it", "Stop"),
        ("r", "restart_it", "Restart"),
        ("d", "remove_it", "Remove..."),
        ("l", "view_logs", "Logs"),
        ("escape", "dismiss_details", "Close"),
        ("q", "dismiss_details", "Close"),
    ]

    def __init__(self, container: ManagedContainer, gateway: DockerGateway | None = None) -> None:
        super().__init__()
        self._container = container
        self._gateway = gateway
        self.last_result = ""
        self.last_logs: list[str] = []

    def compose(self) -> ComposeResult:
        yield Static(self._details_text(), id="details-text")
        yield Static(
            "Actions: s start · t stop · r restart · d remove (confirms first) · l logs",
            id="details-actions",
        )
        yield Static("", id="details-result")
        yield Static("Logs: press l to fetch.", id="details-logs")

    def _details_text(self) -> str:
        container = self._container
        bucket = CONTAINER_BUCKET_LABELS.get(container.state_bucket, container.exact_status)
        lines = [
            f"Container: {container.name}",
            f"Image: {container.image_ref}",
            f"State: {bucket} ({container.exact_status})",
        ]
        if container.is_self:
            lines.append("Note: this is the manager's own container.")
        lines.extend(("", "Press Esc or q to close."))
        return "\n".join(lines)

    def _show_result(self, text: str) -> None:
        self.last_result = text
        try:
            self.query_one("#details-result", Static).update(text)
        except Exception:  # noqa: BLE001 - unmounted in unit tests
            pass

    def _refresh_details(self) -> None:
        try:
            self.query_one("#details-text", Static).update(self._details_text())
        except Exception:  # noqa: BLE001 - unmounted in unit tests
            pass

    def _run_action(self, kind: str) -> None:
        if self._gateway is None:
            self._show_result("Engine unavailable.")
            return
        gateway = self._gateway
        container = self._container

        def work() -> None:
            try:
                if kind == "start":
                    updated = services.start_managed(gateway, container)
                elif kind == "stop":
                    updated = services.stop_managed(gateway, container)
                elif kind == "restart":
                    updated = services.restart_managed(gateway, container)
                else:  # pragma: no cover - guarded by bindings
                    return
            except services.SelfActionBlocked as exc:
                self.app.call_from_thread(self._show_result, str(exc))
                return
            except ContainerOperationError as exc:
                self.app.call_from_thread(self._show_result, str(exc))
                return
            except Exception as exc:  # noqa: BLE001 - never crash the worker
                self.app.call_from_thread(self._show_result, f"Action failed: {exc}")
                return
            self._container = updated
            self.app.call_from_thread(self._after_mutation, f"{kind} done: {updated.name}.")

        self.run_worker(work, thread=True)

    def _after_mutation(self, text: str) -> None:
        self._refresh_details()
        self._show_result(text)

    def _do_remove(self, confirmed: bool | None) -> None:
        if not confirmed or self._gateway is None:
            if not confirmed:
                self._show_result("Removal cancelled.")
            return
        gateway = self._gateway
        container = self._container

        def work() -> None:
            try:
                services.remove_managed(gateway, container, confirmed=True)
            except services.SelfActionBlocked as exc:
                self.app.call_from_thread(self._show_result, str(exc))
                return
            except ContainerOperationError as exc:
                self.app.call_from_thread(self._show_result, str(exc))
                return
            except Exception as exc:  # noqa: BLE001 - never crash the worker
                self.app.call_from_thread(self._show_result, f"Action failed: {exc}")
                return
            self.app.call_from_thread(self.dismiss, True)

        self.run_worker(work, thread=True)

    def action_start_it(self) -> None:
        """Start the container (s)."""
        self._run_action("start")

    def action_stop_it(self) -> None:
        """Stop the container gracefully (t)."""
        self._run_action("stop")

    def action_restart_it(self) -> None:
        """Restart the container (r)."""
        self._run_action("restart")

    def action_remove_it(self) -> None:
        """Ask for confirmation, then remove (d)."""
        if self._gateway is None:
            self._show_result("Engine unavailable.")
            return
        self.app.push_screen(
            ConfirmScreen(f"Remove container '{self._container.name}'?"),
            self._do_remove,
        )

    def _show_logs(self, lines: list[str]) -> None:
        self.last_logs = lines
        try:
            body = "\n".join(lines) if lines else "(no log output)"
            self.query_one("#details-logs", Static).update(f"Logs (latest {len(lines)}):\n{body}")
        except Exception:  # noqa: BLE001 - unmounted in unit tests
            pass

    def action_view_logs(self) -> None:
        """Fetch and show recent logs with a loading indication (l)."""
        if self._gateway is None:
            self._show_result("Engine unavailable.")
            return
        gateway = self._gateway
        container = self._container
        try:
            self.query_one("#details-logs", Static).update("Fetching logs…")
        except Exception:  # noqa: BLE001 - unmounted in unit tests
            pass

        def work() -> None:
            try:
                lines = services.fetch_logs(gateway, container)
            except ContainerOperationError as exc:
                self.app.call_from_thread(self._show_result, str(exc))
                return
            except Exception as exc:  # noqa: BLE001 - never crash the worker
                self.app.call_from_thread(self._show_result, f"Action failed: {exc}")
                return
            self.app.call_from_thread(self._show_logs, lines)

        self.run_worker(work, thread=True)

    def action_dismiss_details(self) -> None:
        """Close the details modal."""
        self.dismiss(False)


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
