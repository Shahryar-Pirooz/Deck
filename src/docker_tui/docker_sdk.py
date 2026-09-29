"""Concrete Docker Engine adapter.

This is the ONLY module allowed to import the ``docker`` package. All SDK
details — client construction, API calls, exception taxonomy — are mapped
here to :mod:`docker_tui.docker_gateway` types so the TUI and services never
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
from docker.errors import APIError, DockerException

from docker_tui.config import DEFAULT_ENDPOINT
from docker_tui.docker_gateway import (
    ConnectionState,
    DockerGateway,
    DockerSnapshot,
    DockerSystemSummary,
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
        return docker.from_env(timeout=self._timeout, use_context=False)

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

    def __enter__(self) -> SdkGateway:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None
