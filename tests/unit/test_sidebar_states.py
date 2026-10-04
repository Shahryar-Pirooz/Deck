"""Selection/state behavior for the multi-resource list."""

from deck.docker_gateway import ManagedImage, ManagedVolume, ResourceType
from deck.tui.screens import ResourceListView


def test_empty_state_names_the_resource() -> None:
    view = ResourceListView()
    view.show_resource(ResourceType.IMAGES, [])
    assert "No images found." in str(view._render_resource_rows())

    view.show_resource(ResourceType.VOLUMES, [])
    assert "No volumes found." in str(view._render_resource_rows())

    view.show_resource(ResourceType.NETWORKS, [])
    assert "No networks found." in str(view._render_resource_rows())


def test_unavailable_state_is_not_rendered_as_empty() -> None:
    view = ResourceListView()
    view.show_resource(
        ResourceType.NETWORKS,
        [],
        state="unavailable",
        message="Networks unavailable.\n\nPress r to retry.",
    )
    rendered = str(view._render_resource_rows())
    assert "Networks unavailable." in rendered
    assert "No networks found." not in rendered


def test_selection_is_clamped_when_data_shrinks() -> None:
    view = ResourceListView()
    rows = [
        ManagedVolume("one", "local", "/one"),
        ManagedVolume("two", "local", "/two"),
        ManagedVolume("three", "local", "/three"),
    ]
    view.show_resource(ResourceType.VOLUMES, rows, position=2)
    assert view.position == 2
    view.show_resource(ResourceType.VOLUMES, rows[:1], position=view.position)
    assert view.position == 0


def test_resource_details_rows_are_selectable() -> None:
    view = ResourceListView()
    rows = [
        ManagedImage("sha256:one", "one:latest", 1, "today"),
        ManagedImage("sha256:two", "two:latest", 2, "today"),
    ]
    view.show_resource(ResourceType.IMAGES, rows)
    assert view.selected_resource() == rows[0]
    view.move_selection(1)
    assert view.selected_resource() == rows[1]
