"""US3 integration: manual refresh against a live daemon; skip without one."""

from __future__ import annotations

import pytest

from deck.config import ApplicationConfiguration
from deck.docker_gateway import ConnectionState
from deck.docker_sdk import SdkGateway
from deck.tui.app import DeckApp

pytestmark = pytest.mark.integration


async def test_refresh_live_updates() -> None:
    """Pressing r re-probes and keeps a populated status view."""
    try:
        if SdkGateway().get_snapshot().state is not ConnectionState.CONNECTED:
            pytest.skip("no live Docker daemon")
    except Exception:  # noqa: BLE001
        pytest.skip("no live Docker daemon")
    app = DeckApp(gateway=SdkGateway(), config=ApplicationConfiguration())
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("r")
        await pilot.pause()
        values = app.query_one("#status-view").snapshot_values()  # type: ignore[no-any-return]
        assert values["connection"] == "Connected"
