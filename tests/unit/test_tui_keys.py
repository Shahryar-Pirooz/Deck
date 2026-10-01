"""US4: Vim movement + help open/close via Pilot with faked gateway."""

from __future__ import annotations

from datetime import UTC, datetime

from deck.config import ApplicationConfiguration
from deck.docker_gateway import (
    ConnectionState,
    DockerGateway,
    DockerSnapshot,
)
from deck.tui.app import DockerTUIApp
from deck.tui.screens import HelpScreen, StatusView


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


def make_app() -> DockerTUIApp:
    return DockerTUIApp(gateway=FakeGateway(), config=ApplicationConfiguration())


async def test_j_k_move_selection() -> None:
    app = make_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app._selected_index == 0
        await pilot.press("j")
        await pilot.pause()
        assert app._selected_index == 1
        await pilot.press("k")
        await pilot.pause()
        assert app._selected_index == 0


async def test_help_open_close() -> None:
    app = make_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("question_mark")
        await pilot.pause()
        assert isinstance(app.screen, HelpScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, HelpScreen)


async def test_status_view_starts_unmounted_safe() -> None:
    view = StatusView()
    # show_snapshot before mount must not raise (unit-test path).
    view.show_snapshot(FakeGateway().get_snapshot())
    assert view.snapshot_values()["connection"] == ""
