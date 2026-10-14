"""US3: volume mount and environment variable parsing."""

from __future__ import annotations

import pytest

from deck import services
from deck.docker_gateway import ContainerRunError


def test_parse_valid_volume_mount() -> None:
    mount = services.parse_volume_mount("/data:/app/data")
    assert mount.source_path == "/data"
    assert mount.container_path == "/app/data"


def test_parse_volume_mount_strips_whitespace() -> None:
    mount = services.parse_volume_mount("  /data:/app/data  ")
    assert mount.source_path == "/data"
    assert mount.container_path == "/app/data"


def test_parse_volume_missing_destination_rejected() -> None:
    with pytest.raises(ContainerRunError) as excinfo:
        services.parse_volume_mount("/data")
    assert excinfo.value.code == "InvalidVolumeFormat"


def test_parse_volume_empty_parts_rejected() -> None:
    with pytest.raises(ContainerRunError) as excinfo:
        services.parse_volume_mount(":")
    assert excinfo.value.code == "InvalidVolumeFormat"


def test_parse_valid_env_var() -> None:
    entry = services.parse_env_var("DEBUG=true")
    assert entry.key == "DEBUG"
    assert entry.value == "true"


def test_parse_env_var_value_may_contain_equals() -> None:
    entry = services.parse_env_var("OPTS=a=b")
    assert entry.key == "OPTS"
    assert entry.value == "a=b"


def test_parse_env_var_value_may_be_empty() -> None:
    entry = services.parse_env_var("EMPTY=")
    assert entry.key == "EMPTY"
    assert entry.value == ""


def test_parse_env_var_without_equals_rejected() -> None:
    with pytest.raises(ContainerRunError) as excinfo:
        services.parse_env_var("DEBUG")
    assert excinfo.value.code == "InvalidEnvFormat"


def test_parse_env_var_empty_key_rejected() -> None:
    with pytest.raises(ContainerRunError) as excinfo:
        services.parse_env_var("=value")
    assert excinfo.value.code == "InvalidEnvFormat"
