"""Cross-cutting edge cases: daemon loss, no TTY context, unknown self (no daemon)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from deck import services
from deck.docker_gateway import (
    ConnectionState,
    ContainerStateBucket,
    DockerGateway,
    DockerSnapshot,
    ManagedContainer,
)
from deck.tui.screens import ContainerListView


def _row(name: str) -> ManagedContainer:
    return ManagedContainer(
        container_id=f"id-{name}",
        name=name,
        image_ref="img:1",
        state_bucket=ContainerStateBucket.RUNNING,
        exact_status="running",
    )


class FlappingGateway(DockerGateway):
    """Connected once, then the daemon goes away mid-session."""

    def __init__(self) -> None:
        self.up = True

    @property
    def endpoint(self) -> str:
        return "fake://local"

    def get_snapshot(self) -> DockerSnapshot:
        state = ConnectionState.CONNECTED if self.up else ConnectionState.UNAVAILABLE
        return DockerSnapshot(
            state=state,
            summary=None,
            detail=state.value,
            endpoint=self.endpoint,
            probed_at=datetime.now(UTC),
        )

    def list_containers(self) -> list[ManagedContainer]:
        if not self.up:
            from deck.docker_gateway import ContainerOperationError

            raise ContainerOperationError("list", "-", "daemon stopped.", "Retry with r.")
        return [_row("web")]

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


def test_daemon_loss_degrades_list_to_empty() -> None:
    gateway = FlappingGateway()
    assert [row.name for row in services.list_managed(gateway)] == ["web"]
    gateway.up = False
    assert services.refresh_snapshot(gateway).state is ConnectionState.UNAVAILABLE
    assert services.list_managed(gateway) == []


def test_unknown_self_applies_no_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(services.socket, "gethostname", lambda: "some-other-host")
    rows = services.mark_self([_row("web")])
    assert all(row.is_self is False for row in rows)


def test_hostname_lookup_failure_is_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> str:
        raise OSError("no hostname")

    monkeypatch.setattr(services.socket, "gethostname", boom)
    assert [row.name for row in services.mark_self([_row("web")])] == ["web"]


def test_empty_list_selection_is_stable() -> None:
    view = ContainerListView()
    view.show_containers([], note="Engine unreachable.")
    view.move_selection(1)
    assert view.selected() is None
    assert view.position == 0
