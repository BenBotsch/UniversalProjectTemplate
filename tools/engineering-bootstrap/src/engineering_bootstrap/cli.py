"""Command line interface ``project-bootstrap``.

Every command runs as a dry run unless ``--apply`` is given. Exit codes:

- ``0``: the run succeeded.
- ``1``: a change failed or the configuration is invalid.
- ``2``: invalid usage, or the command is not implemented yet.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from engineering_bootstrap import __version__
from engineering_bootstrap.config import CONFIG_NAMES, resolve_config_dir, validate_config
from engineering_bootstrap.engine import Action, Change
from engineering_bootstrap.github import RedactingFilter
from engineering_bootstrap.report import Report, render_json, render_text

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
DEFAULT_CONFIG = Path(".project/bootstrap.yml")
CONFIG_RESOURCE = "config"


def _common_options() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="bootstrap.yml or the .project directory (default: %(default)s)",
    )
    mode = common.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        dest="apply",
        action="store_false",
        help="only report planned changes (default)",
    )
    mode.add_argument("--apply", dest="apply", action="store_true", help="write the changes")
    common.set_defaults(apply=False)
    common.add_argument(
        "--format", choices=("text", "json"), default="text", help="output format of the report"
    )
    common.add_argument("--report-file", type=Path, help="also write the JSON report to this file")
    common.add_argument("-v", "--verbose", action="store_true", help="log debug messages")
    return common


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser with all subcommands."""
    common = _common_options()
    parser = argparse.ArgumentParser(
        prog="project-bootstrap",
        description="Plan and apply the GitHub setup of a project created from the template.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    init = commands.add_parser(
        "init", parents=[common], help="create and configure a repository (not implemented yet)"
    )
    init.add_argument("--repo", required=True, metavar="OWNER/NAME")
    init.add_argument("--profile", metavar="PROFILE", help="technology profile, e.g. python")

    validate = commands.add_parser(
        "validate",
        parents=[common],
        help="validate the configuration; with --repo also the repository (not implemented yet)",
    )
    validate.add_argument("--repo", metavar="OWNER/NAME")

    sync = commands.add_parser(
        "sync-labels", parents=[common], help="synchronize labels (not implemented yet)"
    )
    sync.add_argument("--repo", required=True, metavar="OWNER/NAME")

    audit = commands.add_parser(
        "audit", parents=[common], help="audit the repositories of an owner (not implemented yet)"
    )
    audit.add_argument("--owner", required=True, metavar="OWNER")
    return parser


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
        force=True,
    )
    # Removes credential-like values even before a token is known.
    redacting = RedactingFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(redacting)


def validate_local(config_dir: Path) -> list[Change]:
    """Return one change per configuration file: ``noop`` if valid, else ``failed``."""
    _, problems = validate_config(config_dir)
    changes = []
    for name in CONFIG_NAMES:
        file_problems = problems[name]
        key = f"{name}.yml"
        if not file_problems:
            changes.append(Change(CONFIG_RESOURCE, key, Action.NOOP, "valid"))
            continue
        messages = [f"{problem.path}: {problem.message}" for problem in file_problems]
        changes.append(
            Change(
                CONFIG_RESOURCE,
                key,
                Action.FAILED,
                "; ".join(messages),
                details={"problems": messages},
            )
        )
    return changes


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    args = build_parser().parse_args(argv)
    _configure_logging(args.verbose)

    if args.command != "validate" or args.repo is not None:
        print(f"project-bootstrap {args.command}: not implemented yet", file=sys.stderr)
        return EXIT_USAGE

    config_dir = resolve_config_dir(args.config)
    report = Report(
        command=args.command,
        mode="apply" if args.apply else "dry-run",
        target=config_dir.as_posix(),
        changes=validate_local(config_dir),
    )
    sys.stdout.write(render_json(report) if args.format == "json" else render_text(report))
    if args.report_file is not None:
        try:
            args.report_file.write_text(render_json(report), encoding="utf-8")
        except OSError as exc:
            print(f"cannot write report file {args.report_file}: {exc.strerror}", file=sys.stderr)
            return EXIT_FAILED
    return EXIT_FAILED if report.failed else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
