"""Command line interface ``project-bootstrap``.

Every command runs as a dry run unless ``--apply`` is given. Exit codes:

- ``0``: the run succeeded.
- ``1``: a change failed, the configuration is invalid, no token is available, or
  ``apply-rulesets`` found an unprotected repository without ``--allow-unprotected``.
- ``2``: invalid usage, an unconfirmed prune, or a command that is not implemented yet.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from collections.abc import Sequence
from pathlib import Path

import httpx

from engineering_bootstrap import __version__
from engineering_bootstrap.config import (
    CONFIG_NAMES,
    ConfigError,
    ProjectConfig,
    load_config,
    resolve_config_dir,
    validate_config,
)
from engineering_bootstrap.engine import Action, Change, Engine
from engineering_bootstrap.github import (
    AuthenticationError,
    GitHubClient,
    RedactingFilter,
    install_redaction,
    resolve_token,
)
from engineering_bootstrap.report import Report, render_json, render_text
from engineering_bootstrap.resources.branches import BranchResource, spec_from_config
from engineering_bootstrap.resources.labels import LabelResource, specs_from_config
from engineering_bootstrap.resources.repo_settings import (
    RepoSettingsResource,
    settings_from_config,
)
from engineering_bootstrap.resources.rulesets import RulesetResource, rulesets_from_config

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
DEFAULT_CONFIG = Path(".project/bootstrap.yml")
CONFIG_RESOURCE = "config"
# OWNER/NAME as GitHub allows them; also keeps the value from changing the API path.
REPO_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}")


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
        "sync-labels", parents=[common], help="make the repository labels match labels.yml"
    )
    sync.add_argument("--repo", required=True, metavar="OWNER/NAME")
    sync.add_argument(
        "--prune",
        action="store_true",
        help="delete labels that are not in labels.yml; requires --apply and confirmation",
    )
    sync.add_argument(
        "--yes", action="store_true", help="confirm --prune without asking, e.g. in CI"
    )

    configure = commands.add_parser(
        "configure-repo",
        parents=[common],
        help="create the development branch and apply the repository settings",
    )
    configure.add_argument("--repo", required=True, metavar="OWNER/NAME")

    rulesets = commands.add_parser(
        "apply-rulesets",
        parents=[common],
        help="protect the default and development branch and the release tags with rulesets",
    )
    rulesets.add_argument("--repo", required=True, metavar="OWNER/NAME")
    rulesets.add_argument(
        "--allow-unprotected",
        action="store_true",
        help="exit with 0 even if GitHub offers no rulesets for the repository",
    )

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


def _confirm_prune(deletions: list[Change], args: argparse.Namespace) -> bool:
    """List the labels that prune deletes and ask for confirmation."""
    print(f"--prune deletes {len(deletions)} label(s) from {args.repo}:", file=sys.stderr)
    for change in deletions:
        print(f"  {change.key}: {change.reason}", file=sys.stderr)
    if args.yes:
        return True
    if args.format != "text" or not sys.stdin.isatty():
        print("confirm the deletion with --yes", file=sys.stderr)
        return False
    answer = input(f"Delete {len(deletions)} label(s)? [y/N] ")
    return answer.strip().lower() in {"y", "yes"}


def _prepare_remote(args: argparse.Namespace) -> tuple[ProjectConfig, str] | int:
    """Check ``--repo``, load the configuration and resolve the token, or return an exit code."""
    if not REPO_PATTERN.fullmatch(args.repo):
        print(f"invalid --repo {args.repo!r}; expected OWNER/NAME", file=sys.stderr)
        return EXIT_USAGE
    try:
        config = load_config(resolve_config_dir(args.config))
    except ConfigError as exc:
        for problem in exc.problems:
            print(f"invalid configuration: {problem}", file=sys.stderr)
        return EXIT_FAILED
    try:
        token = resolve_token()
    except AuthenticationError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_FAILED
    install_redaction(token)
    return config, token


def _sync_labels(args: argparse.Namespace, transport: httpx.BaseTransport | None) -> Report | int:
    if args.prune and not args.apply:
        print("--prune requires --apply", file=sys.stderr)
        return EXIT_USAGE
    prepared = _prepare_remote(args)
    if isinstance(prepared, int):
        return prepared
    config, token = prepared

    with GitHubClient(token, transport=transport) as client:
        resource = LabelResource(
            client, args.repo, specs_from_config(config.files["labels"]), prune=args.prune
        )
        engine = Engine([resource], allow_destructive=args.prune)
        if args.prune:
            deletions = [c for c in engine.run(apply=False) if c.action is Action.DELETE]
            if deletions and not _confirm_prune(deletions, args):
                print("prune not confirmed; nothing was changed", file=sys.stderr)
                return EXIT_USAGE
        changes = engine.run(apply=args.apply)
    return Report(
        command=args.command,
        mode="apply" if args.apply else "dry-run",
        target=args.repo,
        changes=changes,
    )


def _configure_repo(
    args: argparse.Namespace, transport: httpx.BaseTransport | None
) -> Report | int:
    prepared = _prepare_remote(args)
    if isinstance(prepared, int):
        return prepared
    config, token = prepared
    try:
        settings = settings_from_config(config.files)
    except ValueError as exc:
        print(f"invalid configuration: {exc}", file=sys.stderr)
        return EXIT_FAILED

    with GitHubClient(token, transport=transport) as client:
        resources = [
            BranchResource(
                client,
                args.repo,
                spec_from_config(config.files["project"]),
                create_development_branch=config.bootstrap["create_develop_branch"],
            ),
            RepoSettingsResource(client, args.repo, settings),
        ]
        changes = Engine(resources).run(apply=args.apply)
    return Report(
        command=args.command,
        mode="apply" if args.apply else "dry-run",
        target=args.repo,
        changes=changes,
    )


def _apply_rulesets(
    args: argparse.Namespace, transport: httpx.BaseTransport | None
) -> Report | int:
    prepared = _prepare_remote(args)
    if isinstance(prepared, int):
        return prepared
    config, token = prepared
    try:
        specs = rulesets_from_config(config.files)
    except ValueError as exc:
        print(f"invalid configuration: {exc}", file=sys.stderr)
        return EXIT_FAILED

    with GitHubClient(token, transport=transport) as client:
        resource = RulesetResource(
            client, args.repo, specs, allow_unprotected=args.allow_unprotected
        )
        changes = Engine([resource]).run(apply=args.apply)
    return Report(
        command=args.command,
        mode="apply" if args.apply else "dry-run",
        target=args.repo,
        changes=changes,
    )


def _emit(report: Report, args: argparse.Namespace) -> int:
    sys.stdout.write(render_json(report) if args.format == "json" else render_text(report))
    if args.report_file is not None:
        try:
            args.report_file.write_text(render_json(report), encoding="utf-8")
        except OSError as exc:
            print(f"cannot write report file {args.report_file}: {exc.strerror}", file=sys.stderr)
            return EXIT_FAILED
    return EXIT_FAILED if report.failed else EXIT_OK


def main(argv: Sequence[str] | None = None, *, transport: httpx.BaseTransport | None = None) -> int:
    """Run the CLI and return the exit code.

    Args:
        argv: Command line arguments; defaults to ``sys.argv[1:]``.
        transport: httpx transport for the GitHub client; tests pass a mock.
    """
    args = build_parser().parse_args(argv)
    _configure_logging(args.verbose)

    remote_commands = {
        "sync-labels": _sync_labels,
        "configure-repo": _configure_repo,
        "apply-rulesets": _apply_rulesets,
    }
    if args.command in remote_commands:
        result = remote_commands[args.command](args, transport)
        return result if isinstance(result, int) else _emit(result, args)

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
    return _emit(report, args)


if __name__ == "__main__":
    sys.exit(main())
