"""US2: lifecycle actions, confirmation gate, and self-block (no daemon)."""

from __future__ import annotations

from datetime import UTC, datetime

from docker_tui import services
from docker_tui.config import ApplicationConfiguration
from docker_tui.docker_gateway import (
    ConnectionState,
    ContainerStateBucket,
    DockerGateway,
    DockerSnapshot,
    ManagedContainer,
)
from docker_tui.tui.app import DockerTUIApp
from docker_tui.tui.screens import ConfirmScreen, ContainerDetailsScreen


def _row(name: str, status: str = "exited", is_self: bool = False) -> ManagedContainer:
    bucket = (
        ContainerStateBucket.RUNNING
        if status in ("running", "restarting")
        else ContainerStateBucket.STOPPED
    )
    return ManagedContainer(
        container_id=f"id-{name}",
        name=name,
        image_ref="img:1",
        state_bucket=bucket,
        exact_status=status,
        is_self=is_self,
    )


class FakeLifecycleGateway(DockerGateway):
    def __init__(self, rows: list[ManagedContainer]) -> None:
        self._rows = {row.container_id: row for row in rows}
        self.calls: list[str] = []

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
        return list(self._rows.values())

    def get_container(self, container_id: str) -> ManagedContainer:
        return self._rows[container_id]

    def container_logs(self, container_id: str, tail: int = 200):  # type: ignore[no-untyped-def]
        raise AssertionError("not used here")

    def _refresh(self, container_id: str, status: str) -> ManagedContainer:
        row = self._rows[container_id]
        updated = ManagedContainer(
            container_id=row.container_id,
            name=row.name,
            image_ref=row.image_ref,
            state_bucket=(
                ContainerStateBucket.RUNNING
                if status == "running"
                else ContainerStateBucket.STOPPED
            ),
            exact_status=status,
            is_self=row.is_self,
        )
        self._rows[container_id] = updated
        return updated

    def start_container(self, container_id: str) -> ManagedContainer:
        self.calls.append(f"start:{container_id}")
        return self._refresh(container_id, "running")

    def stop_container(self, container_id: str) -> ManagedContainer:
        self.calls.append(f"stop:{container_id}")
        return self._refresh(container_id, "exited")

    def restart_container(self, container_id: str) -> ManagedContainer:
        self.calls.append(f"restart:{container_id}")
        return self._refresh(container_id, "running")

    def remove_container(self, container_id: str) -> None:
        self.calls.append(f"remove:{container_id}")
        del self._rows[container_id]


def _app(rows: list[ManagedContainer]) -> tuple[DockerTUIApp, FakeLifecycleGateway]:
    gateway = FakeLifecycleGateway(rows)
    return DockerTUIApp(gateway=gateway, config=ApplicationConfiguration()), gateway


async def test_stop_action_updates_row() -> None:
    app, gateway = _app([_row("web", status="running")])
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, ContainerDetailsScreen)
        await pilot.press("t")
        await pilot.pause()
        await pilot.pause()
        assert "stop:id-web" in gateway.calls


async def test_remove_requires_confirmation() -> None:
    app, gateway = _app([_row("web")])
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press("n")
        await pilot.pause()
        assert "remove:id-web" not in gateway.calls
        assert isinstance(app.screen, ContainerDetailsScreen)
        await pilot.press("d")
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()
        await pilot.pause()
        assert "remove:id-web" in gateway.calls


async def test_self_stop_blocked_with_message() -> None:
    app, gateway = _app([_row("web", status="running", is_self=True)])
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("t")
        await pilot.pause()
        await pilot.pause()
        assert "stop:id-web" not in gateway.calls
        screen = app.screen
        assert isinstance(screen, ContainerDetailsScreen)
        assert "own container" in screen.last_result


def test_service_remove_without_confirmation_fails() -> None:
    gateway = FakeLifecycleGateway([_row("web")])
    try:
        services.remove_managed(gateway, _row("web"), confirmed=False)
    except Exception as exc:
        assert "Confirm removal first" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ContainerOperationError")
