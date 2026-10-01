"""Foundational container mapping, guards, and error rules (no live daemon)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from docker.errors import APIError

from deck import services
from deck.docker_gateway import (
    ConnectionState,
    ContainerLogView,
    ContainerOperationError,
    ContainerStateBucket,
    DockerGateway,
    DockerSnapshot,
    ManagedContainer,
    bucket_for_status,
)
from deck.docker_sdk import _operation_error, build_managed


def _row(name: str = "web", status: str = "running", self: bool = False) -> ManagedContainer:
    return ManagedContainer(
        container_id=f"id-{name}",
        name=name,
        image_ref="img:1",
        state_bucket=bucket_for_status(status),
        exact_status=status,
        is_self=self,
    )


class FakeManagedGateway(DockerGateway):
    """Scripted container gateway (no daemon)."""

    def __init__(self, rows: list[ManagedContainer]) -> None:
        self._rows = rows
        self.calls: list[str] = []
        self.fail_list = False

    @property
    def endpoint(self) -> str:
        return "fake://local"

    def get_snapshot(self) -> DockerSnapshot:
        return DockerSnapshot(
            state=ConnectionState.CONNECTED,
            summary=None,
            detail="ok",
            endpoint=self.endpoint,
            probed_at=datetime.now(UTC),
        )

    def list_containers(self) -> list[ManagedContainer]:
        if self.fail_list:
            raise ContainerOperationError("list", "-", "down.", "Retry.")
        return list(self._rows)

    def get_container(self, container_id: str) -> ManagedContainer:
        for row in self._rows:
            if row.container_id == container_id:
                return row
        raise ContainerOperationError("inspect", container_id, "not found.", "Refresh.")

    def container_logs(self, container_id: str, tail: int = 200) -> ContainerLogView:
        return ContainerLogView(
            container_id=container_id,
            lines=("line-1", "line-2"),
            fetched_at=datetime.now(UTC),
        )

    def start_container(self, container_id: str) -> ManagedContainer:
        self.calls.append(f"start:{container_id}")
        return self.get_container(container_id)

    def stop_container(self, container_id: str) -> ManagedContainer:
        self.calls.append(f"stop:{container_id}")
        return self.get_container(container_id)

    def restart_container(self, container_id: str) -> ManagedContainer:
        self.calls.append(f"restart:{container_id}")
        return self.get_container(container_id)

    def remove_container(self, container_id: str) -> None:
        self.calls.append(f"remove:{container_id}")
        self.get_container(container_id)


def test_bucket_mapping() -> None:
    assert bucket_for_status("running") is ContainerStateBucket.RUNNING
    assert bucket_for_status("Restarting") is ContainerStateBucket.RUNNING
    for status in ("exited", "created", "dead", "removing", "  EXITED "):
        assert bucket_for_status(status) is ContainerStateBucket.STOPPED
    assert bucket_for_status("paused") is ContainerStateBucket.OTHER
    assert bucket_for_status("mystery-state") is ContainerStateBucket.OTHER


def test_managed_container_rejects_empty_identity() -> None:
    with pytest.raises(ValueError):
        ManagedContainer(
            container_id="",
            name="x",
            image_ref="i",
            state_bucket=ContainerStateBucket.RUNNING,
            exact_status="running",
        )
    with pytest.raises(ValueError):
        ManagedContainer(
            container_id="a",
            name="",
            image_ref="i",
            state_bucket=ContainerStateBucket.RUNNING,
            exact_status="running",
        )


def test_log_view_bounds_tail() -> None:
    with pytest.raises(ValueError):
        ContainerLogView(
            container_id="a",
            lines=tuple(f"l{i}" for i in range(1001)),
            fetched_at=datetime.now(UTC),
        )


def test_mark_self_matches_hostname(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(services.socket, "gethostname", lambda: "id-web")
    rows = services.mark_self([_row("web"), _row("db")])
    assert rows[0].is_self is True
    assert rows[1].is_self is False


def test_mark_self_empty_hostname(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(services.socket, "gethostname", lambda: "")
    assert services.mark_self([_row("web")])[0].is_self is False


def test_self_actions_blocked() -> None:
    gateway = FakeManagedGateway([_row("web", self=True)])
    with pytest.raises(services.SelfActionBlocked):
        services.stop_managed(gateway, _row("web", self=True))
    with pytest.raises(services.SelfActionBlocked):
        services.start_managed(gateway, _row("web", self=True))
    with pytest.raises(services.SelfActionBlocked):
        services.restart_managed(gateway, _row("web", self=True))
    with pytest.raises(services.SelfActionBlocked):
        services.remove_managed(gateway, _row("web", self=True), confirmed=True)
    assert gateway.calls == []


def test_remove_requires_confirmation() -> None:
    gateway = FakeManagedGateway([_row("web")])
    with pytest.raises(ContainerOperationError):
        services.remove_managed(gateway, _row("web"), confirmed=False)
    assert gateway.calls == []
    services.remove_managed(gateway, _row("web"), confirmed=True)
    assert gateway.calls == ["remove:id-web"]


def test_lifecycle_delegates_to_gateway() -> None:
    gateway = FakeManagedGateway([_row("web")])
    services.start_managed(gateway, _row("web"))
    services.stop_managed(gateway, _row("web"))
    services.restart_managed(gateway, _row("web"))
    assert gateway.calls == ["start:id-web", "stop:id-web", "restart:id-web"]


def test_list_degrades_to_empty_on_failure() -> None:
    gateway = FakeManagedGateway([])
    gateway.fail_list = True
    assert services.list_managed(gateway) == []


def test_fetch_logs_returns_lines() -> None:
    assert services.fetch_logs(FakeManagedGateway([]), _row("web")) == ["line-1", "line-2"]


def test_build_managed_maps_native_object() -> None:
    native = SimpleNamespace(
        id="abc123",
        name="/my-app",
        image=SimpleNamespace(tags=["repo/app:2"], short_id="sha256:x"),
        status="running",
    )
    row = build_managed(native)
    assert (row.container_id, row.name, row.image_ref) == ("abc123", "my-app", "repo/app:2")
    assert row.state_bucket is ContainerStateBucket.RUNNING
    assert row.exact_status == "running"


def test_build_managed_falls_back_without_tags() -> None:
    native = SimpleNamespace(
        id="abc123", name="x", image=SimpleNamespace(tags=[], short_id="sha256:x"), status="paused"
    )
    row = build_managed(native)
    assert row.image_ref == "sha256:x"
    assert row.state_bucket is ContainerStateBucket.OTHER


def _api_error(status_code: int) -> APIError:
    response = SimpleNamespace(status_code=status_code)
    return APIError("engine refused", response=response, explanation="refused")


def test_operation_error_maps_conflict_and_missing() -> None:
    conflict = _operation_error("remove", "db", _api_error(409))
    assert "Stop the container first" in str(conflict)
    missing = _operation_error("inspect", "db", _api_error(404))
    assert "not found" in str(missing)


def test_operation_error_maps_permission() -> None:
    err = _operation_error("stop", "db", OSError("permission denied on socket"))
    assert "permission was denied" in str(err)


def test_not_running_in_container_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DECK_CONTAINER", raising=False)
    monkeypatch.setattr(services.os.path, "exists", lambda _: False)
    assert services.is_running_in_container() is False
