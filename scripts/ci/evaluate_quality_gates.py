"""Evaluate the quality gates of .project/quality-gates.yml against the jobs of a CI run.

The ``quality-gate`` job in ``.github/workflows/ci.yml`` runs this script after every other job
of the run. It is the single required status check: a pipeline is green only if this script
exits with ``0``.

Rules:

- A gate that applies passes only if every run of its job finished with ``success``. A skipped,
  cancelled, failed or missing job fails the gate.
- A gate that applies but is ``not_implemented`` fails.
- A gate that does not apply passes; the reason is printed.
- ``review_required_for_relevant_changes`` gates never fail the run. When they apply, they print
  a notice; the review policy enforces them.
- A failed or cancelled job of the run fails the evaluation even if no gate lists it.

When a gate applies is declared in ``applies_when`` in ``quality-gates.yml``, never in this
script. Job results are read from the JSON pages of the GitHub REST endpoint
``GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt}/jobs``.

Exit codes: 0 all gates passed, 1 a gate failed, 2 invalid input or configuration.
"""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import os
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

QUALITY_GATES_PATH = ".project/quality-gates.yml"
PROJECT_PATH = ".project/project.yml"
WORKFLOWS_DIR = ".github/workflows"
CI_WORKFLOW = "ci.yml"
EVALUATOR_JOB = "quality-gate"
SUPPORTED_SCHEMA = "1.1"

GATE_KINDS = (
    "required",
    "required_when_applicable",
    "required_for_code_changes",
    "review_required_for_relevant_changes",
)
REVIEW_KIND = "review_required_for_relevant_changes"
FAILED_CONCLUSIONS = frozenset(
    {"failure", "cancelled", "timed_out", "action_required", "startup_failure", "stale"}
)
ALL_ZERO_SHA = frozenset({"0" * 40, "0" * 64})

PASSED = "passed"
FAILED = "failed"
NOT_APPLICABLE = "not applicable"
REVIEW = "review required"


def _load_sibling(relative: str, name: str) -> ModuleType:
    """Load a module by path; ``python -I`` does not put the script directory on ``sys.path``."""
    path = Path(__file__).resolve().parent / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    # Dataclasses with postponed annotations look their module up in sys.modules.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


pr_validator = _load_sibling("pr_validation/validator.py", "pr_validator")


# Data


@dataclass(frozen=True)
class Conditions:
    """The ``applies_when`` conditions of a gate; ``None`` means the condition is not set."""

    events: tuple[str, ...] | None = None
    languages: tuple[str, ...] | None = None
    changed_paths: tuple[str, ...] | None = None
    ignored_paths: tuple[str, ...] | None = None


@dataclass(frozen=True)
class Gate:
    """One entry of ``quality_gates``."""

    name: str
    kind: str
    workflow: str
    job: str
    implemented: bool
    conditions: Conditions = Conditions()


@dataclass(frozen=True)
class FlakyTest:
    """A quarantined flaky test and the issue that tracks it."""

    test: str
    issue: str
    reason: str


@dataclass(frozen=True)
class Context:
    """The CI run the gates are evaluated for.

    ``changed_files`` is ``None`` when the changed files are unknown; path conditions then count
    as met, so an unknown change never makes a gate inapplicable.
    """

    event: str
    languages: tuple[str, ...] = ()
    changed_files: tuple[str, ...] | None = None


@dataclass(frozen=True)
class Job:
    """One job of the run as reported by the GitHub API."""

    name: str
    status: str
    conclusion: str | None

    @property
    def result(self) -> str:
        """The conclusion, or the status while the job has not completed."""
        return self.conclusion or self.status


@dataclass(frozen=True)
class GateResult:
    """The outcome for one gate, or for a failed job that no gate lists."""

    gate: str
    job: str
    outcome: str
    reason: str


# Configuration


def _strings(value: Any) -> tuple[str, ...] | None:
    return None if value is None else tuple(str(item) for item in value)


def load_gates(path: Path) -> tuple[list[Gate], list[FlakyTest]]:
    """Read ``quality-gates.yml``.

    The file is expected to be schema-valid; ``validate_project.py`` checks the schema.

    Raises:
        ValueError: If the schema version is not supported or a gate has no applicability key.
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be a mapping")  # noqa: TRY004 - input error
    version = data.get("schema_version")
    if version != SUPPORTED_SCHEMA:
        raise ValueError(
            f"{path}: schema_version {version!r} is not supported; migrate to "
            f"{SUPPORTED_SCHEMA!r} as described in .project/README.md#migrations"
        )
    gates = []
    for name, entry in data["quality_gates"].items():
        kinds = [kind for kind in GATE_KINDS if entry.get(kind) is True]
        if len(kinds) != 1:
            raise ValueError(
                f"{path}: gate {name!r} needs exactly one of {list(GATE_KINDS)}"
            )
        when = entry.get("applies_when") or {}
        gates.append(
            Gate(
                name=name,
                kind=kinds[0],
                workflow=entry["workflow"],
                job=entry["job"],
                implemented=entry["status"] == "implemented",
                conditions=Conditions(
                    events=_strings(when.get("events")),
                    languages=_strings(when.get("languages")),
                    changed_paths=_strings(when.get("changed_paths")),
                    ignored_paths=_strings(when.get("ignored_paths")),
                ),
            )
        )
    flaky = [
        FlakyTest(str(item["test"]), str(item["issue"]), str(item["reason"]))
        for item in data.get("flaky_tests") or []
    ]
    return gates, flaky


def load_languages(path: Path) -> tuple[str, ...]:
    """Read ``technology.languages`` from ``project.yml``; a missing file means no languages."""
    if not path.is_file():
        return ()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return tuple((data.get("technology") or {}).get("languages") or ())


def _job_display_name(job_id: str, job: Any) -> str:
    if isinstance(job, dict) and isinstance(job.get("name"), str):
        return job["name"]
    return job_id


def _workflow_jobs(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, dict):
        raise ValueError(f"{path}: no jobs")  # noqa: TRY004 - input error
    return jobs


def resolve_job_names(workflows_dir: Path) -> dict[tuple[str, str], str]:
    """Map ``(workflow file, job id)`` to the job name the GitHub API reports for this run.

    Jobs of ``ci.yml`` keep their own name. Jobs of a workflow that ``ci.yml`` calls as a
    reusable workflow are reported as ``<calling job name> / <job name>``.
    """
    names: dict[tuple[str, str], str] = {}
    for job_id, job in _workflow_jobs(workflows_dir / CI_WORKFLOW).items():
        caller = _job_display_name(job_id, job)
        uses = job.get("uses") if isinstance(job, dict) else None
        if isinstance(uses, str) and uses.startswith(f"./{WORKFLOWS_DIR}/"):
            called = uses.removeprefix(f"./{WORKFLOWS_DIR}/")
            for called_id, called_job in _workflow_jobs(workflows_dir / called).items():
                names[(called, called_id)] = (
                    f"{caller} / {_job_display_name(called_id, called_job)}"
                )
        else:
            names[(CI_WORKFLOW, job_id)] = caller
    return names


def parse_jobs(text: str) -> list[Job]:
    """Parse the job pages of the GitHub API.

    ``gh api --paginate`` writes one JSON object per page without separators; a single object or
    a JSON list of jobs is accepted as well.
    """
    decoder = json.JSONDecoder()
    position, items = 0, []
    while True:
        while position < len(text) and text[position].isspace():
            position += 1
        if position == len(text):
            break
        value, position = decoder.raw_decode(text, position)
        if isinstance(value, dict):
            items.extend(value.get("jobs", []))
        elif isinstance(value, list):
            items.extend(value)
        else:
            raise ValueError("job results must be JSON objects or lists")  # noqa: TRY004 - input error
    return [
        Job(str(item["name"]), str(item.get("status") or ""), item.get("conclusion"))
        for item in items
    ]


# Evaluation


def _matches(path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def inapplicable_reason(conditions: Conditions, context: Context) -> str | None:
    """Return why a gate does not apply, or ``None`` if every condition is met."""
    if conditions.events is not None and context.event not in conditions.events:
        return f"event {context.event!r} is not one of {list(conditions.events)}"
    if conditions.languages is not None:
        if "*" in conditions.languages:
            if not context.languages:
                return "project.yml lists no technology.languages"
        elif not set(conditions.languages) & set(context.languages):
            return (
                f"none of the languages {list(conditions.languages)} is in project.yml"
            )
    path_condition = (
        conditions.changed_paths is not None or conditions.ignored_paths is not None
    )
    if path_condition and context.changed_files is not None:
        relevant = [
            path
            for path in context.changed_files
            if not _matches(path, conditions.ignored_paths or ())
        ]
        if conditions.changed_paths is not None:
            relevant = [
                path for path in relevant if _matches(path, conditions.changed_paths)
            ]
        if not relevant:
            return "no relevant file changed"
    return None


def _job_runs(jobs: Sequence[Job], name: str) -> list[Job]:
    """Return the runs of a job, including matrix runs named ``<name> (<values>)``."""
    return [job for job in jobs if job.name == name or job.name.startswith(f"{name} (")]


def evaluate_gate(
    gate: Gate,
    context: Context,
    jobs: Sequence[Job],
    names: Mapping[tuple[str, str], str],
) -> GateResult:
    """Evaluate one gate."""
    expected = names.get((gate.workflow, gate.job), gate.job)
    reason = inapplicable_reason(gate.conditions, context)
    if reason is not None:
        return GateResult(gate.name, expected, NOT_APPLICABLE, reason)
    if gate.kind == REVIEW_KIND:
        return GateResult(
            gate.name, expected, REVIEW, "relevant changes need reviewer attention"
        )
    if not gate.implemented:
        return GateResult(
            gate.name,
            expected,
            FAILED,
            f"gate {gate.name} is required but not implemented",
        )
    if (gate.workflow, gate.job) not in names:
        return GateResult(
            gate.name,
            expected,
            FAILED,
            f"job {gate.job!r} of {gate.workflow} is not part of {CI_WORKFLOW}; "
            "call the workflow from ci.yml or correct quality-gates.yml",
        )
    runs = _job_runs(jobs, expected)
    if not runs:
        return GateResult(gate.name, expected, FAILED, "the job did not run")
    bad = [run for run in runs if run.result != "success"]
    if bad:
        # Matrix variants are named "<job> (<values>)"; only they need the name in the reason.
        results = ", ".join(
            run.result if run.name == expected else f"{run.name}: {run.result}"
            for run in bad
        )
        return GateResult(gate.name, expected, FAILED, f"job result: {results}")
    return GateResult(gate.name, expected, PASSED, "success")


def evaluate(
    gates: Sequence[Gate],
    context: Context,
    jobs: Sequence[Job],
    names: Mapping[tuple[str, str], str],
) -> list[GateResult]:
    """Evaluate every gate, then add every failed job that no failed gate already reports."""
    results = [evaluate_gate(gate, context, jobs, names) for gate in gates]
    reported = {
        run.name
        for result in results
        if result.outcome == FAILED
        for run in _job_runs(jobs, result.job)
    }
    for job in jobs:
        if job.name == EVALUATOR_JOB or job.name in reported:
            continue
        if job.conclusion in FAILED_CONCLUSIONS:
            results.append(
                GateResult(
                    "(no gate)", job.name, FAILED, f"job result: {job.conclusion}"
                )
            )
    return results


# Input


def changed_files_from_event(
    repo: Path, event_name: str, event_path: Path
) -> tuple[str, ...] | None:
    """Read the changed files of a ``pull_request`` or ``push`` event.

    Returns ``None`` if they cannot be determined, for example for the first push of a branch.
    """
    event = json.loads(event_path.read_text(encoding="utf-8"))
    if event_name == "pull_request":
        _, revision_range = pr_validator.read_event(event_path)
    elif event_name == "push":
        before, after = event.get("before"), event.get("after")
        valid = pr_validator.COMMIT_ID_PATTERN.match
        if not (isinstance(before, str) and isinstance(after, str)):
            return None
        if before in ALL_ZERO_SHA or not (valid(before) and valid(after)):
            return None
        revision_range = f"{before}..{after}"
    else:
        return None
    return tuple(pr_validator.read_changed_files(repo, revision_range))


def head_sha(event_name: str, event_path: Path | None) -> str:
    """Return the tested commit: the head of a pull request, otherwise ``GITHUB_SHA``."""
    if event_name == "pull_request" and event_path is not None:
        event = json.loads(event_path.read_text(encoding="utf-8"))
        return str(event["pull_request"]["head"]["sha"])
    return os.environ.get("GITHUB_SHA", "unknown")


# Output


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def report(
    results: Sequence[GateResult],
    flaky: Sequence[FlakyTest],
    sha: str,
    run_id: str,
) -> int:
    """Print the results and append a table to the GitHub job summary.

    Returns:
        1 if a gate or job failed, otherwise 0.
    """
    failed = [result for result in results if result.outcome == FAILED]
    for result in results:
        if result.outcome == FAILED:
            print(f"error: [{result.gate}] {result.job}: {result.reason}")
        elif result.outcome == REVIEW:
            print(
                f"::notice title=Review required::gate {result.gate}: {result.reason}"
            )
        else:
            print(f"{result.outcome}: [{result.gate}] {result.job}: {result.reason}")
    for test in flaky:
        print(f"quarantined flaky test: {test.test} ({test.issue}): {test.reason}")
    print(f"Quality gates for {sha} in run {run_id}: {len(failed)} failed")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        lines = [
            "## Quality gates",
            "",
            f"Commit `{sha}`, run `{run_id}`: "
            + ("**failed**" if failed else "all required gates passed"),
            "",
            "| Gate | Job | Result | Reason |",
            "|---|---|---|---|",
        ]
        lines += [
            f"| {_cell(r.gate)} | {_cell(r.job)} | {r.outcome} | {_cell(r.reason)} |"
            for r in results
        ]
        if flaky:
            lines += [
                "",
                "### Quarantined flaky tests",
                "",
                "| Test | Issue | Reason |",
            ]
            lines += ["|---|---|---|"]
            lines += [
                f"| {_cell(t.test)} | {_cell(t.issue)} | {_cell(t.reason)} |"
                for t in flaky
            ]
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write("\n".join(lines) + "\n")
    return 1 if failed else 0


def _parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--repo", type=Path, default=Path("."), help="repository root")
    parser.add_argument(
        "--jobs", type=Path, required=True, help="JSON job results of the run"
    )
    parser.add_argument(
        "--event-name",
        default=os.environ.get("GITHUB_EVENT_NAME"),
        help="triggering event, default GITHUB_EVENT_NAME",
    )
    changes = parser.add_mutually_exclusive_group()
    changes.add_argument(
        "--event", type=Path, help="event JSON file, to find changed files"
    )
    changes.add_argument("--range", help="BASE..HEAD, to find changed files")
    parser.add_argument(
        "--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"), help="CI run id"
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface."""
    args = _parse_arguments(argv)
    repo = args.repo
    try:
        if not args.event_name:
            raise ValueError("pass --event-name or set GITHUB_EVENT_NAME")
        gates, flaky = load_gates(repo / QUALITY_GATES_PATH)
        names = resolve_job_names(repo / WORKFLOWS_DIR)
        if args.event is not None:
            changed = changed_files_from_event(repo, args.event_name, args.event)
        elif args.range is not None:
            changed = tuple(pr_validator.read_changed_files(repo, args.range))
        else:
            changed = None
        context = Context(args.event_name, load_languages(repo / PROJECT_PATH), changed)
        jobs = parse_jobs(args.jobs.read_text(encoding="utf-8"))
        results = evaluate(gates, context, jobs, names)
        return report(
            results, flaky, head_sha(args.event_name, args.event), args.run_id
        )
    except (
        OSError,
        KeyError,
        TypeError,
        ValueError,
        RuntimeError,
        yaml.YAMLError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
