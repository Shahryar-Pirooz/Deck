"""US2: multiple port mappings reach the gateway on launch."""

from __future__ import annotations

from run_fakes import RunFakeGateway

from deck.config import ApplicationConfiguration
from deck.tui.app import DeckApp
from deck.tui.run_config import RunConfigScreen


def _app(gateway: RunFakeGateway) -> DeckApp:
    return DeckApp(gateway=gateway, config=ApplicationConfiguration())


async def test_multiple_port_mappings_reach_gateway() -> None:
    gateway = RunFakeGateway()
    app = _app(gateway)
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
        await pilot.press(*list("ports-app"))

        ports_field = screen.query_one("#run-ports")
        ports_field.focus()
        await pilot.pause()
        for raw in ("8080:80", "9090:90"):
            ports_field.action_add_entry()
            await pilot.pause()
            await pilot.press(*list(raw))
            await pilot.press("enter")
            await pilot.pause()
        assert ports_field.values() == ["8080:80", "9090:90"]

        screen.query_one("#run-start").focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()
        await pilot.pause()
        await pilot.pause()

        assert len(gateway.run_requests) == 1
        request = gateway.run_requests[0]
        assert [(p.host_port, p.container_port) for p in request.ports] == [
            ("8080", "80"),
            ("9090", "90"),
        ]


async def test_no_port_mappings_means_no_ports() -> None:
    gateway = RunFakeGateway()
    app = _app(gateway)
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
        await pilot.press(*list("bare-app"))

        screen.query_one("#run-start").focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()
        await pilot.pause()
        await pilot.pause()

        assert len(gateway.run_requests) == 1
        assert gateway.run_requests[0].ports == ()


async def test_invalid_port_entry_shown_and_not_added() -> None:
    gateway = RunFakeGateway()
    app = _app(gateway)
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

        ports_field = screen.query_one("#run-ports")
        ports_field.focus()
        await pilot.pause()
        ports_field.action_add_entry()
        await pilot.pause()
        await pilot.press(*list("abc:80"))
        await pilot.press("enter")
        await pilot.pause()
        assert ports_field.values() == []
        assert (
            "InvalidPortFormat" in screen.last_error
            or "host_port:container_port" in screen.last_error
        )
