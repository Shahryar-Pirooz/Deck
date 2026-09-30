"""US1: container list, selection, open, and container-aware guidance (no daemon)."""

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
from docker_tui.tui.screens import ContainerDetailsScreen, ContainerListView, StatusView


def _row(name: str, status: str = "running", is_self: bool = False) -> ManagedContainer:
    return ManagedContainer(
        container_id=f"id-{name}",
        name=name,
        image_ref="img:1",
        state_bucket=(
            ContainerStateBucket.RUNNING if status == "running" else ContainerStateBucket.STOPPED
        ),
        exact_status=status,
        is_self=is_self,
    )


class FakeListGateway(DockerGateway):
    def __init__(self, rows: list[ManagedContainer]) -> None:
        self._rows = rows

    @property
    def endpoint(self) -> str:
        return "fake://local"

    def get_snapshot(self) -> DockerSnapshot:
        return DockerSnapshot(
            state=ConnectionState.CONNECTED,
            summary=None,
            detail="Connected to Docker fake.",
            endpoint=self.endpoint,
            probed_at=datetime.now(UTC),
        )

    def list_containers(self) -> list[ManagedContainer]:
        return list(self._rows)

    def get_container(self, container_id: str) -> ManagedContainer:
        raise AssertionError("not used here")

    def container_logs(self, container_id: str, tail: int = 200):  # type: ignore[no-untyped-def]
        raise AssertionError("not used here")

    def start_container(self, container_id: str) -> ManagedContainer:
        raise AssertionError("not used here")

    def stop_container(self, container_id: str) -> ManagedContainer:
        raise AssertionError("not used here")

    def restart_container(self, container_id: str) -> ManagedContainer:
        raise AssertionError("not used here")

    def remove_container(self, container_id: str) -> None:
        raise AssertionError("not used here")


def _snapshot(state: ConnectionState) -> DockerSnapshot:
    return DockerSnapshot(
        state=state,
        summary=None,
        detail=state.value,
        endpoint="fake://local",
        probed_at=datetime.now(UTC),
    )


def test_row_text_marks_self() -> None:
    assert "← this container" in ContainerListView.row_text(_row("web", is_self=True))
    assert "← this container" not in ContainerListView.row_text(_row("db"))
    assert "[Running]" in ContainerListView.row_text(_row("web"))
    assert "[Stopped]" in ContainerListView.row_text(_row("db", status="exited"))


def test_list_selection_and_empty_note() -> None:
    view = ContainerListView()
    view.show_containers([_row("a"), _row("b")])
    assert view.selected() is not None and view.selected().name == "a"  # type: ignore[union-attr]
    view.move_selection(1)
    assert view.selected() is not None and view.selected().name == "b"  # type: ignore[union-attr]
    assert view.position == 1
    view.move_selection(5)
    assert view.position == 1
    empty = ContainerListView()
    empty.show_containers([], note="why empty")
    assert empty.selected() is None
    assert len(empty.row_texts()) == 0


def test_unavailable_guidance_names_container_run(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(services, "is_running_in_container", lambda: True)
    view = StatusView()
    view.show_snapshot(_snapshot(ConnectionState.UNAVAILABLE))
    # Unmounted path keeps values blank; guidance logic must not raise.
    assert view.snapshot_values()["connection"] == ""


async def test_j_k_move_containers_when_rows_present() -> None:
    app = DockerTUIApp(
        gateway=FakeListGateway([_row("a"), _row("b")]),
        config=ApplicationConfiguration(),
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        view = app.query_one("#container-list", ContainerListView)
        assert len(view.row_texts()) == 2
        await pilot.press("j")
        await pilot.pause()
        assert app._container_index == 1
        await pilot.press("k")
        await pilot.pause()
        assert app._container_index == 0


async def test_enter_opens_details() -> None:
    app = DockerTUIApp(
        gateway=FakeListGateway([_row("a")]),
        config=ApplicationConfiguration(),
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, ContainerDetailsScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, ContainerDetailsScreen)
