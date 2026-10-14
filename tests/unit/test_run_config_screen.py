"""US1: RunConfigScreen TUI behavior (open, cancel, confirm, collision, pull)."""

from __future__ import annotations

from run_fakes import RunFakeGateway, make_image, make_running_container

from deck.config import ApplicationConfiguration
from deck.docker_gateway import (
    ContainerRunError,
)
from deck.tui.app import DeckApp
from deck.tui.run_config import RunConfigScreen, RunConfirmScreen


def _app(gateway: RunFakeGateway) -> DeckApp:
    return DeckApp(gateway=gateway, config=ApplicationConfiguration())


async def _open_run_screen(app: DeckApp, pilot) -> RunConfigScreen:  # type: ignore[no-untyped-def]
    await pilot.pause()
    await pilot.pause()
    await pilot.press("2")  # switch to Images view
    await pilot.pause()
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()
    assert isinstance(app.screen, RunConfigScreen)
    return app.screen


async def _set_name(screen: RunConfigScreen, pilot, name: str) -> None:  # type: ignore[no-untyped-def]
    name_input = screen.query_one("#run-name")
    name_input.focus()
    await pilot.pause()
    await pilot.press(*name)


async def _press_start(screen: RunConfigScreen, pilot) -> None:  # type: ignore[no-untyped-def]
    screen.query_one("#run-start").focus()
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


def _notification_messages(app: DeckApp) -> list[str]:  # type: ignore[type-arg]
    try:
        return [str(getattr(note, "message", note)) for note in list(app._notifications)]  # noqa: SLF001
    except Exception:  # noqa: BLE001 - notification buffer internals vary
        return []


async def test_enter_on_image_opens_run_screen() -> None:
    app = _app(RunFakeGateway())
    async with app.run_test() as pilot:
        screen = await _open_run_screen(app, pilot)
        assert isinstance(screen, RunConfigScreen)


async def test_screen_shows_all_five_fields() -> None:
    app = _app(RunFakeGateway())
    async with app.run_test() as pilot:
        screen = await _open_run_screen(app, pilot)
        for widget_id in ("run-name", "run-ports", "run-volumes", "run-network", "run-envs"):
            assert screen.query_one(f"#{widget_id}") is not None


async def test_escape_cancels_without_creating_container() -> None:
    gateway = RunFakeGateway()
    app = _app(gateway)
    async with app.run_test() as pilot:
        await _open_run_screen(app, pilot)
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, RunConfigScreen)
        assert gateway.run_requests == []


async def test_start_with_empty_name_shows_error_and_keeps_form_open() -> None:
    gateway = RunFakeGateway()
    app = _app(gateway)
    async with app.run_test() as pilot:
        screen = await _open_run_screen(app, pilot)
        await _press_start(screen, pilot)
        assert isinstance(app.screen, RunConfigScreen)
        assert gateway.run_requests == []
        assert "required" in screen.last_error.lower()


async def test_confirm_creates_and_starts_container() -> None:
    gateway = RunFakeGateway()
    app = _app(gateway)
    async with app.run_test() as pilot:
        screen = await _open_run_screen(app, pilot)
        await _set_name(screen, pilot, "my-web")
        await _press_start(screen, pilot)
        assert isinstance(app.screen, RunConfirmScreen)
        await pilot.press("y")
        await pilot.pause()
        await pilot.pause()
        await pilot.pause()
        assert not isinstance(app.screen, RunConfirmScreen)
        assert len(gateway.run_requests) == 1
        request = gateway.run_requests[0]
        assert request.name == "my-web"
        assert request.image == "nginx:latest"
        assert app.current_resource_type.value == "containers"
        assert any("started successfully" in message for message in _notification_messages(app))


async def test_confirm_screen_cancel_keeps_form_open() -> None:
    gateway = RunFakeGateway()
    app = _app(gateway)
    async with app.run_test() as pilot:
        screen = await _open_run_screen(app, pilot)
        await _set_name(screen, pilot, "my-web")
        await _press_start(screen, pilot)
        assert isinstance(app.screen, RunConfirmScreen)
        await pilot.press("n")
        await pilot.pause()
        assert isinstance(app.screen, RunConfigScreen)
        assert gateway.run_requests == []


async def test_name_collision_shows_error_and_suggestion() -> None:
    gateway = RunFakeGateway(containers=[make_running_container("nginx-test")])
    app = _app(gateway)
    async with app.run_test() as pilot:
        screen = await _open_run_screen(app, pilot)
        await _set_name(screen, pilot, "nginx-test")
        await _press_start(screen, pilot)
        await pilot.press("y")
        await pilot.pause()
        await pilot.pause()
        await pilot.pause()
        assert gateway.run_requests == []
        assert isinstance(app.screen, RunConfigScreen)
        assert "already exists" in screen.last_error
        assert "nginx-test-2" in screen.last_error


async def test_missing_local_image_pulls_in_background_then_runs() -> None:
    gateway = RunFakeGateway(images=[])  # nothing pulled locally
    image = make_image("busybox:latest")
    app = _app(gateway)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        app.push_screen(RunConfigScreen(image, gateway))
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, RunConfigScreen)
        await _set_name(screen, pilot, "my-pulled")
        await _press_start(screen, pilot)
        await pilot.press("y")
        await pilot.pause()
        await pilot.pause()
        await pilot.pause()
        await pilot.pause()
        assert gateway.pulled == ["busybox:latest"]
        assert len(gateway.run_requests) == 1
        assert gateway.run_requests[0].name == "my-pulled"
        assert any("pulled successfully" in message for message in _notification_messages(app))


async def test_pull_failure_shows_error_and_keeps_form_open() -> None:
    gateway = RunFakeGateway(
        images=[],
        fail_pull=ContainerRunError(
            "ImageNotFound",
            "Image 'busybox:latest' is not available locally and could not be found.",
            "Check the image name and tag, or pull it manually.",
        ),
    )
    image = make_image("busybox:latest")
    app = _app(gateway)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        app.push_screen(RunConfigScreen(image, gateway))
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, RunConfigScreen)
        await _set_name(screen, pilot, "my-pulled")
        await _press_start(screen, pilot)
        await pilot.press("y")
        await pilot.pause()
        await pilot.pause()
        await pilot.pause()
        await pilot.pause()
        assert gateway.run_requests == []
        assert isinstance(app.screen, RunConfigScreen)
        assert "not available locally" in screen.last_error
