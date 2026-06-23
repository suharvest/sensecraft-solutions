"""``solutionctl export`` — package a solution into an import-ready zip.

Produces a zip with ``solution.yaml`` at its root, the format accepted by the
desktop App's "Import Solution" flow (``POST /api/solutions/import/parse``).
Use it to preview locally-edited content in the installed app without a build.

Zero engine code — this is a pure local zip of the solution directory (junk
files like ``.DS_Store`` excluded). The solution directory is taken from
``--solutions-dir`` if given, otherwise auto-discovered from the repo root above
the current working directory (same logic the engine-driven commands use).
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from typing import Optional

import yaml

from .._env import _find_repo_solutions_dir

_JUNK_NAMES = {".DS_Store", "Thumbs.db", "__pycache__"}


def _keep(p: Path) -> bool:
    return p.is_file() and not any(part in _JUNK_NAMES for part in p.parts)


def _create_zip(solution_dir: Path, output_path: Path) -> None:
    """Zip *solution_dir* with paths relative to it (solution.yaml at root)."""
    files = sorted(p for p in solution_dir.rglob("*") if _keep(p))
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, f.relative_to(solution_dir).as_posix())


def run(
    solution_id: str,
    solutions_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> int:
    if solutions_dir:
        sols = Path(solutions_dir).expanduser().resolve()
    else:
        sols = _find_repo_solutions_dir()
        if sols is None:
            print(
                "Could not find a solutions/ directory. Run from inside a clone "
                "of the sensecraft-solutions repo, or pass --solutions-dir.",
                file=sys.stderr,
            )
            return 1

    solution_dir = sols / solution_id
    yaml_path = solution_dir / "solution.yaml"
    if not yaml_path.exists():
        print(f"Error: solution.yaml not found at {yaml_path}", file=sys.stderr)
        print(
            "Hint: `solutionctl solution list` shows available ids.",
            file=sys.stderr,
        )
        return 1

    try:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        print(f"Error: solution.yaml is not valid YAML: {exc}", file=sys.stderr)
        return 1
    sid = data.get("id") or solution_id
    name = data.get("name") or sid

    out = (
        Path(output_dir).expanduser().resolve()
        if output_dir
        else (Path.cwd() / "dist")
    )
    out.mkdir(parents=True, exist_ok=True)
    output_path = out / f"{sid}.zip"
    _create_zip(solution_dir, output_path)

    size_kb = output_path.stat().st_size / 1024
    print(f"Exported: {name} ({sid})")
    print(f"  source: {solution_dir}")
    print(f"  zip   : {output_path}  ({size_kb:.1f} KB)")
    print()
    print("Next: open the SenseCraft app -> Solutions -> Import, select the zip")
    print("(or use the preview-solution-content skill to import via the API).")
    return 0
