"""Concrete Docker Engine adapter.

This is the ONLY module allowed to import the ``docker`` package. All SDK
details — client construction, API calls, exception taxonomy — are mapped
here to :mod:`deck.docker_gateway` types so the TUI and services never
see SDK exceptions.
"""

from __future__ import annotations

import errno
import logging
import os
from datetime import UTC, datetime
from types import TracebackType
from typing import Any

import docker
from docker.errors import APIError, DockerException, NotFound

from deck.config import DEFAULT_ENDPOINT
from deck.docker_gateway import (
    ConnectionState,
    ContainerLogView,
    ContainerOperationError,
    DockerGateway,
    DockerSnapshot,
    DockerSystemSummary,
    ManagedContainer,
    ManagedImage,
    ManagedNetwork,
    ManagedVolume,
    ResourceType,
    bucket_for_status,
)

log = logging.getLogger(__name__)

_MISSING_SOCKET_HINT = "Check that Docker is running."
_PERMISSION_HINT = (
    "Check that the current user has permission to access the Docker socket "
    "(e.g. membership in the docker group)."
)


def _chain_messages(exc: BaseException) -> str:
    """Collect messages from the exception and its causes for classification."""
    parts: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        parts.append(str(current))
        current = current.__cause__ or current.__context__
    return " | ".join(part for part in parts if part)


def _chain_errnos(exc: BaseException) -> set[int | None]:
    """Collect errno values from OSError entries in the exception chain."""
    errnos: set[int | None] = set()
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, OSError):
            errnos.add(current.errno)
        current = current.__cause__ or current.__context__
    return errnos


def classify_error(exc: BaseException) -> tuple[ConnectionState, str]:
    """Map any probe failure to a connection state plus user guidance."""
    chained = _chain_messages(exc).lower()
    errnos = _chain_errnos(exc)

    if errno.EACCES in errnos or "permission denied" in chained:
        return (
            ConnectionState.PERMISSION_DENIED,
            f"Permission denied accessing the Docker Engine. {_PERMISSION_HINT}",
        )
    if (
        errno.ENOENT in errnos
        or "no such file" in chained
        or "error while fetching server api version" in chained
        and ("not found" in chained or "no such" in chained)
    ):
        return (
            ConnectionState.UNAVAILABLE,
            f"Cannot connect to the Docker Engine. {_MISSING_SOCKET_HINT}",
        )
    if isinstance(exc, FileNotFoundError):
        return (
            ConnectionState.UNAVAILABLE,
            f"Cannot connect to the Docker Engine. {_MISSING_SOCKET_HINT}",
        )
    return (
        ConnectionState.CONNECTION_FAILED,
        "Connection to the Docker Engine failed. "
        "Check that Docker is running and reachable, then press r to retry.",
    )


def build_summary(version_data: dict[str, Any], info_data: dict[str, Any]) -> DockerSystemSummary:
    """Translate raw ``version()``/``info()`` payloads to a validated summary."""
    total = int(info_data.get("Containers", 0))
    running = int(info_data.get("ContainersRunning", 0))
    stopped = int(info_data.get("ContainersStopped", max(total - running, 0)))
    return DockerSystemSummary(
        version=str(version_data.get("Version", "unknown")),
        api_version=(str(version_data["ApiVersion"]) if version_data.get("ApiVersion") else None),
        os=str(version_data.get("Os", "unknown")),
        architecture=str(version_data.get("Arch", "unknown")),
        containers_total=total,
        containers_running=running,
        containers_stopped=stopped,
        images=int(info_data.get("Images", 0)),
    )


def _container_image_ref(native: Any) -> str:
    """Image reference for a container row without extra Engine calls.

    ``native.image`` performs an API request per container and raises
    ``ImageNotFound`` when the image was removed or retagged, which used to
    make the whole list come back empty. Prefer the reference already present
    in the list payload and only then fall back to the image object.
    """
    attrs = getattr(native, "attrs", None)
    if isinstance(attrs, dict):
        ref = attrs.get("Image")
        if isinstance(ref, str) and ref:
            return ref[:19] if ref.startswith("sha256:") else ref
    try:
        image = getattr(native, "image", None)
        tags = getattr(image, "tags", None) or []
        if tags:
            return str(tags[0])
        short_id = getattr(image, "short_id", None)
        if short_id:
            return str(short_id)
    except Exception:  # noqa: BLE001 - image removed/untagged; keep the row
        pass
    return "unknown"


def _format_created(value: Any) -> str:
    """Render an Engine ``Created`` value (epoch int or ISO string)."""
    if isinstance(value, bool):
        return "unknown"
    if isinstance(value, (int, float)) and value > 0:
        return datetime.fromtimestamp(value, UTC).strftime("%Y-%m-%d %H:%M")
    if isinstance(value, str) and value:
        return value[:16].replace("T", " ")
    return "unknown"


def _native_attr(native: Any, name: str, key: str) -> str:
    """Read a property, falling back to the raw Engine ``attrs`` payload.

    SDK ``Volume``/``Network`` objects expose only ``name``/``id``; fields such
    as driver, mountpoint and scope live in ``attrs``.
    """
    value = getattr(native, name, None)
    if value:
        return str(value)
    attrs = getattr(native, "attrs", None)
    if isinstance(attrs, dict) and attrs.get(key):
        return str(attrs[key])
    return "unknown"


def build_managed(native: Any) -> ManagedContainer:
    """Translate one SDK container object to a validated row."""
    container_id = str(getattr(native, "id", "") or "")
    raw_name = str(getattr(native, "name", "") or "unknown")
    image_ref = _container_image_ref(native)
    status = str(getattr(native, "status", "unknown") or "unknown")
    return ManagedContainer(
        container_id=container_id,
        name=raw_name.lstrip("/") or "unknown",
        image_ref=image_ref,
        state_bucket=bucket_for_status(status),
        exact_status=status,
    )


def build_managed_image(native: Any) -> ManagedImage:
    """Translate one SDK image object to a validated row."""
    image_id = str(getattr(native, "id", "") or "")
    tags = getattr(native, "tags", None) or []
    repository_tag = str(tags[0] if tags else (getattr(native, "short_id", "") or "unknown") or "unknown")
    attrs = getattr(native, "attrs", None)
    if not isinstance(attrs, dict):
        attrs = {}
    created_attr = getattr(native, "created", None)
    created = str(created_attr) if created_attr else _format_created(attrs.get("Created"))
    size_bytes = int(attrs.get("Size", 0)) if isinstance(attrs.get("Size"), (int, float)) else 0
    return ManagedImage(image_id=image_id, repository_tag=repository_tag, size_bytes=size_bytes, created=created)


def build_managed_volume(native: Any) -> ManagedVolume:
    """Translate one SDK volume object to a validated row."""
    name = str(getattr(native, "name", "") or "unknown")
    driver = _native_attr(native, "driver", "Driver")
    mountpoint = _native_attr(native, "mountpoint", "Mountpoint")
    return ManagedVolume(name=name, driver=driver, mountpoint=mountpoint)


def build_managed_network(native: Any) -> ManagedNetwork:
    """Translate one SDK network object to a validated row."""
    network_id = str(getattr(native, "id", "") or "")
    name = str(getattr(native, "name", "") or "unknown")
    driver = _native_attr(native, "driver", "Driver")
    scope = _native_attr(native, "scope", "Scope")
    return ManagedNetwork(network_id=network_id, name=name, driver=driver, scope=scope)


def _operation_error(operation: str, container: str, exc: BaseException) -> ContainerOperationError:
    """Map an SDK failure to an actionable operation error."""
    if isinstance(exc, APIError):
        code = exc.status_code
        if code == 404 or isinstance(exc, NotFound):
            return ContainerOperationError(
                operation, container, "it was not found.", "Press r to refresh the list."
            )
        if code == 409:
            return ContainerOperationError(
                operation,
                container,
                "the Engine refused it (often: removing a running container).",
                "Stop the container first, then retry.",
            )
    chained = _chain_messages(exc).lower()
    if "permission denied" in chained or "permission" in chained:
        return ContainerOperationError(
            operation,
            container,
            "permission was denied.",
            "Check Engine access, then press r to retry.",
        )
    return ContainerOperationError(
        operation,
        container,
        "the Engine reported a failure.",
        "Press r to refresh and retry.",
    )


class SdkGateway(DockerGateway):
    """Local-Engine gateway backed by the official Docker SDK."""

    def __init__(self, endpoint: str = DEFAULT_ENDPOINT, timeout: int = 5) -> None:
        self._endpoint = endpoint or DEFAULT_ENDPOINT
        self._timeout = timeout

    @property
    def endpoint(self) -> str:
        return self._endpoint

    def _make_client(self) -> docker.DockerClient:
        # Honor the standard socket/env but never follow a remote CLI context:
        # this release is local-only, so force the default context behavior
        # (docker>=7.2 supports use_context).
        if self._endpoint != DEFAULT_ENDPOINT and "DOCKER_HOST" not in os.environ:
            return docker.DockerClient(base_url=self._endpoint, timeout=self._timeout)
        try:
            return docker.from_env(timeout=self._timeout, use_context=False)
        except TypeError:
            # Older docker SDK releases do not accept ``use_context``.
            return docker.from_env(timeout=self._timeout)

    def get_snapshot(self) -> DockerSnapshot:
        probed_at = datetime.now(UTC)
        try:
            client = self._make_client()
        except Exception as exc:  # noqa: BLE001 - mapped to a state below
            state, detail = classify_error(exc)
            log.debug("Docker client creation failed: %r", exc)
            return DockerSnapshot(
                state=state,
                summary=None,
                detail=detail,
                endpoint=self._endpoint,
                probed_at=probed_at,
            )
        try:
            client.ping()
            version_data: dict[str, Any] = client.version()
            info_data: dict[str, Any] = client.info()
        except (DockerException, APIError, OSError) as exc:
            state, detail = classify_error(exc)
            log.debug("Docker probe failed: %r", exc)
            return DockerSnapshot(
                state=state,
                summary=None,
                detail=detail,
                endpoint=self._endpoint,
                probed_at=probed_at,
            )
        except Exception as exc:  # noqa: BLE001 - never leak SDK internals
            log.debug("Unexpected Docker probe failure: %r", exc)
            return DockerSnapshot(
                state=ConnectionState.CONNECTION_FAILED,
                summary=None,
                detail=(
                    "Connection to the Docker Engine failed. "
                    "Check that Docker is running and reachable, then press r to retry."
                ),
                endpoint=self._endpoint,
                probed_at=probed_at,
            )
        finally:
            try:
                client.close()
            except Exception:  # noqa: BLE001, S110 - best-effort cleanup
                pass
        try:
            summary = build_summary(version_data, info_data)
        except (ValueError, KeyError, TypeError) as exc:
            log.debug("Docker payload parsing failed: %r", exc)
            return DockerSnapshot(
                state=ConnectionState.CONNECTION_FAILED,
                summary=None,
                detail="Docker responded with unexpected data. Press r to retry.",
                endpoint=self._endpoint,
                probed_at=probed_at,
            )
        return DockerSnapshot(
            state=ConnectionState.CONNECTED,
            summary=summary,
            detail=f"Connected to Docker {summary.version}.",
            endpoint=self._endpoint,
            probed_at=probed_at,
        )

    def _container_client(self) -> docker.DockerClient:
        return self._make_client()

    def list_containers(self) -> list[ManagedContainer]:
        try:
            client = self._container_client()
        except Exception as exc:  # noqa: BLE001 - degraded list, status explains
            log.debug("Container listing client failed: %r", exc)
            return []
        try:
            natives = client.containers.list(all=True, limit=200)
        except Exception as exc:  # noqa: BLE001 - degraded list
            log.debug("Container listing query failed: %r", exc)
            return []
        finally:
            try:
                client.close()
            except Exception:  # noqa: BLE001, S110 - best-effort cleanup
                pass
        rows: list[ManagedContainer] = []
        for native in natives:
            try:
                rows.append(build_managed(native))
            except (ValueError, TypeError, AttributeError) as exc:
                log.debug("Skipping unparsable container row: %r", exc)
        return rows

    def _get_container(self, client: docker.DockerClient, container_id: str, operation: str) -> Any:
        try:
            return client.containers.get(container_id)
        except Exception as exc:  # noqa: BLE001 - mapped below
            raise _operation_error(operation, container_id, exc) from exc

    def get_container(self, container_id: str) -> ManagedContainer:
        try:
            client = self._container_client()
        except Exception as exc:  # noqa: BLE001 - mapped below
            raise _operation_error("inspect", container_id, exc) from exc
        try:
            return build_managed(self._get_container(client, container_id, "inspect"))
        finally:
            try:
                client.close()
            except Exception:  # noqa: BLE001, S110 - best-effort cleanup
                pass

    def container_logs(self, container_id: str, tail: int = 200) -> ContainerLogView:
        bounded = max(1, min(tail, 1000))
        try:
            client = self._container_client()
        except Exception as exc:  # noqa: BLE001 - mapped below
            raise _operation_error("logs", container_id, exc) from exc
        try:
            native = self._get_container(client, container_id, "logs")
            try:
                raw = native.logs(tail=bounded)
            except Exception as exc:  # noqa: BLE001 - mapped below
                raise _operation_error("logs", container_id, exc) from exc
            if isinstance(raw, bytes):
                text = raw.decode("utf-8", errors="replace")
            else:
                text = str(raw)
            return ContainerLogView(
                container_id=container_id,
                lines=tuple(text.splitlines()[-bounded:]),
                fetched_at=datetime.now(UTC),
            )
        finally:
            try:
                client.close()
            except Exception:  # noqa: BLE001, S110 - best-effort cleanup
                pass

    def _act(self, container_id: str, operation: str, action: str) -> ManagedContainer:
        try:
            client = self._container_client()
        except Exception as exc:  # noqa: BLE001 - mapped below
            raise _operation_error(operation, container_id, exc) from exc
        try:
            native = self._get_container(client, container_id, operation)
            name = str(getattr(native, "name", container_id))
            try:
                if action == "start":
                    native.start()
                elif action == "stop":
                    native.stop(timeout=10)
                elif action == "restart":
                    native.restart(timeout=10)
                else:  # pragma: no cover - guarded by callers
                    raise ValueError(f"unknown action: {action}")
            except ContainerOperationError:
                raise
            except Exception as exc:  # noqa: BLE001 - mapped below
                raise _operation_error(operation, name, exc) from exc
            try:
                native.reload()
            except Exception:  # noqa: BLE001 - stale row still better than failure
                log.debug("Container reload failed after %s; using cached row", operation)
            return build_managed(native)
        finally:
            try:
                client.close()
            except Exception:  # noqa: BLE001, S110 - best-effort cleanup
                pass

    def start_container(self, container_id: str) -> ManagedContainer:
        return self._act(container_id, "start", "start")

    def stop_container(self, container_id: str) -> ManagedContainer:
        return self._act(container_id, "stop", "stop")

    def restart_container(self, container_id: str) -> ManagedContainer:
        return self._act(container_id, "restart", "restart")

    def remove_container(self, container_id: str) -> None:
        try:
            client = self._container_client()
        except Exception as exc:  # noqa: BLE001 - mapped below
            raise _operation_error("remove", container_id, exc) from exc
        try:
            native = self._get_container(client, container_id, "remove")
            name = str(getattr(native, "name", container_id))
            try:
                native.remove()
            except Exception as exc:  # noqa: BLE001 - mapped below
                raise _operation_error("remove", name, exc) from exc
        finally:
            try:
                client.close()
            except Exception:  # noqa: BLE001, S110 - best-effort cleanup
                pass

    def list_images(self) -> list[ManagedImage]:
        try:
            client = self._container_client()
        except Exception as exc:  # noqa: BLE001 - degraded list, status explains
            log.debug("Image listing client failed: %r", exc)
            return []
        try:
            natives = client.images.list(all=True)
        except Exception as exc:  # noqa: BLE001 - degraded list
            log.debug("Image listing query failed: %r", exc)
            return []
        finally:
            try:
                client.close()
            except Exception:  # noqa: BLE001, S110 - best-effort cleanup
                pass
        rows: list[ManagedImage] = []
        for native in natives:
            try:
                rows.append(build_managed_image(native))
            except (ValueError, TypeError, AttributeError) as exc:
                log.debug("Skipping unparsable image row: %r", exc)
        return rows

    def list_volumes(self) -> list[ManagedVolume]:
        try:
            client = self._container_client()
        except Exception as exc:  # noqa: BLE001 - degraded list, status explains
            log.debug("Volume listing client failed: %r", exc)
            return []
        try:
            natives = client.volumes.list()
        except Exception as exc:  # noqa: BLE001 - degraded list
            log.debug("Volume listing query failed: %r", exc)
            return []
        finally:
            try:
                client.close()
            except Exception:  # noqa: BLE001, S110 - best-effort cleanup
                pass
        rows: list[ManagedVolume] = []
        for native in natives:
            try:
                rows.append(build_managed_volume(native))
            except (ValueError, TypeError, AttributeError) as exc:
                log.debug("Skipping unparsable volume row: %r", exc)
        return rows

    def list_networks(self) -> list[ManagedNetwork]:
        try:
            client = self._container_client()
        except Exception as exc:  # noqa: BLE001 - degraded list, status explains
            log.debug("Network listing client failed: %r", exc)
            return []
        try:
            natives = client.networks.list()
        except Exception as exc:  # noqa: BLE001 - degraded list
            log.debug("Network listing query failed: %r", exc)
            return []
        finally:
            try:
                client.close()
            except Exception:  # noqa: BLE001, S110 - best-effort cleanup
                pass
        rows: list[ManagedNetwork] = []
        for native in natives:
            try:
                rows.append(build_managed_network(native))
            except (ValueError, TypeError, AttributeError) as exc:
                log.debug("Skipping unparsable network row: %r", exc)
        return rows

    def __enter__(self) -> SdkGateway:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None
