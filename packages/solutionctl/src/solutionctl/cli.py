"""solutionctl command-line entry point.

Thin dispatcher: ``solution`` / ``deploy`` / ``manage`` / ``meta`` / ``validate``.
Contains zero engine code;
each command resolves the engine binary and drives it via subprocess.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from ._env import engine_env
from .engine_locator import EngineNotFoundError, locate_engine


def _cmd_meta(_args: argparse.Namespace) -> int:
    engine = locate_engine()
    print(f"Using engine: {engine}", file=sys.stderr)
    proc = subprocess.run(
        [str(engine), "meta", "--json"],
        capture_output=True,
        text=True,
        env=engine_env(),
    )
    sys.stderr.write(proc.stderr)
    if proc.returncode == 0:
        try:
            print(json.dumps(json.loads(proc.stdout), ensure_ascii=False, indent=2))
        except ValueError:
            sys.stdout.write(proc.stdout)
    else:
        sys.stdout.write(proc.stdout)
    return proc.returncode


def _cmd_solution(args: argparse.Namespace) -> int:
    from .commands import solution

    if args.solution_command == "list":
        return solution.run_list(solutions_dir=args.solutions_dir)
    if args.solution_command == "show":
        return solution.run_show(
            solution_id=args.solution_id,
            lang=args.lang,
            solutions_dir=args.solutions_dir,
        )
    # argparse enforces required=True on the subcommand, so this is unreachable.
    return 2


def _cmd_deploy(args: argparse.Namespace) -> int:
    from .commands import deploy

    return deploy.run(
        solution_id=args.solution_id,
        connection=args.connection,
        preset=args.preset,
        device=args.device,
        skip_verify=args.skip_verify,
        solutions_dir=args.solutions_dir,
        replace_existing=args.replace_existing,
        verbose=args.verbose,
    )


def _cmd_deploy_info(args: argparse.Namespace) -> int:
    from .commands import deploy_info

    return deploy_info.run(
        solution_id=args.solution_id,
        preset=args.preset,
        lang=args.lang,
        solutions_dir=args.solutions_dir,
    )


def _cmd_export(args: argparse.Namespace) -> int:
    from .commands import export

    return export.run(
        solution_id=args.solution_id,
        solutions_dir=args.solutions_dir,
        output_dir=args.output_dir,
    )


def _cmd_manage(args: argparse.Namespace) -> int:
    from .commands import manage

    return manage.run(args.subcommand)


def _cmd_validate(args: argparse.Namespace) -> int:
    from .commands import validate

    return validate.run(
        solution_path=args.solution_path,
        spec_dir=args.spec_dir,
        check_urls=args.check_urls,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="solutionctl",
        description="Thin client for the SenseCraft Solution engine binary.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_meta = sub.add_parser("meta", help="Print engine metadata (meta --json)")
    p_meta.set_defaults(func=_cmd_meta)

    p_solution = sub.add_parser(
        "solution", help="Discover solutions via the engine (list / show)"
    )
    sol_sub = p_solution.add_subparsers(dest="solution_command", required=True)

    p_sol_list = sol_sub.add_parser("list", help="List available solutions")
    p_sol_list.add_argument("--solutions-dir", default=None)
    p_sol_list.set_defaults(func=_cmd_solution)

    p_sol_show = sol_sub.add_parser(
        "show", help="Show a solution's detail incl. presets"
    )
    p_sol_show.add_argument("solution_id", help="Solution ID to show")
    p_sol_show.add_argument(
        "--lang", default=None, choices=["en", "zh"], help="Content language"
    )
    p_sol_show.add_argument("--solutions-dir", default=None)
    p_sol_show.set_defaults(func=_cmd_solution)

    p_deploy = sub.add_parser("deploy", help="Deploy a solution via the engine")
    p_deploy.add_argument("solution_id", help="Solution ID to deploy")
    p_deploy.add_argument("--connection", default=None, help="JSON device->params dict")
    p_deploy.add_argument("--preset", default=None, help="Preset ID")
    p_deploy.add_argument("--device", default=None, help="Single device ID")
    p_deploy.add_argument("--skip-verify", action="store_true")
    p_deploy.add_argument("--solutions-dir", default=None)
    p_deploy.add_argument(
        "--replace-existing",
        action="store_true",
        help="Auto stop + replace a same-named container if one already exists "
        "(otherwise the deploy fails and asks the user to confirm).",
    )
    # solutionctl runs the engine non-interactively and always passes the
    # engine's --yes internally, so this is a no-op accepted for ergonomics /
    # CI-script symmetry — agents naturally write `--yes` and it should not error.
    p_deploy.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Accepted for symmetry; deploys are always non-interactive.",
    )
    p_deploy.add_argument(
        "--verbose",
        action="store_true",
        help="Show the full engine event stream (docker pulls, polling). "
        "By default only the lifecycle skeleton + error logs are shown.",
    )
    p_deploy.set_defaults(func=_cmd_deploy)

    p_deploy_info = sub.add_parser(
        "deploy-info",
        help="Show presets, required params, and a fill-and-send deploy template",
    )
    p_deploy_info.add_argument("solution_id", help="Solution ID")
    p_deploy_info.add_argument(
        "--preset", default=None, help="Filter to a single preset ID"
    )
    p_deploy_info.add_argument(
        "--lang", default=None, choices=["en", "zh"], help="Content language"
    )
    p_deploy_info.add_argument("--solutions-dir", default=None)
    p_deploy_info.set_defaults(func=_cmd_deploy_info)

    p_export = sub.add_parser(
        "export",
        help="Package a solution into an import-ready zip (for app preview)",
    )
    p_export.add_argument("solution_id", help="Solution ID (directory under solutions/)")
    p_export.add_argument("--solutions-dir", default=None)
    p_export.add_argument(
        "--output-dir", default=None, help="Where to write <id>.zip (default: ./dist)"
    )
    p_export.set_defaults(func=_cmd_export)

    p_manage = sub.add_parser("manage", help="Drive headless device-management REST")
    p_manage.add_argument("subcommand", help="e.g. list-apps")
    p_manage.set_defaults(func=_cmd_manage)

    p_validate = sub.add_parser(
        "validate",
        help="Offline-validate a solution against the spec/ contract (zero engine)",
    )
    p_validate.add_argument("solution_path", help="Path to the solution directory")
    p_validate.add_argument(
        "--spec-dir",
        default=None,
        dest="spec_dir",
        help="Path to the spec/ directory (auto-discovered if omitted)",
    )
    p_validate.add_argument(
        "--check-urls",
        action="store_true",
        dest="check_urls",
        help="Also check that http(s):// references are reachable (4xx → fail; "
        "transient/5xx/network errors are tolerated)",
    )
    p_validate.set_defaults(func=_cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except EngineNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
