"""Stdlib logging with secret redaction on every handler."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import platformdirs

from deck.config import APP_NAME

_REDACT_PATTERN = re.compile(
    r"(?i)(password|passwd|token|secret|authorization|api[_-]?key)\s*[:=]\s*"
    r"([\"']?)([^\s\"',;}]+)\2"
)
_REDACT_REPLACEMENT = r"\1=***REDACTED***"


class RedactionFilter(logging.Filter):
    """Replace credential-like values with ***REDACTED*** in log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = _REDACT_PATTERN.sub(_REDACT_REPLACEMENT, message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def default_log_path() -> Path:
    """Return the platform log file path."""
    return platformdirs.user_log_path(APP_NAME) / f"{APP_NAME}.log"


def setup_logging(debug: bool = False) -> Path:
    """Configure root logging; return the log file path."""
    log_path = default_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    redaction = RedactionFilter()

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.addFilter(redaction)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if debug else logging.WARNING)
    console_handler.addFilter(redaction)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    root.addHandler(file_handler)
    root.addHandler(console_handler)
    return log_path
