"""``solutionctl manage`` — drive the engine's headless REST server.

Starts ``<bin> serve --headless`` (see ``_engine_http``), calls the REST
endpoint, then shuts the server down.
"""

from __future__ import annotations

import json
import sys

from .._engine_http import get, headless_engine


def list_apps() -> int:
    """List active/deployed applications via the REST API."""
    with headless_engine() as base_url:
        # 15 s as before this call moved into _engine_http.
        data = get(base_url, "/api/device-management/active", timeout=15.0)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def run(subcommand: str) -> int:
    """Dispatch a manage subcommand."""
    if subcommand in ("list-apps", "list"):
        return list_apps()
    print(f"Unknown manage subcommand: {subcommand!r}", file=sys.stderr)
    print("Available: list-apps", file=sys.stderr)
    return 2
