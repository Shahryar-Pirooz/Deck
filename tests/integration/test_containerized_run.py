"""US1 integration: containerized run contract; skip without a live daemon."""

from __future__ import annotations

from pathlib import Path

import pytest

from docker_tui.docker_gateway import ConnectionState, ManagedContainer
from docker_tui.docker_sdk import SdkGateway

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]


def _daemon_reachable() -> bool:
    try:
        return SdkGateway().get_snapshot().state is ConnectionState.CONNECTED
    except Exception:  # noqa: BLE001 - any failure means "no live daemon"
        return False


def test_image_definition_exists() -> None:
    """The shippable image definition is versioned and points at the entry point."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "ENTRYPOINT" in dockerfile and "Deck" in dockerfile
    assert "3.11" in dockerfile


def test_run_contract_files_exist() -> None:
    assert (REPO_ROOT / ".dockerignore").exists()


def test_live_lists_sibling_containers() -> None:
    """Host Engine exposes rows with identity, image, and bucket."""
    if not _daemon_reachable():
        pytest.skip("no live Docker daemon")
    rows: list[ManagedContainer] = SdkGateway().list_containers()
    assert isinstance(rows, list)
    for row in rows:
        assert row.name and row.container_id and row.image_ref
