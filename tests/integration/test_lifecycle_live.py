"""US2 integration: lifecycle against a live daemon; skip without one."""

from __future__ import annotations

import uuid

import pytest

from docker_tui import services
from docker_tui.docker_gateway import ConnectionState
from docker_tui.docker_sdk import SdkGateway

pytestmark = pytest.mark.integration


def _daemon_reachable() -> bool:
    try:
        return SdkGateway().get_snapshot().state is ConnectionState.CONNECTED
    except Exception:  # noqa: BLE001 - any failure means "no live daemon"
        return False


def test_live_lifecycle_round_trip() -> None:
    """Create → start → stop → remove a throwaway container on a live daemon."""
    if not _daemon_reachable():
        pytest.skip("no live Docker daemon")
    import docker

    name = f"deck-test-{uuid.uuid4().hex[:8]}"
    client = docker.from_env(timeout=30)
    container_id = ""
    try:
        try:
            native = client.containers.run("alpine:3.20", "sleep 60", detach=True, name=name)
        except Exception as exc:  # noqa: BLE001 - image/network unavailable
            pytest.skip(f"cannot provision test container: {exc}")
        container_id = str(native.id)
        gateway = SdkGateway()
        row = gateway.get_container(container_id)
        assert row.name == name
        stopped = services.stop_managed(gateway, row)
        assert stopped.exact_status in ("exited", "stopped", "created")
        started = services.start_managed(gateway, stopped)
        assert started.exact_status == "running"
        services.stop_managed(gateway, started)
        services.remove_managed(gateway, started, confirmed=True)
    finally:
        try:
            if container_id:
                client.containers.get(container_id).remove(force=True)
        except Exception:  # noqa: BLE001 - best-effort cleanup
            pass
        try:
            client.close()
        except Exception:  # noqa: BLE001 - best-effort cleanup
            pass
