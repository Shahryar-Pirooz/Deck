"""Unit tests for sidebar resource mapping and entry order."""

from __future__ import annotations

from deck.docker_gateway import ResourceType


def test_resource_type_order():
    """ResourceType enum order matches sidebar order."""
    # Containers first as per clarification
    expected_order = [ResourceType.CONTAINERS, ResourceType.IMAGES, ResourceType.VOLUMES, ResourceType.NETWORKS]
    actual_order = list(ResourceType)
    assert actual_order == expected_order


def test_sidebar_entry_labels():
    """Sidebar entry labels are exactly as specified."""
    # The menu labels are derived in the TUI; this test validates the ResourceType mapping
    assert ResourceType.CONTAINERS.value == "containers"
    assert ResourceType.IMAGES.value == "images"
    assert ResourceType.VOLUMES.value == "volumes"
    assert ResourceType.NETWORKS.value == "networks"