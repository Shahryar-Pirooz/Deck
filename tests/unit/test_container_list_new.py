"""Table-based resource lists with scrolling support.

US1: container list, selection, open, and container-aware guidance (with modern table UX)
"""

from __future__ import annotations

from datetime import UTC, datetime

from deck import services
from deck.config import ApplicationConfiguration
from deck.docker_gateway import (
    ConnectionState,
    ContainerStateBucket,
    DockerGateway,
    DockerSnapshot,
    ManagedContainer,
)
from deck.tui.app import DeckApp
from deck.tui.screens import ContainerDetailsScreen, ContainerListView, ResourceListView, StatusView


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


async def test_j_k_move_containers_when_rows_present() -> None:
    app = DeckApp(
        gateway=FakeListGateway([_row("a"), _row("b")]),
        config=ApplicationConfiguration(),
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        view = app.query_one("#container-list", ResourceListView)
        # Check that table has correct columns
        assert view._table is not None
        assert len(view.COLUMNS) == 3
        assert "NAME" in view.COLUMNS
        # Check selection is at first row
        assert view._selected == 0
        # Test navigation
        await pilot.press("j")
        await pilot.pause()
        assert view._selected == 1
        await pilot.press("k")
        await pilot.pause()
        assert view._selected == 0


async def test_enter_opens_details() -> None:
    app = DeckApp(
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
