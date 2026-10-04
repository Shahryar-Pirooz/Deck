"""Application services over the DockerGateway protocol.

Services are synchronous and blocking by design — callers (the Textual worker)
are responsible for running them off the render loop.
"""

from __future__ import annotations

import logging
import os
import socket
from dataclasses import replace

from deck.docker_gateway import (
    ContainerOperationError,
    DockerGateway,
    DockerSnapshot,
    ManagedContainer,
    ManagedImage,
    ManagedNetwork,
    ManagedVolume,
    ResourceType,
)

log = logging.getLogger(__name__)


class SelfActionBlocked(Exception):
    """Raised when an action targets the manager's own container."""


def is_running_in_container() -> bool:
    """Best-effort detection of running inside a container."""
    if os.environ.get("DECK_CONTAINER") == "1":
        return True
    try:
        return os.path.exists("/.dockerenv")
    except OSError:
        return False


def mark_self(containers: list[ManagedContainer]) -> list[ManagedContainer]:
    """Flag the manager's own row by matching visible identity. Best-effort."""
    try:
        hostname = socket.gethostname().strip()
    except OSError:
        hostname = ""
    if not hostname:
        return list(containers)
    marked: list[ManagedContainer] = []
    for container in containers:
        name = container.name.lstrip("/")
        is_self = (
            container.container_id == hostname
            or container.container_id.startswith(hostname)
            or name == hostname
        )
        marked.append(
            replace(container, is_self=True) if is_self and not container.is_self else container
        )
    return marked


def list_managed(gateway: DockerGateway) -> list[ManagedContainer]:
    """List sibling containers; empty when the Engine is unreachable."""
    log.info("Listing containers via: %s", gateway.endpoint)
    try:
        containers = gateway.list_containers()
    except ContainerOperationError as exc:
        log.info("Container listing unavailable: %s", exc)
        return []
    except Exception as exc:  # noqa: BLE001 - degraded list, status screen explains
        log.debug("Container listing failed: %r", exc)
        return []
    return mark_self(containers)


def list_managed_images(gateway: DockerGateway) -> list[ManagedImage]:
    """List images; empty when the Engine is unreachable."""
    log.info("Listing images via: %s", gateway.endpoint)
    try:
        images = gateway.list_images()
    except ContainerOperationError as exc:
        log.info("Image listing unavailable: %s", exc)
        return []
    except Exception as exc:  # noqa: BLE001 - degraded list
        log.debug("Image listing failed: %r", exc)
        return []
    return images


def list_managed_volumes(gateway: DockerGateway) -> list[ManagedVolume]:
    """List volumes; empty when the Engine is unreachable."""
    log.info("Listing volumes via: %s", gateway.endpoint)
    try:
        volumes = gateway.list_volumes()
    except ContainerOperationError as exc:
        log.info("Volume listing unavailable: %s", exc)
        return []
    except Exception as exc:  # noqa: BLE001 - degraded list
        log.debug("Volume listing failed: %r", exc)
        return []
    return volumes


def list_managed_networks(gateway: DockerGateway) -> list[ManagedNetwork]:
    """List networks; empty when the Engine is unreachable."""
    log.info("Listing networks via: %s", gateway.endpoint)
    try:
        networks = gateway.list_networks()
    except ContainerOperationError as exc:
        log.info("Network listing unavailable: %s", exc)
        return []
    except Exception as exc:  # noqa: BLE001 - degraded list
        log.debug("Network listing failed: %r", exc)
        return []
    return networks


def ensure_not_self(container: ManagedContainer, operation: str) -> None:
    """Block stop/restart/remove against the manager's own container."""
    if container.is_self:
        raise SelfActionBlocked(
            f"Refusing to {operation} container '{container.name}': "
            "this is the manager's own container. Act on it from outside the tool."
        )


def start_managed(gateway: DockerGateway, container: ManagedContainer) -> ManagedContainer:
    """Start a sibling container (self is blocked)."""
    ensure_not_self(container, "start")
    log.info("Starting container '%s'", container.name)
    return gateway.start_container(container.container_id)


def stop_managed(gateway: DockerGateway, container: ManagedContainer) -> ManagedContainer:
    """Stop a sibling container gracefully (self is blocked)."""
    ensure_not_self(container, "stop")
    log.info("Stopping container '%s'", container.name)
    return gateway.stop_container(container.container_id)


def restart_managed(gateway: DockerGateway, container: ManagedContainer) -> ManagedContainer:
    """Restart a sibling container (self is blocked)."""
    ensure_not_self(container, "restart")
    log.info("Restarting container '%s'", container.name)
    return gateway.restart_container(container.container_id)


def remove_managed(gateway: DockerGateway, container: ManagedContainer, confirmed: bool) -> None:
    """Remove a sibling container. Requires explicit confirmation; self is blocked."""
    ensure_not_self(container, "remove")
    if not confirmed:
        raise ContainerOperationError(
            "remove",
            container.name,
            "removal was not confirmed.",
            "Confirm removal first.",
        )
    log.info("Removing container '%s'", container.name)
    gateway.remove_container(container.container_id)


def fetch_logs(gateway: DockerGateway, container: ManagedContainer, tail: int = 200) -> list[str]:
    """Fetch a bounded tail of log lines for one container."""
    log.info("Fetching logs for container '%s'", container.name)
    return list(gateway.container_logs(container.container_id, tail=tail).lines)


def refresh_snapshot(gateway: DockerGateway) -> DockerSnapshot:
    """Probe the Engine once through the gateway and log the outcome."""
    log.info("Probing Docker endpoint: %s", gateway.endpoint)
    snapshot = gateway.get_snapshot()
    log.info("Docker probe result: %s", snapshot.state.value)
    log.debug("Docker probe detail: %s", snapshot.detail)
    return snapshot
