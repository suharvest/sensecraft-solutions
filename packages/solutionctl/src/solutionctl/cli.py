"""solutionctl command-line entry point.

Thin dispatcher: ``deploy`` / ``manage`` / ``meta``. Contains zero engine code;
each command resolves the engine binary and drives it via subprocess.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from .engine_locator import EngineNotFoundError, locate_engine


def _cmd_meta(_args: argparse.Namespace) -> int:
    engine = locate_engine()
    print(f"Using engine: {engine}", file=sys.stderr)
    proc = subprocess.run([str(engine), "meta", "--json"], capture_output=True, text=True)
    sys.stderr.write(proc.stderr)
    if proc.returncode == 0:
        try:
            print(json.dumps(json.loads(proc.stdout), ensure_ascii=False, indent=2))
        except ValueError:
            sys.stdout.write(proc.stdout)
    else:
        sys.stdout.write(proc.stdout)
    return proc.returncode


def _cmd_deploy(args: argparse.Namespace) -> int:
    from .commands import deploy

    return deploy.run(
        solution_id=args.solution_id,
        connection=args.connection,
        preset=args.preset,
        device=args.device,
        skip_verify=args.skip_verify,
        solutions_dir=args.solutions_dir,
    )


def _cmd_manage(args: argparse.Namespace) -> int:
    from .commands import manage

    return manage.run(args.subcommand)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="solutionctl",
        description="Thin client for the SenseCraft Solution engine binary.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_meta = sub.add_parser("meta", help="Print engine metadata (meta --json)")
    p_meta.set_defaults(func=_cmd_meta)

    p_deploy = sub.add_parser("deploy", help="Deploy a solution via the engine")
    p_deploy.add_argument("solution_id", help="Solution ID to deploy")
    p_deploy.add_argument("--connection", default=None, help="JSON device->params dict")
    p_deploy.add_argument("--preset", default=None, help="Preset ID")
    p_deploy.add_argument("--device", default=None, help="Single device ID")
    p_deploy.add_argument("--skip-verify", action="store_true")
    p_deploy.add_argument("--solutions-dir", default=None)
    p_deploy.set_defaults(func=_cmd_deploy)

    p_manage = sub.add_parser("manage", help="Drive headless device-management REST")
    p_manage.add_argument("subcommand", help="e.g. list-apps")
    p_manage.set_defaults(func=_cmd_manage)

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
