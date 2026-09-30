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


class ContainerStateBucket(StrEnum):
    """List grouping for Engine statuses. `other` never hides the exact status."""

    RUNNING = "running"
    STOPPED = "stopped"
    OTHER = "other"


def bucket_for_status(status: str) -> ContainerStateBucket:
    """Map a verbatim Engine status to its list bucket."""
    normalized = status.strip().lower()
    if normalized in ("running", "restarting"):
        return ContainerStateBucket.RUNNING
    if normalized in ("exited", "created", "dead", "removing", "removal"):
        return ContainerStateBucket.STOPPED
    if normalized in ("paused",):
        return ContainerStateBucket.OTHER
    return ContainerStateBucket.OTHER


@dataclass(frozen=True)
class ManagedContainer:
    """One sibling container row. `exact_status` is verbatim Engine status."""

    container_id: str
    name: str
    image_ref: str
    state_bucket: ContainerStateBucket
    exact_status: str
    is_self: bool = False

    def __post_init__(self) -> None:
        if not self.container_id:
            raise ValueError("container_id must be a non-empty string")
        if not self.name:
            raise ValueError("name must be a non-empty string")
        if not self.image_ref:
            raise ValueError("image_ref must be a non-empty string")


@dataclass(frozen=True)
class ContainerLogView:
    """Bounded tail of log lines for one container."""

    container_id: str
    lines: tuple[str, ...]
    fetched_at: datetime

    def __post_init__(self) -> None:
        if not self.container_id:
            raise ValueError("container_id must be a non-empty string")
        if len(self.lines) > 1000:
            raise ValueError("lines must be a bounded tail (<=1000)")


class ContainerOperationError(Exception):
    """Actionable container-operation failure (what/which/likely-why/next)."""

    def __init__(self, operation: str, container: str, reason: str, next_step: str) -> None:
        super().__init__(f"{operation} failed for container '{container}': {reason} {next_step}")
        self.operation = operation
        self.container = container
        self.reason = reason
        self.next_step = next_step


class DockerGateway(Protocol):
    """Thin connectivity seam owned by the application."""

    @property
    def endpoint(self) -> str:
        """Human-readable label of the probed endpoint (never a secret)."""
        ...

    def get_snapshot(self) -> DockerSnapshot:
        """Probe the Engine once and return a frozen snapshot."""
        ...

    def list_containers(self) -> list[ManagedContainer]:
        """List all sibling containers once (empty when unreachable)."""
        ...

    def get_container(self, container_id: str) -> ManagedContainer:
        """Return one container row; raises ContainerOperationError when missing."""
        ...

    def container_logs(self, container_id: str, tail: int = 200) -> ContainerLogView:
        """Return a bounded tail of log lines; raises ContainerOperationError."""
        ...

    def start_container(self, container_id: str) -> ManagedContainer:
        """Start a container; returns the refreshed row."""
        ...

    def stop_container(self, container_id: str) -> ManagedContainer:
        """Stop a container gracefully; returns the refreshed row."""
        ...

    def restart_container(self, container_id: str) -> ManagedContainer:
        """Restart a container; returns the refreshed row."""
        ...

    def remove_container(self, container_id: str) -> None:
        """Remove a container. Callers MUST confirm first; self is blocked upstream."""
        ...
