"""Adapter tests for create_and_run_container and pull_image (no live daemon)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from docker.errors import APIError, DockerException, NotFound

from deck.docker_gateway import (
    ContainerRunError,
    ContainerRunRequest,
    EnvVar,
    PortMapping,
    VolumeMount,
)
from deck.docker_sdk import SdkGateway


def _gateway_with(client: MagicMock) -> tuple[MagicMock, SdkGateway]:
    gateway = SdkGateway()
    gateway._make_client = lambda: client  # type: ignore[method-assign]
    return client, gateway


def _client() -> MagicMock:
    client = MagicMock()
    container = MagicMock()
    container.id = "cid-123"
    client.containers.run.return_value = container
    return client


def test_create_and_run_passes_all_options_to_sdk() -> None:
    client, gateway = _gateway_with(_client())
    request = ContainerRunRequest(
        image="nginx:latest",
        name="my-web",
        ports=(PortMapping("8080", "80"),),
        volumes=(VolumeMount("/data", "/app/data"),),
        network="app-net",
        env_vars=(EnvVar("DEBUG", "true"),),
    )
    container_id = gateway.create_and_run_container(request)
    assert container_id == "cid-123"
    kwargs = client.containers.run.call_args.kwargs
    assert kwargs["detach"] is True
    assert kwargs["name"] == "my-web"
    assert kwargs["ports"] == {"8080/tcp": "80"}
    assert kwargs["volumes"] == {"/data": {"bind": "/app/data", "mode": "rw"}}
    assert kwargs["network"] == "app-net"
    assert kwargs["environment"] == ["DEBUG=true"]
    client.close.assert_called()


def test_create_and_run_minimal_request_omits_empty_options() -> None:
    client, gateway = _gateway_with(_client())
    gateway.create_and_run_container(ContainerRunRequest(image="nginx:latest", name="bare"))
    kwargs = client.containers.run.call_args.kwargs
    assert "ports" not in kwargs
    assert "volumes" not in kwargs
    assert "environment" not in kwargs
    assert "network" not in kwargs


def test_create_name_collision_maps_to_contract_code() -> None:
    client, gateway = _gateway_with(_client())
    client.containers.run.side_effect = APIError("conflict", response=MagicMock(status_code=409))
    with pytest.raises(ContainerRunError) as excinfo:
        gateway.create_and_run_container(ContainerRunRequest(image="nginx:latest", name="dup"))
    assert excinfo.value.code == "NameCollision"


def test_create_missing_image_maps_to_image_not_found() -> None:
    client, gateway = _gateway_with(_client())
    response = MagicMock(status_code=404)
    client.containers.run.side_effect = NotFound("no such image", response=response)
    with pytest.raises(ContainerRunError) as excinfo:
        gateway.create_and_run_container(ContainerRunRequest(image="ghost:latest", name="x"))
    assert excinfo.value.code == "ImageNotFound"


def test_create_daemon_down_maps_to_daemon_unavailable() -> None:
    client, gateway = _gateway_with(_client())
    client.containers.run.side_effect = DockerException("cannot connect to daemon")
    with pytest.raises(ContainerRunError) as excinfo:
        gateway.create_and_run_container(ContainerRunRequest(image="nginx:latest", name="x"))
    assert excinfo.value.code == "DaemonUnavailable"


def test_pull_image_success_records_call() -> None:
    client, gateway = _gateway_with(_client())
    gateway.pull_image("busybox:latest")
    client.images.pull.assert_called_once_with("busybox:latest")
    client.close.assert_called()


def test_pull_image_not_found_maps_to_contract_code() -> None:
    client, gateway = _gateway_with(_client())
    response = MagicMock(status_code=404)
    client.images.pull.side_effect = NotFound("not found", response=response)
    with pytest.raises(ContainerRunError) as excinfo:
        gateway.pull_image("ghost:latest")
    assert excinfo.value.code == "ImageNotFound"
