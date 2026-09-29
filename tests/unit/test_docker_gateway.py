"""US1/US2: gateway snapshot and error-classification tests (no live daemon)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from docker_tui.docker_gateway import (
    ConnectionState,
    DockerSnapshot,
    DockerSystemSummary,
)
from docker_tui.docker_sdk import SdkGateway, classify_error


def make_version() -> dict[str, object]:
    return {"Version": "29.8.1", "ApiVersion": "1.56", "Os": "linux", "Arch": "amd64"}


def make_info() -> dict[str, object]:
    return {
        "Containers": 5,
        "ContainersRunning": 2,
        "ContainersStopped": 3,
        "Images": 7,
    }


def make_client() -> MagicMock:
    client = MagicMock()
    client.ping.return_value = True
    client.version.return_value = make_version()
    client.info.return_value = make_info()
    return client


def test_success_snapshot_connected() -> None:
    """Faked SDK success yields connected + validated summary counts."""
    gateway = SdkGateway()
    with patch("docker_tui.docker_sdk.docker.from_env", return_value=make_client()):
        snapshot = gateway.get_snapshot()
    assert snapshot.state is ConnectionState.CONNECTED
    assert snapshot.summary is not None
    assert snapshot.summary.version == "29.8.1"
    assert snapshot.summary.os == "linux"
    assert snapshot.summary.architecture == "amd64"
    assert snapshot.summary.containers_total == 5
    assert snapshot.summary.containers_running == 2
    assert snapshot.summary.containers_stopped == 3
    assert snapshot.summary.images == 7
    assert (
        snapshot.summary.containers_running + snapshot.summary.containers_stopped
        <= snapshot.summary.containers_total
    )


def test_summary_rejects_negative_counts() -> None:
    with pytest.raises(ValueError):
        DockerSystemSummary(
            version="x",
            api_version=None,
            os="linux",
            architecture="amd64",
            containers_total=-1,
            containers_running=0,
            containers_stopped=0,
            images=0,
        )


def test_unavailable_on_missing_socket() -> None:
    gateway = SdkGateway()
    with patch(
        "docker_tui.docker_sdk.docker.from_env",
        side_effect=FileNotFoundError(2, "No such file or directory"),
    ):
        snapshot = gateway.get_snapshot()
    assert snapshot.state is ConnectionState.UNAVAILABLE
    assert snapshot.summary is None


def test_permission_denied_distinct() -> None:
    gateway = SdkGateway()
    with patch(
        "docker_tui.docker_sdk.docker.from_env",
        side_effect=PermissionError(13, "Permission denied"),
    ):
        snapshot = gateway.get_snapshot()
    assert snapshot.state is ConnectionState.PERMISSION_DENIED
    assert snapshot.summary is None


def test_permission_denied_wrapped_in_ping() -> None:
    """Production chain: ping raises DockerException wrapping PermissionError."""
    from docker.errors import DockerException

    client = make_client()
    wrapped = PermissionError(13, "Permission denied")
    client.ping.side_effect = DockerException(
        f"Error while fetching server API version: {wrapped!r}"
    )
    try:
        raise client.ping.side_effect
    except DockerException as exc:
        exc.__cause__ = wrapped
        client.ping.side_effect = exc
    gateway = SdkGateway()
    with patch("docker_tui.docker_sdk.docker.from_env", return_value=client):
        snapshot = gateway.get_snapshot()
    assert snapshot.state is ConnectionState.PERMISSION_DENIED


def test_connection_failed_fallback() -> None:
    gateway = SdkGateway()
    with patch(
        "docker_tui.docker_sdk.docker.from_env",
        side_effect=ConnectionRefusedError("refused"),
    ):
        snapshot = gateway.get_snapshot()
    assert snapshot.state is ConnectionState.CONNECTION_FAILED


def test_classify_error_never_leaks_sdk_types() -> None:
    state, detail = classify_error(RuntimeError("boom"))
    assert state is ConnectionState.CONNECTION_FAILED
    assert "boom" not in detail  # user guidance only, no raw internals
    assert isinstance(detail, str) and detail


def test_probing_initial_state() -> None:
    snapshot = DockerSnapshot.probing("unix:///var/run/docker.sock")
    assert snapshot.state is ConnectionState.UNAVAILABLE
    assert snapshot.detail == "Probing…"
    assert isinstance(snapshot.probed_at, datetime)
    assert snapshot.probed_at.tzinfo is UTC
