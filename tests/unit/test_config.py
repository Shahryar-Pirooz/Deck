"""US5: config defaults, persistence, and per-field fallback."""

from __future__ import annotations

from pathlib import Path

from docker_tui.config import DEFAULT_ENDPOINT, load_config


def write_config(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_defaults_when_missing(tmp_path: Path) -> None:
    config = load_config(tmp_path / "does-not-exist.toml")
    assert config.docker.endpoint == DEFAULT_ENDPOINT
    assert config.display.theme == "dark"
    assert config.logging.debug is False
    assert config.ignored == ()


def test_valid_edits_survive(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        '[docker]\nendpoint = "unix:///custom/docker.sock"\n'
        '[display]\ntheme = "light"\n[logging]\ndebug = true\n',
    )
    config = load_config(path)
    assert config.docker.endpoint == "unix:///custom/docker.sock"
    assert config.display.theme == "light"
    assert config.logging.debug is True
    assert config.ignored == ()


def test_invalid_toml_falls_back(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path, "[[[broken"))
    assert config.docker.endpoint == DEFAULT_ENDPOINT
    assert len(config.ignored) == 1


def test_bad_single_value_falls_back_per_field(tmp_path: Path) -> None:
    path = write_config(tmp_path, '[display]\ntheme = "neon"\n[logging]\ndebug = "yes"\n')
    config = load_config(path)
    assert config.display.theme == "dark"  # default for bad field only
    assert config.logging.debug is False
    assert len(config.ignored) == 2


def test_remote_endpoint_rejected(tmp_path: Path) -> None:
    path = write_config(tmp_path, '[docker]\nendpoint = "tcp://remote:2375"\n')
    config = load_config(path)
    assert config.docker.endpoint == DEFAULT_ENDPOINT
    assert any("unix://" in notice for notice in config.ignored)


def test_unknown_keys_ignored_silently(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path, "[future]\nfoo = 1\n"))
    assert config.docker.endpoint == DEFAULT_ENDPOINT
