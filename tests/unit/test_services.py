"""US3: refresh service transitions (no live daemon)."""

from __future__ import annotations

from datetime import UTC, datetime

from deck import services
from deck.docker_gateway import (
    ConnectionState,
    DockerGateway,
    DockerSnapshot,
)


class FakeGateway(DockerGateway):
    """Canned gateway returning a scripted state sequence."""

    def __init__(self, states: list[ConnectionState]) -> None:
        self._states = states
        self.calls = 0

    @property
    def endpoint(self) -> str:
        return "fake://local"

    def get_snapshot(self) -> DockerSnapshot:
        state = self._states[min(self.calls, len(self._states) - 1)]
        self.calls += 1
        return DockerSnapshot(
            state=state,
            summary=None,
            detail=state.value,
            endpoint=self.endpoint,
            probed_at=datetime.now(UTC),
        )


def test_refresh_transitions_any_to_any() -> None:
    gateway = FakeGateway(
        [ConnectionState.UNAVAILABLE, ConnectionState.CONNECTED, ConnectionState.PERMISSION_DENIED]
    )
    assert services.refresh_snapshot(gateway).state is ConnectionState.UNAVAILABLE
    assert services.refresh_snapshot(gateway).state is ConnectionState.CONNECTED
    assert services.refresh_snapshot(gateway).state is ConnectionState.PERMISSION_DENIED
    assert gateway.calls == 3


def test_refresh_logs_without_daemon(caplog: object) -> None:
    gateway = FakeGateway([ConnectionState.CONNECTION_FAILED])
    snapshot = services.refresh_snapshot(gateway)
    assert snapshot.state is ConnectionState.CONNECTION_FAILED
