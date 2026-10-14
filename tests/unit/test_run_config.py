"""US1: name validation, unique-name suggestion, and run form logic."""

from __future__ import annotations

import pytest

from deck import services
from deck.docker_gateway import ContainerRunError
from deck.tui.run_config import RunConfigForm


def test_validate_name_rejects_empty() -> None:
    with pytest.raises(ContainerRunError) as excinfo:
        services.validate_name("")
    assert excinfo.value.code == "NameRequired"


def test_validate_name_rejects_whitespace_only() -> None:
    with pytest.raises(ContainerRunError) as excinfo:
        services.validate_name("   \t  ")
    assert excinfo.value.code == "NameRequired"


def test_validate_name_strips_and_returns() -> None:
    assert services.validate_name("  my-web  ") == "my-web"


def test_suggest_unique_name_returns_base_when_free() -> None:
    assert services.suggest_unique_name([], "myapp") == "myapp"
    assert services.suggest_unique_name(["other"], "myapp") == "myapp"


def test_suggest_unique_name_appends_numeric_suffix() -> None:
    # Spec clarification: suffix like "myapp-2".
    assert services.suggest_unique_name(["myapp"], "myapp") == "myapp-2"
    assert services.suggest_unique_name(["myapp", "myapp-2"], "myapp") == "myapp-3"


def test_suggest_unique_name_ignores_leading_slash() -> None:
    assert services.suggest_unique_name(["/myapp"], "myapp") == "myapp-2"


def test_form_build_request_parses_all_fields() -> None:
    form = RunConfigForm(
        name="my-web",
        ports=["8080:80"],
        volumes=["/data:/app/data"],
        network="",
        envs=["DEBUG=true", "A=b"],
    )
    request = form.build_request("nginx:latest")
    assert request.image == "nginx:latest"
    assert request.name == "my-web"
    assert [(p.host_port, p.container_port) for p in request.ports] == [("8080", "80")]
    assert [(v.source_path, v.container_path) for v in request.volumes] == [("/data", "/app/data")]
    assert request.network is None
    assert [(e.key, e.value) for e in request.env_vars] == [("DEBUG", "true"), ("A", "b")]


def test_form_build_request_requires_valid_name() -> None:
    form = RunConfigForm(name="   ")
    with pytest.raises(ContainerRunError) as excinfo:
        form.build_request("nginx:latest")
    assert excinfo.value.code == "NameRequired"


def test_form_review_text_includes_env_values() -> None:
    form = RunConfigForm(name="my-app", envs=["SECRET=hunter2"])
    text = form.review_text("nginx:latest")
    assert "my-app" in text
    assert "SECRET=hunter2" in text
    assert "nginx:latest" in text


def test_form_review_text_shows_defaults_for_empty_lists() -> None:
    form = RunConfigForm(name="bare")
    text = form.review_text("nginx:latest")
    assert "(none)" in text
    assert "default (bridge)" in text


def test_run_managed_never_logs_env_values(caplog: object) -> None:
    import logging

    from run_fakes import RunFakeGateway

    from deck.docker_gateway import ContainerRunRequest

    gateway = RunFakeGateway()
    request = ContainerRunRequest(
        image="nginx:latest",
        name="leaky",
        env_vars=(services.parse_env_var("DB_PASSWORD=hunter2"),),
    )
    with caplog.at_level(logging.DEBUG):  # type: ignore[attr-defined]
        services.run_managed(gateway, request)
    assert "hunter2" not in caplog.text  # type: ignore[attr-defined]


def test_redaction_filter_masks_sensitive_env_values() -> None:
    import logging

    from deck.logging_setup import RedactionFilter

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="env DB_PASSWORD=hunter2 API_KEY=abc123",
        args=(),
        exc_info=None,
    )
    RedactionFilter().filter(record)
    assert "hunter2" not in record.msg
    assert "abc123" not in record.msg
    assert "***REDACTED***" in record.msg
