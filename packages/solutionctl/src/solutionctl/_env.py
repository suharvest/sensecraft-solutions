"""Engine subprocess environment derivation (zero engine code).

The engine binary resolves its solutions/devices directories from the
``PS_SOLUTIONS_DIR`` / ``PS_DEVICES_DIR`` environment variables. When
``solutionctl`` drives an already-installed App's sidecar, those variables are
*not* set (the App only sets them for its own GUI launch, and the handshake file
records only the engine path). The result: the engine falls back to its bundled
solutions and cannot see the solutions in a fresh ``git clone``.

:func:`engine_env` fixes that by deriving both directories from the caller's
context and merging them into a copy of ``os.environ`` that every subprocess
launch passes via ``env=``:

* ``PS_SOLUTIONS_DIR`` — explicit ``--solutions-dir`` argument if given,
  otherwise the ``solutions/`` directory of the repo root discovered by walking
  up from the current working directory (a repo root contains both
  ``solutions/`` and ``spec/``). If no such repo is found, it is left unset and
  the engine keeps its own default.
* ``PS_DEVICES_DIR`` — best-effort, from the installed desktop App's bundled
  ``devices/`` (see :func:`solutionctl.engine_locator.locate_app_devices`). A
  fresh clone has no global ``devices/`` catalog, but the App ships one; without
  it, solutions that reference a ``device_class`` (e.g. ``jetson``) fail to load.
  If the App can't be found, it is left unset and the engine emits a warning but
  still works for solutions that don't need a device catalog.

A pre-existing value in ``os.environ`` is always respected (never overwritten),
so an operator can force either path explicitly.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

from .engine_locator import locate_app_devices


def _find_repo_solutions_dir(start: Optional[Path] = None) -> Optional[Path]:
    """Walk up from ``start`` (default cwd) to find a repo root's ``solutions/``.

    A repo root is identified by containing *both* a ``solutions/`` directory and
    a ``spec/`` directory — the layout of the public ``sensecraft-solutions``
    repo. Returns the ``solutions/`` path, or ``None`` if no such root is found.
    """
    here = (start or Path.cwd()).resolve()
    for d in (here, *here.parents):
        if (d / "solutions").is_dir() and (d / "spec").is_dir():
            return d / "solutions"
    return None


def engine_env(solutions_dir: Optional[str] = None) -> Dict[str, str]:
    """Return a copy of ``os.environ`` with engine path vars filled in.

    ``solutions_dir`` (if provided) takes precedence for ``PS_SOLUTIONS_DIR``;
    otherwise it is auto-discovered from the repo root above the cwd.
    ``PS_DEVICES_DIR`` is best-effort from the installed App. Existing
    environment values are never overwritten.
    """
    env = dict(os.environ)

    if "PS_SOLUTIONS_DIR" not in env:
        if solutions_dir:
            env["PS_SOLUTIONS_DIR"] = str(Path(solutions_dir).expanduser().resolve())
        else:
            found = _find_repo_solutions_dir()
            if found is not None:
                env["PS_SOLUTIONS_DIR"] = str(found)

    if "PS_DEVICES_DIR" not in env:
        devices = locate_app_devices()
        if devices is not None:
            env["PS_DEVICES_DIR"] = str(devices)

    # The engine writes its logs/cache/runtime state under ``<data_dir>``, which
    # defaults to ``_internal/data`` *inside the frozen PyInstaller payload*. The
    # GUI App sidesteps this by copying ``_internal`` to a writable cache before
    # launch; when ``solutionctl`` drives the *installed* engine in place, that
    # payload is read-only — ``/usr/lib/<App>/...`` on a .deb install, or the
    # read-only ``.app`` bundle on macOS — so any command that writes a cache or
    # log entry (``solution``/``deploy``/``deploy-info``) crashes with EACCES or
    # ENOENT. Redirect all three writable dirs to a per-user location. (The
    # defaults are independent fields baked at engine-class definition, so
    # ``PS_DATA_DIR`` alone does not move logs/cache — set each explicitly.)
    runtime_base = Path.home() / ".sensecraft" / "engine-runtime"
    for var, sub in (("PS_DATA_DIR", None), ("PS_LOGS_DIR", "logs"), ("PS_CACHE_DIR", "cache")):
        if var not in env:
            env[var] = str(runtime_base / sub if sub else runtime_base)

    return env
