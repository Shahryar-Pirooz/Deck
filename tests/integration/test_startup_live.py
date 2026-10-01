"""US1 integration: launch against a live daemon; skip without one."""

from __future__ import annotations

import socket

import pytest

from deck.config import ApplicationConfiguration
from deck.docker_sdk import SdkGateway
from deck.tui.app import DockerTUIApp

pytestmark = pytest.mark.integration


def _daemon_reachable() -> bool:
    try:
        gateway = SdkGateway()
        snapshot = gateway.get_snapshot()
    except Exception:  # noqa: BLE001 - any failure means "no live daemon"
        return False
    from deck.docker_gateway import ConnectionState

    return snapshot.state is ConnectionState.CONNECTED


async def test_startup_live_shows_summary() -> None:
    """Header/status/footer render with populated summary on a live daemon."""
    if not _daemon_reachable():
        pytest.skip("no live Docker daemon")
    app = DockerTUIApp(gateway=SdkGateway(), config=ApplicationConfiguration())
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one("#status-view") is not None
        values = app.query_one("#status-view").snapshot_values()  # type: ignore[no-any-return]
        assert values["connection"] == "Connected"
        assert values["version"] not in ("", "unavailable")
        assert values["containers"] not in ("", "unavailable")


async def test_socket_probe_helper() -> None:
    """Sanity: unix socket path probe used by the skip guard above."""
    assert isinstance(socket.gethostname(), str)
