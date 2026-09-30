"""US3: details content and log fetching behavior (no daemon)."""

from __future__ import annotations

from datetime import UTC, datetime

from docker_tui.config import ApplicationConfiguration
from docker_tui.docker_gateway import (
    ConnectionState,
    ContainerLogView,
    ContainerOperationError,
    ContainerStateBucket,
    DockerGateway,
    DockerSnapshot,
    ManagedContainer,
)
from docker_tui.tui.app import DockerTUIApp
from docker_tui.tui.screens import ContainerDetailsScreen


def _row(name: str = "web", status: str = "running") -> ManagedContainer:
    return ManagedContainer(
        container_id=f"id-{name}",
        name=name,
        image_ref="img:1",
        state_bucket=ContainerStateBucket.RUNNING,
        exact_status=status,
    )


class FakeInspectGateway(DockerGateway):
    def __init__(self, fail_logs: bool = False) -> None:
        self.fail_logs = fail_logs

    @property
    def endpoint(self) -> str:
        return "fake://local"

    def get_snapshot(self) -> DockerSnapshot:
        return DockerSnapshot(
            state=ConnectionState.CONNECTED,
            summary=None,
            detail="ok",
            endpoint=self.endpoint,
            probed_at=datetime.now(UTC),
        )

    def list_containers(self) -> list[ManagedContainer]:
        return [_row()]

    def get_container(self, container_id: str) -> ManagedContainer:
        return _row()

    def container_logs(self, container_id: str, tail: int = 200) -> ContainerLogView:
        if self.fail_logs:
            raise ContainerOperationError("logs", "web", "unavailable.", "Retry later.")
        return ContainerLogView(
            container_id=container_id,
            lines=("boot ok", "listening on 80"),
            fetched_at=datetime.now(UTC),
        )

    def start_container(self, container_id: str) -> ManagedContainer:
        raise AssertionError("not used here")

    def stop_container(self, container_id: str) -> ManagedContainer:
        raise AssertionError("not used here")

    def restart_container(self, container_id: str) -> ManagedContainer:
        raise AssertionError("not used here")

    def remove_container(self, container_id: str) -> None:
        raise AssertionError("not used here")


async def test_details_show_exact_status() -> None:
    app = DockerTUIApp(
        gateway=FakeInspectGateway(),
        config=ApplicationConfiguration(),
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, ContainerDetailsScreen)
        assert app.screen._container.name == "web"
        assert "running" in app.screen._details_text()


async def test_logs_key_shows_content() -> None:
    app = DockerTUIApp(
        gateway=FakeInspectGateway(),
        config=ApplicationConfiguration(),
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("l")
        await pilot.pause()
        await pilot.pause()
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, ContainerDetailsScreen)
        assert screen.last_logs == ["boot ok", "listening on 80"]


async def test_logs_failure_reports_actionable_error() -> None:
    app = DockerTUIApp(
        gateway=FakeInspectGateway(fail_logs=True),
        config=ApplicationConfiguration(),
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("l")
        await pilot.pause()
        await pilot.pause()
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, ContainerDetailsScreen)
        assert "Retry later" in screen.last_result
