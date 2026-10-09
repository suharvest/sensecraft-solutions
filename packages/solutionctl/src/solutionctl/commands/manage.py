"""``solutionctl manage`` — call the engine's device-management REST API.

With the Rust engine this goes through the shared engine instance (``daemon
ensure`` + a lease held while the command runs); older engines get a
temporary ``serve --headless`` that is shut down afterwards (see
``_engine_http.engine_session``).
"""

from __future__ import annotations

import json
import sys

from .._engine_http import EngineConflictError, EngineHttpError, engine_session
from ..engine_locator import EngineNotFoundError


# Same codes the Rust engine CLI uses: instance conflict / shutting down (3),
# "needs the desktop App" (HTTP 501 -> 4).
EXIT_CONFLICT = 3
EXIT_REQUIRES_APP = 4


def list_apps() -> int:
    """List active/deployed applications via the REST API."""
    try:
        with engine_session() as conn:
            # 15 s as before this call moved into _engine_http.
            data = conn.get("/api/device-management/active", timeout=15.0)
    except EngineConflictError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_CONFLICT
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
    except EngineNotFoundError:
        raise  # cli.main prints the guidance (exit 3)
    except RuntimeError as exc:
        # the engine did not come up (no ready line, ensure failed, ...)
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
