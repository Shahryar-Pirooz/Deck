"""US4: clean quit and shutdown paths."""

from __future__ import annotations

from datetime import UTC, datetime

from deck.cli import build_gateway, parse_args
from deck.config import ApplicationConfiguration
from deck.docker_gateway import (
    ConnectionState,
    DockerGateway,
    DockerSnapshot,
)
from deck.docker_sdk import SdkGateway
from deck.tui.app import DeckApp
from deck.tui.screens import HelpScreen


class FakeGateway(DockerGateway):
    @property
    def endpoint(self) -> str:
        return "fake://local"

    def get_snapshot(self) -> DockerSnapshot:
        return DockerSnapshot(
            state=ConnectionState.UNAVAILABLE,
            summary=None,
            detail="Cannot connect.",
            endpoint=self.endpoint,
            probed_at=datetime.now(UTC),
        )


async def test_q_quits_from_main() -> None:
    app = DeckApp(gateway=FakeGateway(), config=ApplicationConfiguration())
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("q")
        await pilot.pause()


async def test_q_closes_help_first() -> None:
    app = DeckApp(gateway=FakeGateway(), config=ApplicationConfiguration())
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("question_mark")
        await pilot.pause()
        assert isinstance(app.screen, HelpScreen)
        await pilot.press("q")
        await pilot.pause()
        assert not isinstance(app.screen, HelpScreen)


def test_cli_builds_local_gateway() -> None:
    gateway = build_gateway(ApplicationConfiguration())
    assert isinstance(gateway, SdkGateway)


def test_parse_args_defaults() -> None:
    args = parse_args([])
    assert args.debug is False
    assert args.config is None
