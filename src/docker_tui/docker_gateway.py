"""App-owned Docker connectivity seam.

The TUI and services depend only on the protocol defined here. The concrete
SDK implementation lives in :mod:`docker_tui.docker_sdk`, which is the single
module allowed to import the ``docker`` package.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol


class ConnectionState(StrEnum):
    """Engine reachability. Exactly one of these four states is reported."""

    CONNECTED = "connected"
    UNAVAILABLE = "unavailable"
    PERMISSION_DENIED = "permission-denied"
    CONNECTION_FAILED = "connection-failed"


@dataclass(frozen=True)
class DockerSystemSummary:
    """Point-in-time Engine facts shown on the status screen."""

    version: str
    api_version: str | None
    os: str
    architecture: str
    containers_total: int
    containers_running: int
    containers_stopped: int
    images: int

    def __post_init__(self) -> None:
        for field_name in (
            "containers_total",
            "containers_running",
            "containers_stopped",
            "images",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative int")
        if self.containers_running + self.containers_stopped > self.containers_total:
            raise ValueError("running + stopped must not exceed total")


@dataclass(frozen=True)
class DockerSnapshot:
    """Result of one manual probe."""

    state: ConnectionState
    summary: DockerSystemSummary | None
    detail: str
    endpoint: str
    probed_at: datetime

    @classmethod
    def probing(cls, endpoint: str) -> DockerSnapshot:
        """Initial state before the first probe completes."""
        return cls(
            state=ConnectionState.UNAVAILABLE,
            summary=None,
            detail="Probing…",
            endpoint=endpoint,
            probed_at=datetime.now(UTC),
        )


class DockerGateway(Protocol):
    """Thin connectivity seam owned by the application."""

    @property
    def endpoint(self) -> str:
        """Human-readable label of the probed endpoint (never a secret)."""
        ...

    def get_snapshot(self) -> DockerSnapshot:
        """Probe the Engine once and return a frozen snapshot."""
        ...
