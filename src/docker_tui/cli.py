"""Terminal entry point: ``Deck``."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from deck import __version__
from deck.config import ApplicationConfiguration, default_config_path, load_config
from deck.docker_gateway import DockerGateway
from deck.docker_sdk import SdkGateway
from deck.logging_setup import setup_logging
from deck.tui.app import DeckApp

log = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI flags."""
    parser = argparse.ArgumentParser(
        prog="Deck",
        description="Keyboard-first terminal UI for managing the local Docker Engine.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show diagnostic detail on screen (default from config file).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help=f"Override config file path (default {default_config_path()}).",
    )
    return parser.parse_args(argv)


def build_gateway(config: ApplicationConfiguration) -> DockerGateway:
    """Create the local-Engine gateway from configuration."""
    return SdkGateway(endpoint=config.docker.endpoint)


def main(argv: list[str] | None = None) -> int:
    """Launch the TUI. Returns the process exit code."""
    args = parse_args(argv)
    try:
        config = load_config(args.config)
    except Exception as exc:  # noqa: BLE001 - config must never block startup
        print(f"Deck: ignoring config ({exc}); using defaults.", file=sys.stderr)
        config = ApplicationConfiguration()

    debug = bool(args.debug or config.logging.debug)
    try:
        log_path = setup_logging(debug=debug)
    except Exception as exc:  # noqa: BLE001 - logging must never block startup
        print(f"Deck: logging unavailable ({exc}).", file=sys.stderr)
        log_path = Path("-")

    for notice in config.ignored:
        print(f"Deck: config: {notice}", file=sys.stderr)

    try:
        gateway = build_gateway(config)
        app = DeckApp(gateway=gateway, config=config)
    except Exception as exc:  # noqa: BLE001 - fatal init stays concise
        print(f"Deck: failed to initialize: {exc}", file=sys.stderr)
        if debug:
            raise
        return 1

    log.info("Starting Deck (debug=%s, log=%s)", debug, log_path)
    try:
        app.run()
    except KeyboardInterrupt:
        return 0
    except Exception as exc:  # noqa: BLE001 - fatal runtime stays concise
        print(f"Deck: fatal error: {exc}", file=sys.stderr)
        if debug:
            raise
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
