"""Shared fake gateway and helpers for Image Run Menu tests (no live daemon)."""

from __future__ import annotations

from datetime import UTC, datetime

from deck.docker_gateway import (
    ConnectionState,
    ContainerLogView,
    ContainerOperationError,
    ContainerRunError,
    ContainerRunRequest,
    DockerGateway,
    DockerSnapshot,
    ManagedContainer,
    ManagedImage,
    ManagedNetwork,
    ManagedVolume,
    ResourceType,
    bucket_for_status,
)


class RunFakeGateway(DockerGateway):
    """In-memory gateway that records run/pull calls for assertions."""

    def __init__(
        self,
        images: list[ManagedImage] | None = None,
        containers: list[ManagedContainer] | None = None,
        networks: list[ManagedNetwork] | None = None,
        fail_run: ContainerRunError | None = None,
        fail_pull: ContainerRunError | None = None,
    ) -> None:
        self.images = (
            images
            if images is not None
            else [
                ManagedImage(
                    image_id="sha256:abc123",
                    repository_tag="nginx:latest",
                    size_bytes=1024,
                    created="2026-01-01 00:00",
                )
            ]
        )
        self.containers = containers if containers is not None else []
        self.networks = (
            networks
            if networks is not None
            else [
                ManagedNetwork(network_id="net1", name="bridge", driver="bridge", scope="local"),
                ManagedNetwork(network_id="net2", name="app-net", driver="bridge", scope="local"),
            ]
        )
        self.fail_run = fail_run
        self.fail_pull = fail_pull
        self.run_requests: list[ContainerRunRequest] = []
        self.pulled: list[str] = []
        self.next_container_id = "cid-new-1"

    @property
    def endpoint(self) -> str:
        return "fake://run"

    def get_snapshot(self) -> DockerSnapshot:
        return DockerSnapshot(
            state=ConnectionState.CONNECTED,
            summary=None,
            detail="Connected to Docker fake.",
            endpoint=self.endpoint,
            probed_at=datetime.now(UTC),
        )

    def list_containers(self) -> list[ManagedContainer]:
        return list(self.containers)

    def get_container(self, container_id: str) -> ManagedContainer:
        for container in self.containers:
            if container.container_id == container_id:
                return container
            raise ContainerOperationError(
                "inspect", container_id, "it was not found.", "Refresh first."
            )

    def container_logs(self, container_id: str, tail: int = 200) -> ContainerLogView:
        return ContainerLogView(container_id=container_id, lines=(), fetched_at=datetime.now(UTC))

    def start_container(self, container_id: str) -> ManagedContainer:
        return self.get_container(container_id)

    def stop_container(self, container_id: str) -> ManagedContainer:
        return self.get_container(container_id)

    def restart_container(self, container_id: str) -> ManagedContainer:
        return self.get_container(container_id)

    def remove_container(self, container_id: str) -> None:
        return None

    def list_images(self) -> list[ManagedImage]:
        return list(self.images)

    def list_volumes(self) -> list[ManagedVolume]:
        return []

    def list_networks(self) -> list[ManagedNetwork]:
        return list(self.networks)

    def create_and_run_container(self, request: ContainerRunRequest) -> str:
        if self.fail_run is not None:
            raise self.fail_run
        self.run_requests.append(request)
        self.containers.append(
            ManagedContainer(
                container_id=self.next_container_id,
                name=request.name,
                image_ref=request.image,
                state_bucket=bucket_for_status("running"),
                exact_status="running",
            )
        )
        return self.next_container_id

    def pull_image(self, image: str) -> None:
        if self.fail_pull is not None:
            raise self.fail_pull
        self.pulled.append(image)


def make_running_container(name: str) -> ManagedContainer:
    return ManagedContainer(
        container_id=f"cid-{name}",
        name=name,
        image_ref="nginx:latest",
        state_bucket=bucket_for_status("running"),
        exact_status="running",
    )


def make_image(repository_tag: str) -> ManagedImage:
    return ManagedImage(
        image_id="sha256:zzz",
        repository_tag=repository_tag,
        size_bytes=1,
        created="2026-01-01 00:00",
    )


def resource_type_images() -> ResourceType:
    return ResourceType.IMAGES
