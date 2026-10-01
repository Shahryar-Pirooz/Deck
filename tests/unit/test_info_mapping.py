"""US1: Engine payload → summary field mapping (no live daemon)."""

from __future__ import annotations

from deck.docker_sdk import build_summary


def test_full_payload_mapping() -> None:
    summary = build_summary(
        {"Version": "29.8.1", "ApiVersion": "1.56", "Os": "linux", "Arch": "amd64"},
        {
            "Containers": 4,
            "ContainersRunning": 1,
            "ContainersStopped": 2,
            "Images": 9,
        },
    )
    assert summary.version == "29.8.1"
    assert summary.api_version == "1.56"
    assert summary.os == "linux"
    assert summary.architecture == "amd64"
    assert (summary.containers_total, summary.containers_running) == (4, 1)
    assert summary.containers_stopped == 2
    assert summary.images == 9


def test_missing_api_version_is_null() -> None:
    summary = build_summary(
        {"Version": "29.8.1", "Os": "linux", "Arch": "amd64"},
        {"Containers": 0, "ContainersRunning": 0, "ContainersStopped": 0, "Images": 0},
    )
    assert summary.api_version is None  # displayed as unavailable, view not blocked


def test_missing_stopped_derived() -> None:
    summary = build_summary(
        {"Version": "29.8.1", "ApiVersion": "1.56", "Os": "linux", "Arch": "amd64"},
        {"Containers": 3, "ContainersRunning": 1, "Images": 2},
    )
    assert summary.containers_stopped == 2  # derived total - running
