"""``solutionctl manage`` — drive the engine's headless REST server.

Starts ``<bin> serve --headless`` (see ``_engine_http``), calls the REST
endpoint, then shuts the server down.
"""

from __future__ import annotations

import json
import sys

from .._engine_http import EngineHttpError, get, headless_engine


# Same code the Rust engine CLI uses for "needs the desktop App" (HTTP 501).
EXIT_REQUIRES_APP = 4


def list_apps() -> int:
    """List active/deployed applications via the REST API."""
    try:
        with headless_engine() as base_url:
            # 15 s as before this call moved into _engine_http.
            data = get(base_url, "/api/device-management/active", timeout=15.0)
    except EngineHttpError as exc:
        if exc.status == 501 and exc.error == "requires_desktop_app":
            print(
                "This engine does not serve device management "
                "(requires the SenseCraft Solution desktop App's Python backend).\n"
                "Install or start the desktop App, or point SENSECRAFT_ENGINE_BIN "
                "at its provisioning-station binary.",
                file=sys.stderr,
            )
            return EXIT_REQUIRES_APP
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def run(subcommand: str) -> int:
    """Dispatch a manage subcommand."""
    if subcommand in ("list-apps", "list"):
        return list_apps()
    print(f"Unknown manage subcommand: {subcommand!r}", file=sys.stderr)
    print("Available: list-apps", file=sys.stderr)
    return 2
