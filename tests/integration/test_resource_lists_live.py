"""Live Docker coverage for image, volume, and network resource lists."""

from __future__ import annotations

import pytest

from deck.docker_gateway import ConnectionState
from deck.docker_sdk import SdkGateway

pytestmark = pytest.mark.integration


def _gateway_or_skip() -> SdkGateway:
    gateway = SdkGateway()
    try:
        if gateway.get_snapshot().state is not ConnectionState.CONNECTED:
            pytest.skip("no live Docker daemon")
    except Exception:  # noqa: BLE001
        pytest.skip("no live Docker daemon")
    return gateway


def test_images_list_live() -> None:
    gateway = _gateway_or_skip()
    assert isinstance(gateway.list_images(), list)


def test_volumes_list_live() -> None:
    gateway = _gateway_or_skip()
    assert isinstance(gateway.list_volumes(), list)


def test_networks_list_live() -> None:
    gateway = _gateway_or_skip()
    assert isinstance(gateway.list_networks(), list)
