"""US4: network selection — default bridge, pass-through, unknown rejection."""

from __future__ import annotations

import pytest
from run_fakes import RunFakeGateway

from deck import services
from deck.config import ApplicationConfiguration
from deck.docker_gateway import ContainerRunError, ContainerRunRequest
from deck.tui.app import DeckApp
from deck.tui.run_config import RunConfigScreen


def test_empty_network_means_default_bridge() -> None:
    gateway = RunFakeGateway()
    assert services.validate_network(gateway, None) is None
    assert services.validate_network(gateway, "") is None
    assert services.validate_network(gateway, "   ") is None


def test_known_network_passes_through() -> None:
    gateway = RunFakeGateway()
    assert services.validate_network(gateway, "app-net") == "app-net"
    assert services.validate_network(gateway, " bridge ") == "bridge"


def test_unknown_network_rejected_with_actionable_error() -> None:
    gateway = RunFakeGateway()
    with pytest.raises(ContainerRunError) as excinfo:
        services.validate_network(gateway, "no-such-net")
    assert excinfo.value.code == "NetworkNotFound"
    assert "no-such-net" in excinfo.value.message
    assert "default bridge" in excinfo.value.suggestion


def test_run_managed_rejects_unknown_network_before_create() -> None:
    gateway = RunFakeGateway()
    request = ContainerRunRequest(image="nginx:latest", name="net-test", network="ghost")
    with pytest.raises(ContainerRunError) as excinfo:
        services.run_managed(gateway, request)
    assert excinfo.value.code == "NetworkNotFound"
    assert gateway.run_requests == []


async def test_network_field_reaches_gateway() -> None:
    gateway = RunFakeGateway()
    app = DeckApp(gateway=gateway, config=ApplicationConfiguration())
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        await pilot.press("2")
        await pilot.pause()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, RunConfigScreen)

        name_input = screen.query_one("#run-name")
        name_input.focus()
        await pilot.pause()
        await pilot.press(*list("net-app"))

        network_input = screen.query_one("#run-network")
        network_input.focus()
        await pilot.pause()
        await pilot.press(*list("app-net"))

        screen.query_one("#run-start").focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()
        await pilot.pause()
        await pilot.pause()

        assert len(gateway.run_requests) == 1
        assert gateway.run_requests[0].network == "app-net"


async def test_blank_network_uses_default_bridge() -> None:
    gateway = RunFakeGateway()
    app = DeckApp(gateway=gateway, config=ApplicationConfiguration())
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        await pilot.press("2")
        await pilot.pause()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, RunConfigScreen)

        name_input = screen.query_one("#run-name")
        name_input.focus()
        await pilot.pause()
        await pilot.press(*list("plain-app"))

        screen.query_one("#run-start").focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()
        await pilot.pause()
        await pilot.pause()

        assert len(gateway.run_requests) == 1
        assert gateway.run_requests[0].network is None
