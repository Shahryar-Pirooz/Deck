"""US2: port mapping parsing and list-field add/remove/edit behavior."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from deck import services
from deck.docker_gateway import ContainerRunError
from deck.tui.widgets import ListField

# ----------------------------------------------------------------------
# Port mapping validation (FR-003)
# ----------------------------------------------------------------------


def test_parse_valid_port_mapping() -> None:
    mapping = services.parse_port_mapping("8080:80")
    assert mapping.host_port == "8080"
    assert mapping.container_port == "80"


def test_parse_port_mapping_strips_whitespace() -> None:
    mapping = services.parse_port_mapping("  8080:80  ")
    assert mapping.host_port == "8080"
    assert mapping.container_port == "80"


def test_parse_port_mapping_with_ip_prefix() -> None:
    mapping = services.parse_port_mapping("127.0.0.1:8080:80")
    assert mapping.host_port == "127.0.0.1:8080"
    assert mapping.container_port == "80"


def test_parse_invalid_port_mapping_rejected() -> None:
    with pytest.raises(ContainerRunError) as excinfo:
        services.parse_port_mapping("abc:80")
    assert excinfo.value.code == "InvalidPortFormat"
    assert "abc:80" in excinfo.value.message


def test_parse_port_mapping_missing_colon_rejected() -> None:
    with pytest.raises(ContainerRunError) as excinfo:
        services.parse_port_mapping("8080")
    assert excinfo.value.code == "InvalidPortFormat"


def test_parse_port_mapping_non_numeric_container_rejected() -> None:
    with pytest.raises(ContainerRunError) as excinfo:
        services.parse_port_mapping("8080:http")
    assert excinfo.value.code == "InvalidPortFormat"


# ----------------------------------------------------------------------
# ListField keyboard behavior (FR-010)
# ----------------------------------------------------------------------


class ListFieldApp(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.field = ListField(
            "Ports",
            "8080:80",
            "ports-field",
            parser=services.parse_port_mapping,
        )

    def compose(self) -> ComposeResult:
        yield self.field


async def test_list_field_add_entry_via_input() -> None:
    app = ListFieldApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.field.action_add_entry()
        await pilot.pause()
        await pilot.press(*list("8080:80"))
        await pilot.press("enter")
        await pilot.pause()
        assert app.field.values() == ["8080:80"]


async def test_list_field_rejects_invalid_entry() -> None:
    app = ListFieldApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.field.action_add_entry()
        await pilot.pause()
        await pilot.press(*list("abc:80"))
        await pilot.press("enter")
        await pilot.pause()
        assert app.field.values() == []


async def test_list_field_remove_selected_entry() -> None:
    app = ListFieldApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.field._items.extend(["8080:80", "9090:90"])
        app.field._refresh()
        app.field.focus()
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        assert app.field.values() == ["9090:90"]


async def test_list_field_j_k_moves_selection_and_edit_loads_input() -> None:
    app = ListFieldApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.field._items.extend(["8080:80", "9090:90"])
        app.field._selected = 0
        app.field._refresh()
        app.field.focus()
        await pilot.pause()
        await pilot.press("j")
        await pilot.pause()
        assert app.field._selected == 1
        await pilot.press("e")
        await pilot.pause()
        assert app.field.values() == ["8080:80"]
        assert app.query_one("#ports-field-input").value == "9090:90"
