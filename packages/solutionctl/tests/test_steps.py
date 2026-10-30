"""Tests for ``solutionctl steps`` console separation."""

import io
import pytest
from contextlib import redirect_stdout
from pathlib import Path
from solutionctl.commands import steps

REPO_ROOT = Path(__file__).resolve().parents[3]
SOLUTIONS_ROOT = REPO_ROOT / "solutions"
SPEC_DIR = REPO_ROOT / "spec"


def test_steps_splits_console_into_infrastructure_section():
    """Verify that solutions with recamera_console steps have the console
    isolated in 'Console Infrastructure Steps (Legacy / Pre-flight)' and application steps numbered separately."""
    target_solution = SOLUTIONS_ROOT / "recamera_ecosystem"
    if not target_solution.is_dir():
        pytest.skip(f"Solution directory not found: {target_solution}")

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = steps.run(str(target_solution), lang="zh", spec_dir=str(SPEC_DIR))

    assert rc == 0
    out = buf.getvalue()
    assert "🛠 Console Infrastructure Steps (Legacy / Pre-flight):" in out
    assert "升级 reCamera 控制台" in out
    assert "{#deploy_console}" in out
    assert "🚀 Application Deployment Steps:" in out
    # Application step 1 is installing the app, not deploy_console
    assert "1. 安装目标检测应用  {#obj_install_app}" in out
