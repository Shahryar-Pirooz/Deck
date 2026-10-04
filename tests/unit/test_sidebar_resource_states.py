"""Unit coverage for sidebar/resource presentation behavior."""

from deck.docker_gateway import ManagedImage, ManagedNetwork, ManagedVolume, ResourceType
from deck.tui.screens import ResourceListView, _format_size
from deck.tui.widgets import SidebarView


def test_sidebar_has_fixed_order() -> None:
    sidebar = SidebarView()
    assert [(entry.label, entry.type) for entry in sidebar.entries] == [
        ("1 Containers", ResourceType.CONTAINERS),
        ("2 Images", ResourceType.IMAGES),
        ("3 Volumes", ResourceType.VOLUMES),
        ("4 Networks", ResourceType.NETWORKS),
    ]
    assert sidebar.active is ResourceType.CONTAINERS
    assert sidebar.can_focus is False


def test_resource_rows_contain_required_fields() -> None:
    image = ManagedImage("sha256:abc", "nginx:latest", 1024 * 1024, "2026-10-01")
    volume = ManagedVolume("data", "local", "/var/lib/docker/volumes/data/_data")
    network = ManagedNetwork("net-id", "bridge", "bridge", "local")

    assert "nginx:latest" in ResourceListView.format_image(image)
    assert "sha256:abc" in ResourceListView.format_image(image)
    assert "1.0 MB" in ResourceListView.format_image(image)
    assert "2026-10-01" in ResourceListView.format_image(image)
    assert ResourceListView.format_volume(volume) == "data  local  /var/lib/docker/volumes/data/_data"
    assert ResourceListView.format_network(network) == "bridge  bridge  local"


def test_format_size_uses_human_readable_units() -> None:
    assert _format_size(0) == "0 B"
    assert _format_size(1024) == "1.0 KB"
    assert _format_size(1024 * 1024) == "1.0 MB"
