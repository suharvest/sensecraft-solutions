"""Locate the SenseCraft Solution engine binary (zero engine code).

Three-level resolution, per ``docs/OPEN_SOLUTION_SPLIT_PLAN.md`` §4.2:

1. ``$SENSECRAFT_ENGINE_BIN``
2. ``~/.sensecraft/engine.json`` handshake file (``bin`` field)
3. platform-native discovery (macOS mdfind / Windows registry / Linux dpkg)

Each candidate is *validated before acceptance*; an invalid candidate falls
through to the next level. If nothing is found, a friendly
:class:`EngineNotFoundError` is raised.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path
from typing import List, Optional

IDENTIFIER = "com.seeedstudio.sensecraft-solution"
DISPLAY_NAME = "SenseCraft Solution"
DEB_PACKAGE = "sensecraft-solution"
ENGINE_BASENAME = "provisioning-station"

HANDSHAKE_PATH = Path.home() / ".sensecraft" / "engine.json"


class EngineNotFoundError(RuntimeError):
    """Raised when no usable engine binary can be located."""


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def _has_internal_sibling(bin_path: Path) -> bool:
    """True if a PyInstaller onedir ``_internal`` directory sits next to the
    binary.

    Two on-disk shapes must both be accepted:

    * **Native PyInstaller onedir** — ``<dir>/provisioning-station`` plus a real
      ``<dir>/_internal/`` directory.
    * **Tauri junction** (Windows) — the App installs the binary next to an
      ``_internal`` *junction* (reparse point) that resolves to the bundled
      resources. ``Path.is_dir()`` follows the junction transparently, so the
      same check works; we deliberately do **not** require it to be a "real"
      directory.

    On dev/non-frozen layouts an ``_internal`` may be absent; we treat its
    presence as a positive signal but never hard-fail on its absence, because a
    plain Python entry point shim is still a valid engine for our purposes.
    """
    internal = bin_path.parent / "_internal"
    try:
        # is_dir() follows symlinks/junctions, which is what we want.
        return internal.is_dir()
    except OSError:
        return False


def _is_valid_engine(candidate: Optional[Path]) -> bool:
    """A candidate is valid when it is an existing, executable file.

    The ``_internal`` sibling is checked as a soft signal: if there *is* a
    sibling entry named ``_internal`` it must be a directory (or a junction
    resolving to one); a stale/dangling junction makes the candidate invalid so
    resolution falls through to the next level.
    """
    if candidate is None:
        return False
    try:
        if not candidate.is_file():
            return False
        if not os.access(candidate, os.X_OK):
            return False
    except OSError:
        return False

    sibling = candidate.parent / "_internal"
    if sibling.exists() or sibling.is_symlink():
        # Something named _internal is present — it must resolve to a directory.
        # A dangling junction (exists() False but is_symlink() True) is invalid.
        if not _has_internal_sibling(candidate):
            return False
    return True


# --------------------------------------------------------------------------- #
# Level 1: environment variable
# --------------------------------------------------------------------------- #
def _from_env() -> Optional[Path]:
    raw = os.environ.get("SENSECRAFT_ENGINE_BIN")
    if not raw:
        return None
    cand = Path(raw).expanduser()
    return cand if _is_valid_engine(cand) else None


# --------------------------------------------------------------------------- #
# Level 2: handshake file
# --------------------------------------------------------------------------- #
def _from_handshake(handshake_path: Path = HANDSHAKE_PATH) -> Optional[Path]:
    try:
        data = json.loads(handshake_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    bin_field = data.get("bin") if isinstance(data, dict) else None
    if not bin_field:
        return None
    cand = Path(str(bin_field)).expanduser()
    return cand if _is_valid_engine(cand) else None


# --------------------------------------------------------------------------- #
# Level 3: platform-native discovery
# --------------------------------------------------------------------------- #
def _native_candidates_macos() -> List[Path]:
    candidates: List[Path] = []
    try:
        out = subprocess.run(
            ["mdfind", f"kMDItemCFBundleIdentifier=='{IDENTIFIER}'"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        for line in out.stdout.splitlines():
            app = line.strip()
            if app:
                candidates.append(Path(app) / "Contents" / "MacOS" / ENGINE_BASENAME)
    except (OSError, subprocess.SubprocessError):
        pass
    # Fallback: the conventional install location.
    candidates.append(
        Path("/Applications") / f"{DISPLAY_NAME}.app" / "Contents" / "MacOS" / ENGINE_BASENAME
    )
    return candidates


def _native_candidates_windows() -> List[Path]:
    candidates: List[Path] = []
    try:
        import winreg  # type: ignore
    except ImportError:
        return candidates

    uninstall_subkey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    roots = [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]
    for root in roots:
        try:
            base = winreg.OpenKey(root, uninstall_subkey)
        except OSError:
            continue
        try:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(base, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(base, sub) as k:
                        try:
                            name, _ = winreg.QueryValueEx(k, "DisplayName")
                        except OSError:
                            continue
                        if name != DISPLAY_NAME:
                            continue
                        try:
                            loc, _ = winreg.QueryValueEx(k, "InstallLocation")
                        except OSError:
                            continue
                        if loc:
                            candidates.append(Path(loc) / f"{ENGINE_BASENAME}.exe")
                except OSError:
                    continue
        finally:
            winreg.CloseKey(base)
    return candidates


def _native_candidates_linux() -> List[Path]:
    candidates: List[Path] = []
    try:
        out = subprocess.run(
            ["dpkg", "-L", DEB_PACKAGE],
            capture_output=True,
            text=True,
            timeout=10,
        )
        for line in out.stdout.splitlines():
            p = line.strip()
            if p.endswith(f"/{ENGINE_BASENAME}"):
                candidates.append(Path(p))
    except (OSError, subprocess.SubprocessError):
        pass
    return candidates


def _from_native() -> Optional[Path]:
    system = platform.system()
    if system == "Darwin":
        candidates = _native_candidates_macos()
    elif system == "Windows":
        candidates = _native_candidates_windows()
    else:
        candidates = _native_candidates_linux()
    for cand in candidates:
        if _is_valid_engine(cand):
            return cand
    return None


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def locate_engine(handshake_path: Path = HANDSHAKE_PATH) -> Path:
    """Resolve the engine binary using three-level resolution.

    Raises :class:`EngineNotFoundError` with actionable guidance on failure.
    """
    for resolver in (
        _from_env,
        lambda: _from_handshake(handshake_path),
        _from_native,
    ):
        found = resolver()
        if found is not None:
            return found

    raise EngineNotFoundError(
        "Could not locate the SenseCraft Solution engine binary.\n"
        "Tried, in order:\n"
        "  1. $SENSECRAFT_ENGINE_BIN\n"
        f"  2. handshake file {handshake_path}\n"
        "  3. platform-native discovery\n\n"
        "Fix one of:\n"
        "  - Install the SenseCraft Solution desktop App (it writes the "
        "handshake file on first launch), or\n"
        "  - Set SENSECRAFT_ENGINE_BIN to the engine binary's absolute path."
    )
