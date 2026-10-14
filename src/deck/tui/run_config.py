"""Modal run-configuration overlay for launching containers from an image.

``RunConfigScreen`` collects name, ports, volumes, network and environment
variables, shows a confirmation review (Constitution §III) before any Docker
call, and dispatches the create+start through the service layer on a worker
thread so the TUI event loop never blocks (Constitution §V).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from deck import services
from deck.docker_gateway import (
    ContainerRunError,
    ContainerRunRequest,
    DockerGateway,
    ManagedImage,
)
from deck.tui.widgets import ListField


@dataclass
class RunConfigForm:
    """Pure form state for the run menu (unit-testable without Textual)."""

    name: str = ""
    ports: list[str] = field(default_factory=list)
    volumes: list[str] = field(default_factory=list)
    network: str = ""
    envs: list[str] = field(default_factory=list)

    def build_request(self, image: str) -> ContainerRunRequest:
        """Validate and convert the form into a run request."""
        name = services.validate_name(self.name)
        ports = tuple(services.parse_port_mapping(raw) for raw in self.ports)
        volumes = tuple(services.parse_volume_mount(raw) for raw in self.volumes)
        envs = tuple(services.parse_env_var(raw) for raw in self.envs)
        network = self.network.strip() or None
        return ContainerRunRequest(
            image=image,
            name=name,
            ports=ports,
            volumes=volumes,
            network=network,
            env_vars=envs,
        )

    def review_text(self, image: str) -> str:
        """Human-readable summary for the confirmation review screen."""
        lines = [
            "Review container configuration",
            "",
            f"Image:   {image}",
            f"Name:    {self.name.strip() or '(required)'}",
            f"Ports:   {', '.join(self.ports) if self.ports else '(none)'}",
            f"Volumes: {', '.join(self.volumes) if self.volumes else '(none)'}",
            f"Network: {self.network.strip() or 'default (bridge)'}",
            "Environment:",
        ]
        if self.envs:
            lines.extend(f"  {raw}" for raw in self.envs)
        else:
            lines.append("  (none)")
        return "\n".join(lines)


class RunConfirmScreen(ModalScreen[bool]):
    """Confirmation review shown before any Docker call (Constitution §III)."""

    BINDINGS = [
        ("y", "confirm_run", "Confirm"),
        ("enter", "confirm_run", "Confirm"),
        ("n", "cancel_confirm", "Back"),
        ("escape", "cancel_confirm", "Back"),
        ("q", "cancel_confirm", "Back"),
    ]

    def __init__(self, review_text: str) -> None:
        super().__init__()
        self._review_text = review_text

    def compose(self) -> ComposeResult:
        yield Static(
            f"{self._review_text}\n\nPress y to create and start, n/Esc to go back.",
            id="confirm-text",
            markup=False,
        )

    def action_confirm_run(self) -> None:
        """Confirm the launch."""
        self.dismiss(True)

    def action_cancel_confirm(self) -> None:
        """Return to the form without launching."""
        self.dismiss(False)


class RunConfigScreen(ModalScreen[bool]):
    """Modal form for launching a container from a selected image.

    Dismisses with True when a container was created and started (caller
    should switch/refresh the Containers view); False/None on cancel.
    """

    DEFAULT_CSS = """
    RunConfigScreen {
        align: center middle;
    }
    #run-dialog {
        width: 90%;
        max-width: 80;
        max-height: 95%;
        padding: 1;
        border: round $primary;
        background: $surface;
    }
    #run-title {
        text-style: bold;
        color: $text-accent;
        margin-bottom: 1;
    }
    #run-error {
        color: $error;
        height: auto;
    }
    #run-help {
        color: $text-muted;
        margin-top: 1;
    }
    #run-actions {
        margin-top: 1;
        height: 3;
    }
    """

    BINDINGS = [
        ("escape", "cancel_run", "Cancel"),
        ("q", "cancel_run", "Cancel"),
    ]

    def __init__(self, image: ManagedImage, gateway: DockerGateway | None = None) -> None:
        super().__init__()
        self._image = image
        self._gateway = gateway
        self.last_error = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="run-dialog"):
            yield Static(f"Run container from: {self._image.repository_tag}", id="run-title")
            yield Input(placeholder="container name (required)", id="run-name")
            yield ListField(
                "Ports (host:container)",
                "type e.g. 8080:80, press Enter",
                parser=services.parse_port_mapping,
                field_id="run-ports",
            )
            yield ListField(
                "Volumes (source:destination)",
                "type e.g. /data:/app/data, press Enter",
                parser=services.parse_volume_mount,
                field_id="run-volumes",
            )
            yield Input(placeholder="network name (empty = default bridge)", id="run-network")
            yield ListField(
                "Environment (KEY=value)",
                "type e.g. DEBUG=true, press Enter",
                parser=services.parse_env_var,
                field_id="run-envs",
            )
            yield Static("", id="run-error")
            yield Static(
                "n add entry · d remove entry · e edit · j/k move · Tab to buttons · Esc cancel",
                id="run-help",
            )
            with Vertical(id="run-actions"):
                yield Button("Review & Start", id="run-start", variant="primary")
                yield Button("Cancel", id="run-cancel")

    def on_mount(self) -> None:
        try:
            self.query_one("#run-name", Input).focus()
        except Exception:  # noqa: BLE001 - unmounted in unit tests
            pass

    # ------------------------------------------------------------------
    # Error surface
    # ------------------------------------------------------------------

    def _show_error(self, text: str) -> None:
        self.last_error = text
        try:
            self.query_one("#run-error", Static).update(text)
        except Exception:  # noqa: BLE001 - unmounted in unit tests
            pass

    def on_list_field_entry_rejected(self, message: ListField.EntryRejected) -> None:
        """Show the validation error for a rejected list entry."""
        self._show_error(message.text)

    def on_list_field_changed(self, message: ListField.Changed) -> None:
        """A successful list edit clears the error line."""
        self._show_error("")

    # ------------------------------------------------------------------
    # Form collection and launch
    # ------------------------------------------------------------------

    def _collect_form(self) -> RunConfigForm:
        return RunConfigForm(
            name=self.query_one("#run-name", Input).value,
            ports=self.query_one("#run-ports", ListField).values(),
            volumes=self.query_one("#run-volumes", ListField).values(),
            network=self.query_one("#run-network", Input).value,
            envs=self.query_one("#run-envs", ListField).values(),
        )

    def action_cancel_run(self) -> None:
        """Close the form without creating a container."""
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "run-cancel":
            self.dismiss(False)
        elif event.button.id == "run-start":
            self._review_and_start()

    def _review_and_start(self) -> None:
        form = self._collect_form()
        try:
            services.validate_name(form.name)
            # Parse eagerly so format errors appear before the review screen.
            form.build_request(self._image.repository_tag)
        except ContainerRunError as exc:
            self._show_error(exc.user_text())
            return
        self._show_error("")
        review = form.review_text(self._image.repository_tag)
        self.app.push_screen(RunConfirmScreen(review), self._after_confirm)

    def _after_confirm(self, confirmed: bool | None) -> None:
        if not confirmed:
            self._show_error("Launch cancelled. Press Review & Start to try again.")
            return
        form = self._collect_form()
        if self._gateway is None:
            self._show_error("Engine unavailable.")
            return
        gateway = self._gateway
        image = self._image.repository_tag

        def work() -> None:
            try:
                request = form.build_request(image)
                if not services.is_image_local(gateway, image):
                    services.pull_image(gateway, image)
                    self.app.call_from_thread(
                        self._notify,
                        f"Image {image} pulled successfully",
                        "information",
                    )
                services.run_managed(gateway, request)
            except ContainerRunError as exc:
                self.app.call_from_thread(self._run_failed, exc)
                return
            except Exception as exc:  # noqa: BLE001 - never crash the worker
                self.app.call_from_thread(
                    self._run_failed,
                    services.classify_run_error(exc),
                )
                return
            self.app.call_from_thread(self._run_succeeded, request.name)

        self.run_worker(work, thread=True, name="run-container")

    def _notify(self, text: str, severity: str = "information") -> None:
        try:
            self.app.notify(text, severity=severity)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001 - notifications optional in tests
            pass

    def _run_succeeded(self, name: str) -> None:
        self._notify(f"Container {name} started successfully", "information")
        self.dismiss(True)

    def _run_failed(self, exc: ContainerRunError) -> None:
        self._show_error(exc.user_text())
        self._notify(exc.user_text(), "error")
