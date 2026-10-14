"""App-owned Docker connectivity seam.

The TUI and services depend only on the protocol defined here. The concrete
SDK implementation lives in :mod:`deck.docker_sdk`, which is the single
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


class ResourceType(StrEnum):
    """Resource category for the sidebar menu. Exactly one of these four is active."""

    CONTAINERS = "containers"
    IMAGES = "images"
    VOLUMES = "volumes"
    NETWORKS = "networks"


@dataclass(frozen=True)
class ManagedImage:
    """One image row from the Engine. `repository_tag` is the primary display identity."""

    image_id: str
    repository_tag: str
    size_bytes: int
    created: str

    def __post_init__(self) -> None:
        if not self.image_id:
            raise ValueError("image_id must be a non-empty string")
        if not self.repository_tag:
            raise ValueError("repository_tag must be a non-empty string")
        if not isinstance(self.size_bytes, int) or self.size_bytes < 0:
            raise ValueError("size_bytes must be a non-negative int")


@dataclass(frozen=True)
class ManagedVolume:
    """One volume row from the Engine."""

    name: str
    driver: str
    mountpoint: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must be a non-empty string")


@dataclass(frozen=True)
class ManagedNetwork:
    """One network row from the Engine."""

    network_id: str
    name: str
    driver: str
    scope: str

    def __post_init__(self) -> None:
        if not self.network_id:
            raise ValueError("network_id must be a non-empty string")
        if not self.name:
            raise ValueError("name must be a non-empty string")


@dataclass(frozen=True)
class PortMapping:
    """One host:container port pair for a container launch."""

    host_port: str
    container_port: str

    def __post_init__(self) -> None:
        if not self.host_port:
            raise ValueError("host_port must be a non-empty string")
        if not self.container_port:
            raise ValueError("container_port must be a non-empty string")


@dataclass(frozen=True)
class VolumeMount:
    """One source:destination bind mount for a container launch."""

    source_path: str
    container_path: str

    def __post_init__(self) -> None:
        if not self.source_path:
            raise ValueError("source_path must be a non-empty string")
        if not self.container_path:
            raise ValueError("container_path must be a non-empty string")


@dataclass(frozen=True)
class EnvVar:
    """One KEY=value environment entry for a container launch."""

    key: str
    value: str

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("key must be a non-empty string")


@dataclass(frozen=True)
class ContainerRunRequest:
    """Contract-shaped request for creating and starting a detached container."""

    image: str
    name: str
    ports: tuple[PortMapping, ...] = ()
    volumes: tuple[VolumeMount, ...] = ()
    network: str | None = None
    env_vars: tuple[EnvVar, ...] = ()

    def __post_init__(self) -> None:
        if not self.image:
            raise ValueError("image must be a non-empty string")
        if not self.name:
            raise ValueError("name must be a non-empty string")
        if self.network is not None and not self.network.strip():
            object.__setattr__(self, "network", None)


class ContainerRunError(Exception):
    """Container-launch failure with a contract error code and optional hint."""

    def __init__(self, code: str, message: str, suggestion: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.suggestion = suggestion

    def user_text(self) -> str:
        """Message plus suggestion for direct display in the TUI."""
        if self.suggestion:
            return f"{self.message} {self.suggestion}"
        return self.message


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

    def list_images(self) -> list[ManagedImage]:
        """List images from the Engine; empty when unreachable."""
        ...

    def list_volumes(self) -> list[ManagedVolume]:
        """List volumes from the Engine; empty when unreachable."""
        ...

    def list_networks(self) -> list[ManagedNetwork]:
        """List networks from the Engine; empty when unreachable."""
        ...

    def create_and_run_container(self, request: ContainerRunRequest) -> str:
        """Create and start a detached container; returns the new container id.

        Raises ContainerRunError with a contract error code on failure.
        """
        ...

    def pull_image(self, image: str) -> None:
        """Pull an image from the configured registry (blocking).

        Raises ContainerRunError with a contract error code on failure.
        """
        ...
