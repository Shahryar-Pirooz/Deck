"""Application services over the DockerGateway protocol.

Services are synchronous and blocking by design — callers (the Textual worker)
are responsible for running them off the render loop.
"""

from __future__ import annotations

import logging
import os
import re
import socket
from dataclasses import replace

from deck.docker_gateway import (
    ContainerOperationError,
    ContainerRunError,
    ContainerRunRequest,
    DockerGateway,
    DockerSnapshot,
    EnvVar,
    ManagedContainer,
    ManagedImage,
    ManagedNetwork,
    ManagedVolume,
    PortMapping,
    VolumeMount,
)

log = logging.getLogger(__name__)

_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _clean_log_line(line: str) -> str:
    """Strip ANSI escapes and control characters that would garble the TUI."""
    return _CONTROL_RE.sub("", _ANSI_RE.sub("", line))


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
    lines = gateway.container_logs(container.container_id, tail=tail).lines
    return [_clean_log_line(line) for line in lines]


def refresh_snapshot(gateway: DockerGateway) -> DockerSnapshot:
    """Probe the Engine once through the gateway and log the outcome."""
    log.info("Probing Docker endpoint: %s", gateway.endpoint)
    snapshot = gateway.get_snapshot()
    log.info("Docker probe result: %s", snapshot.state.value)
    log.debug("Docker probe detail: %s", snapshot.detail)
    return snapshot


# ----------------------------------------------------------------------
# Image Run Menu: validation, suggestions, and run/pull orchestration
# ----------------------------------------------------------------------


def validate_name(name: str) -> str:
    """Return the stripped container name; reject empty/whitespace-only names."""
    cleaned = name.strip()
    if not cleaned:
        raise ContainerRunError(
            "NameRequired",
            "Container name is required and cannot be blank.",
            "Enter a name for the container.",
        )
    return cleaned


def suggest_unique_name(existing_names: list[str], base: str) -> str:
    """Suggest ``base-2``, ``base-3``… until the name is unused."""
    taken = {existing.lstrip("/").strip() for existing in existing_names}
    candidate = base
    counter = 2
    while candidate in taken:
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def parse_port_mapping(raw: str) -> PortMapping:
    """Parse ``host_port:container_port`` (optional IP prefix on the host side)."""
    text = raw.strip()
    parts = text.split(":")
    if len(parts) == 2:
        host, container = parts
    elif len(parts) == 3:
        host, container = f"{parts[0]}:{parts[1]}", parts[2]
    else:
        host, container = "", ""
    host_number = host.split(":")[-1]
    if not host or not container or not host_number.isdigit() or not container.isdigit():
        raise ContainerRunError(
            "InvalidPortFormat",
            f"Invalid port mapping format: '{text}'. Use host_port:container_port",
            "Example: 8080:80",
        )
    return PortMapping(host_port=host, container_port=container)


def parse_volume_mount(raw: str) -> VolumeMount:
    """Parse ``source_path:container_path``."""
    text = raw.strip()
    parts = text.split(":")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise ContainerRunError(
            "InvalidVolumeFormat",
            f"Invalid volume format: '{text}'. Use source_path:container_path",
            "Example: /data:/app/data",
        )
    return VolumeMount(source_path=parts[0].strip(), container_path=parts[1].strip())


def parse_env_var(raw: str) -> EnvVar:
    """Parse ``KEY=value``."""
    text = raw.strip()
    key, sep, value = text.partition("=")
    if not sep or not key.strip():
        raise ContainerRunError(
            "InvalidEnvFormat",
            f"Invalid environment variable: '{text}'. Use KEY=value",
            "Example: DEBUG=true",
        )
    return EnvVar(key=key.strip(), value=value)


def validate_network(gateway: DockerGateway, network: str | None) -> str | None:
    """Return the network name, None for default bridge; reject unknown names."""
    if network is None:
        return None
    name = network.strip()
    if not name:
        return None
    try:
        known = [row.name for row in gateway.list_networks()]
    except Exception as exc:  # noqa: BLE001 - degraded check, let the Engine decide
        log.debug("Network availability check failed: %r", exc)
        return name
    if known and name not in known:
        raise ContainerRunError(
            "NetworkNotFound",
            f"Network '{name}' was not found.",
            "Check the network name, or leave it empty to use the default bridge.",
        )
    return name


def is_image_local(gateway: DockerGateway, image: str) -> bool:
    """True when the image reference exists among locally pulled images."""
    target = image.strip()
    if not target:
        return False
    try:
        images = gateway.list_images()
    except Exception as exc:  # noqa: BLE001 - degraded check, caller pulls
        log.debug("Image availability check failed: %r", exc)
        return False
    for row in images:
        tag = row.repository_tag
        if tag == target or tag.startswith(f"{target}:"):
            return True
    return False


def pull_image(gateway: DockerGateway, image: str) -> None:
    """Pull an image through the gateway; raises ContainerRunError on failure."""
    log.info("Pulling image '%s'", image)
    try:
        gateway.pull_image(image)
    except ContainerRunError:
        raise
    except Exception as exc:  # noqa: BLE001 - mapped to a contract code
        raise classify_run_error(exc) from exc


def classify_run_error(exc: BaseException) -> ContainerRunError:
    """Map a gateway-level failure to a contract-coded run error."""
    if isinstance(exc, ContainerRunError):
        return exc
    if isinstance(exc, ContainerOperationError):
        return ContainerRunError(
            "DaemonUnavailable",
            str(exc),
            "Check that Docker is running, then retry.",
        )
    return ContainerRunError(
        "DaemonUnavailable",
        f"Container launch failed: {exc}",
        "Check that the Docker daemon is running, then retry.",
    )


def run_managed(gateway: DockerGateway, request: ContainerRunRequest) -> str:
    """Validate the name/network, guard collisions, then create and start detached."""
    name = validate_name(request.name)
    network = validate_network(gateway, request.network)
    existing = [container.name for container in list_managed(gateway)]
    if any(existing_name.lstrip("/") == name for existing_name in existing):
        suggestion = suggest_unique_name(existing, name)
        raise ContainerRunError(
            "NameCollision",
            f"Container name '{name}' already exists.",
            f"Try '{suggestion}' instead.",
        )
    log.info("Creating and starting container '%s' from image '%s'", name, request.image)
    try:
        return gateway.create_and_run_container(replace(request, name=name, network=network))
    except ContainerRunError:
        raise
    except Exception as exc:  # noqa: BLE001 - mapped to a contract code
        raise classify_run_error(exc) from exc
