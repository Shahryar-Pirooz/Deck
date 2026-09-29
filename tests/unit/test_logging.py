"""US5: log redaction filter on both handlers."""

from __future__ import annotations

import logging

from docker_tui.logging_setup import RedactionFilter, setup_logging


def test_redaction_filter_masks_credentials() -> None:
    filtr = RedactionFilter()
    record = logging.LogRecord(
        name="t",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="connect password=supersecret token=abc123 ok",
        args=(),
        exc_info=None,
    )
    assert filtr.filter(record) is True
    assert "supersecret" not in record.getMessage()
    assert "abc123" not in record.getMessage()
    assert "***REDACTED***" in record.getMessage()


def test_setup_logging_applies_filter(tmp_path: object, monkeypatch: object) -> None:
    import platformdirs

    monkeypatch.setattr(  # type: ignore[attr-defined]
        platformdirs, "user_log_path", lambda _name: __import__("pathlib").Path(str(tmp_path))
    )
    log_path = setup_logging(debug=True)
    root = logging.getLogger()
    try:
        assert any(
            any(isinstance(f, RedactionFilter) for f in h.filters)
            for h in root.handlers
            if isinstance(h, (logging.FileHandler, logging.StreamHandler))
        )
        assert str(log_path).endswith("docker-tui.log")
    finally:
        for handler in list(root.handlers):
            root.removeHandler(handler)
            try:
                handler.close()
            except Exception:  # noqa: BLE001
                pass
