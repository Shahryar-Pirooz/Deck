"""US1: Sidebar menu visible + view switching via 1-4 with sticky focus (Pilot, faked gateway)."""

from __future__ import annotations

from datetime import UTC, datetime

from deck.docker_gateway import (
    ConnectionState,
    DockerGateway,
    DockerSnapshot,
    ManagedImage,
    ManagedNetwork,
    ManagedVolume,
)
from deck.tui.app import DeckApp
from deck.tui.screens import SidebarView


class FakeGateway(DockerGateway):
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

    def list_images(self) -> list[ManagedImage]:
        return []

    def list_volumes(self) -> list[ManagedVolume]:
        return []

    def list_networks(self) -> list[ManagedNetwork]:
        return []


def make_app() -> DeckApp:
    return DeckApp(gateway=FakeGateway())


async def test_sidebar_has_four_entries_in_order() -> None:
    app = make_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        sidebar = app.query_one(SidebarView)
        assert sidebar is not None
        assert len(sidebar.entries) == 4
        assert sidebar.entries[0].label == "1 Containers"
        assert sidebar.entries[1].label == "2 Images"
        assert sidebar.entries[2].label == "3 Volumes"
        assert sidebar.entries[3].label == "4 Networks"


async def test_pressing_1_switches_to_containers() -> None:
    app = make_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("1")
        await pilot.pause()
        assert app.current_resource_type.value == "containers"
        sidebar = app.query_one(SidebarView)
        assert sidebar.active.value == "containers"


async def test_pressing_2_switches_to_images() -> None:
    app = make_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("2")
        await pilot.pause()
        assert app.current_resource_type.value == "images"
        sidebar = app.query_one(SidebarView)
        assert sidebar.active.value == "images"


async def test_pressing_3_switches_to_volumes() -> None:
    app = make_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("3")
        await pilot.pause()
        assert app.current_resource_type.value == "volumes"


async def test_pressing_4_switches_to_networks() -> None:
    app = make_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("4")
        await pilot.pause()
        assert app.current_resource_type.value == "networks"


async def test_focus_stays_in_main_list_after_switch() -> None:
    app = make_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("2")
        await pilot.pause()
        # Sidebar is non-focusable: focus should NOT be on the sidebar widget
        focused = app.focused
        assert not isinstance(focused, SidebarView)