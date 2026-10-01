"""SdkGateway container operations against a fake client (no live daemon)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from deck import services
from deck.docker_gateway import ContainerOperationError, ContainerStateBucket
from deck.docker_sdk import SdkGateway


class FakeNative:
    """Stands in for one SDK container object."""

    def __init__(self, cid: str, name: str, status: str, tags: list[str]) -> None:
        self.id = cid
        self.name = name
        self.status = status
        self.image = SimpleNamespace(tags=tags, short_id="sha256:x")
        self.calls: list[str] = []
        self.log_payload: Any = b"a\nb\nc"
        self.fail: dict[str, Exception] = {}

    def _maybe_fail(self, action: str) -> None:
        if action in self.fail:
            raise self.fail[action]

    def start(self) -> None:
        self.calls.append("start")
        self._maybe_fail("start")
        self.status = "running"

    def stop(self, timeout: int = 10) -> None:
        self.calls.append(f"stop:{timeout}")
        self._maybe_fail("stop")
        self.status = "exited"

    def restart(self, timeout: int = 10) -> None:
        self.calls.append(f"restart:{timeout}")
        self._maybe_fail("restart")
        self.status = "running"

    def remove(self) -> None:
        self.calls.append("remove")
        self._maybe_fail("remove")

    def reload(self) -> None:
        self.calls.append("reload")

    def logs(self, tail: int = 200) -> Any:
        self.calls.append(f"logs:{tail}")
        self._maybe_fail("logs")
        return self.log_payload


class FakeContainers:
    def __init__(self, natives: list[FakeNative]) -> None:
        self._natives = {native.id: native for native in natives}
        self.list_kwargs: dict[str, Any] = {}

    def list(self, **kwargs: Any) -> list[FakeNative]:
        self.list_kwargs = kwargs
        return list(self._natives.values())

    def get(self, container_id: str) -> FakeNative:
        try:
            return self._natives[container_id]
        except KeyError:
            raise _not_found() from None


def _not_found() -> Exception:
    from docker.errors import NotFound

    return NotFound("no such container")


class FakeClient:
    def __init__(self, natives: list[FakeNative]) -> None:
        self.containers = FakeContainers(natives)
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _gateway(monkeypatch: pytest.MonkeyPatch, natives: list[FakeNative]) -> SdkGateway:
    gateway = SdkGateway()
    client = FakeClient(natives)
    monkeypatch.setattr(gateway, "_make_client", lambda: client)
    monkeypatch.setattr(gateway, "_container_client", lambda: client)
    return gateway


def _native(cid: str = "abc", name: str = "web", status: str = "running") -> FakeNative:
    return FakeNative(cid, name, status, ["repo/web:1"])


def test_list_maps_rows_and_bounds_query(monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = _gateway(monkeypatch, [_native("a", "web", "running"), _native("b", "db", "exited")])
    rows = gateway.list_containers()
    assert [row.name for row in rows] == ["web", "db"]
    assert rows[0].state_bucket is ContainerStateBucket.RUNNING
    assert rows[1].state_bucket is ContainerStateBucket.STOPPED


def test_list_empty_when_client_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = SdkGateway()
    monkeypatch.setattr(gateway, "_make_client", lambda: 1 / 0)  # type: ignore[no-untyped-call]
    monkeypatch.setattr(gateway, "_container_client", gateway._make_client)
    assert gateway.list_containers() == []


def test_get_and_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = _gateway(monkeypatch, [_native()])
    row = gateway.get_container("abc")
    assert row.name == "web"
    view = gateway.container_logs("abc", tail=2)
    assert view.lines == ("b", "c")
    assert view.container_id == "abc"


def test_logs_accepts_text_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    native = _native()
    native.log_payload = "x\ny"
    gateway = _gateway(monkeypatch, [native])
    assert gateway.container_logs("abc").lines == ("x", "y")


def test_lifecycle_actions_reload_and_map(monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = _gateway(monkeypatch, [_native(status="exited")])
    assert gateway.start_container("abc").state_bucket is ContainerStateBucket.RUNNING
    assert gateway.stop_container("abc").state_bucket is ContainerStateBucket.STOPPED
    assert gateway.restart_container("abc").state_bucket is ContainerStateBucket.RUNNING


def test_remove_calls_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    native = _native()
    gateway = _gateway(monkeypatch, [native])
    gateway.remove_container("abc")
    assert "remove" in native.calls


def test_missing_container_raises_actionable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = _gateway(monkeypatch, [])
    with pytest.raises(ContainerOperationError, match="not found"):
        gateway.get_container("ghost")


def test_action_failure_maps_to_guidance(monkeypatch: pytest.MonkeyPatch) -> None:
    native = _native()
    native.fail["stop"] = _conflict()
    gateway = _gateway(monkeypatch, [native])
    with pytest.raises(ContainerOperationError, match="Stop the container first"):
        gateway.stop_container("abc")


def _conflict() -> Exception:
    from types import SimpleNamespace as NS

    from docker.errors import APIError

    return APIError("conflict", response=NS(status_code=409), explanation="conflict")


def test_list_managed_marks_self(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(services.socket, "gethostname", lambda: "abc")
    rows = services.list_managed(_gateway(monkeypatch, [_native()]))
    assert rows[0].is_self is True


def test_running_in_container_markers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DECK_CONTAINER", "1")
    assert services.is_running_in_container() is True
    monkeypatch.delenv("DECK_CONTAINER")
    monkeypatch.setattr(services.os.path, "exists", lambda _: True)
    assert services.is_running_in_container() is True
