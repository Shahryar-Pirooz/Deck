"""Number-key routing and modal isolation for the resource sidebar."""

from datetime import UTC, datetime

from deck.docker_gateway import ConnectionState, DockerGateway, DockerSnapshot, ResourceType
from deck.tui.app import DeckApp
from deck.tui.screens import HelpScreen


class FakeGateway(DockerGateway):
    @property
    def endpoint(self) -> str:
        return "fake://local"

    def get_snapshot(self) -> DockerSnapshot:
        return DockerSnapshot(
            state=ConnectionState.CONNECTED,
            summary=None,
            detail="Connected to Docker fake.",
            endpoint=self.endpoint,
            probed_at=datetime.now(UTC),
        )


def test_number_mapping_is_fixed() -> None:
    app = DeckApp(FakeGateway())
    assert [
        ResourceType.CONTAINERS,
        ResourceType.IMAGES,
        ResourceType.VOLUMES,
        ResourceType.NETWORKS,
    ] == list(ResourceType)
    assert app.current_resource_type is ResourceType.CONTAINERS


async def test_number_keys_are_ignored_while_help_is_open() -> None:
    app = DeckApp(FakeGateway())
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("question_mark")
        await pilot.pause()
        assert isinstance(app.screen, HelpScreen)
        await pilot.press("2")
        await pilot.pause()
        assert app.current_resource_type is ResourceType.CONTAINERS
