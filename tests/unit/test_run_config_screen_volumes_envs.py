"""US3: volume and env entries reach the gateway; env values shown on review."""

from __future__ import annotations

from run_fakes import RunFakeGateway

from deck.config import ApplicationConfiguration
from deck.tui.app import DeckApp
from deck.tui.run_config import RunConfigScreen, RunConfirmScreen


def _app(gateway: RunFakeGateway) -> DeckApp:
    return DeckApp(gateway=gateway, config=ApplicationConfiguration())


async def _open_screen(app: DeckApp, pilot) -> RunConfigScreen:  # type: ignore[no-untyped-def]
    await pilot.pause()
    await pilot.pause()
    await pilot.press("2")
    await pilot.pause()
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()
    screen = app.screen
    assert isinstance(screen, RunConfigScreen)
    return screen


async def test_volumes_and_envs_reach_gateway() -> None:
    gateway = RunFakeGateway()
    app = _app(gateway)
    async with app.run_test() as pilot:
        screen = await _open_screen(app, pilot)

        name_input = screen.query_one("#run-name")
        name_input.focus()
        await pilot.pause()
        await pilot.press(*list("my-data"))

        volumes_field = screen.query_one("#run-volumes")
        volumes_field.focus()
        await pilot.pause()
        volumes_field.action_add_entry()
        await pilot.pause()
        await pilot.press(*list("/home/user/data:/app/data"))
        await pilot.press("enter")
        await pilot.pause()

        envs_field = screen.query_one("#run-envs")
        envs_field.focus()
        await pilot.pause()
        envs_field.action_add_entry()
        await pilot.pause()
        await pilot.press(*list("DEBUG=true"))
        await pilot.press("enter")
        await pilot.pause()

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
        assert [(v.source_path, v.container_path) for v in request.volumes] == [
            ("/home/user/data", "/app/data")
        ]
        assert [(e.key, e.value) for e in request.env_vars] == [("DEBUG", "true")]


async def test_review_shows_env_values_before_confirm() -> None:
    gateway = RunFakeGateway()
    app = _app(gateway)
    async with app.run_test() as pilot:
        screen = await _open_screen(app, pilot)

        name_input = screen.query_one("#run-name")
        name_input.focus()
        await pilot.pause()
        await pilot.press(*list("my-app"))

        envs_field = screen.query_one("#run-envs")
        envs_field.focus()
        await pilot.pause()
        envs_field.action_add_entry()
        await pilot.pause()
        await pilot.press(*list("SECRET=hunter2"))
        await pilot.press("enter")
        await pilot.pause()

        screen.query_one("#run-start").focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        confirm = app.screen
        assert isinstance(confirm, RunConfirmScreen)
        review = confirm._review_text
        assert "SECRET=hunter2" in review
        assert "my-app" in review
        # Cancel — nothing must be created before explicit confirmation.
        await pilot.press("n")
        await pilot.pause()
        assert gateway.run_requests == []


async def test_invalid_volume_entry_rejected_in_form() -> None:
    gateway = RunFakeGateway()
    app = _app(gateway)
    async with app.run_test() as pilot:
        screen = await _open_screen(app, pilot)
        volumes_field = screen.query_one("#run-volumes")
        volumes_field.focus()
        await pilot.pause()
        volumes_field.action_add_entry()
        await pilot.pause()
        await pilot.press(*list("/data"))
        await pilot.press("enter")
        await pilot.pause()
        assert volumes_field.values() == []
        assert "source_path:container_path" in screen.last_error
