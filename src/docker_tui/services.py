"""Application services over the DockerGateway protocol.

Services are synchronous and blocking by design — callers (the Textual worker)
are responsible for running them off the render loop.
"""

from __future__ import annotations

import logging

from docker_tui.docker_gateway import DockerGateway, DockerSnapshot

log = logging.getLogger(__name__)


def refresh_snapshot(gateway: DockerGateway) -> DockerSnapshot:
    """Probe the Engine once through the gateway and log the outcome."""
    log.info("Probing Docker endpoint: %s", gateway.endpoint)
    snapshot = gateway.get_snapshot()
    log.info("Docker probe result: %s", snapshot.state.value)
    log.debug("Docker probe detail: %s", snapshot.detail)
    return snapshot
