"""US3 integration: log fetching on a live daemon; skip without one."""

from __future__ import annotations

import pytest

from docker_tui import services
from docker_tui.docker_gateway import ConnectionState
from docker_tui.docker_sdk import SdkGateway

pytestmark = pytest.mark.integration


def test_live_logs_are_bounded() -> None:
    """Some container's logs fetch as a bounded list on a live daemon."""
    try:
        gateway = SdkGateway()
        if gateway.get_snapshot().state is not ConnectionState.CONNECTED:
            pytest.skip("no live Docker daemon")
        rows = gateway.list_containers()
    except Exception:  # noqa: BLE001 - any failure means "no live daemon"
        pytest.skip("no live Docker daemon")
    if not rows:
        pytest.skip("no containers to inspect")
    lines = services.fetch_logs(gateway, rows[0], tail=50)
    assert isinstance(lines, list)
    assert len(lines) <= 50
