"""Tests for scripts/ci/evaluate_quality_gates.py.

Several tests evaluate the repository's own quality-gates.yml and workflows, so they fail if the
configuration, the workflows and the evaluator drift apart.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "evaluate_quality_gates", ROOT / "scripts" / "ci" / "evaluate_quality_gates.py"
)
evaluator = importlib.util.module_from_spec(_spec)
sys.modules["evaluate_quality_gates"] = evaluator
_spec.loader.exec_module(evaluator)

Gate = evaluator.Gate
Conditions = evaluator.Conditions
Context = evaluator.Context
Job = evaluator.Job

NAMES = {("ci.yml", "build"): "build", ("quality.yml", "lint"): "quality / lint"}
PULL_REQUEST = Context("pull_request", ("python",), ("src/app.py",))


@pytest.fixture(autouse=True)
def _isolate_github_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests from writing into the real job summary when they run in CI."""
    for name in (
        "GITHUB_STEP_SUMMARY",
        "GITHUB_EVENT_NAME",
        "GITHUB_RUN_ID",
        "GITHUB_SHA",
    ):
        monkeypatch.delenv(name, raising=False)


def _success(name: str) -> Job:
    return Job(name, "completed", "success")


def _gate(**overrides: object) -> Gate:
    values: dict[str, object] = {
        "name": "build",
        "kind": "required",
        "workflow": "ci.yml",
        "job": "build",
        "implemented": True,
    }
    values.update(overrides)
    return Gate(**values)


def _outcome(
    gate: Gate, jobs: list[Job], context: Context = PULL_REQUEST
) -> tuple[str, str]:
    result = evaluator.evaluate_gate(gate, context, jobs, NAMES)
    return result.outcome, result.reason


# Required gates (R1)


def test_required_gate_passes_only_with_success() -> None:
    assert _outcome(_gate(), [_success("build")])[0] == evaluator.PASSED


@pytest.mark.parametrize("conclusion", ["skipped", "failure", "cancelled", "neutral"])
def test_required_gate_fails_for_other_results(conclusion: str) -> None:
    outcome, reason = _outcome(_gate(), [Job("build", "completed", conclusion)])
    assert outcome == evaluator.FAILED
    assert reason == f"job result: {conclusion}"


def test_required_build_not_executed_fails() -> None:
    """§21.6: a required build that did not run fails the pipeline."""
    assert _outcome(_gate(), []) == (evaluator.FAILED, "the job did not run")


def test_job_still_running_fails() -> None:
    outcome, reason = _outcome(_gate(), [Job("build", "in_progress", None)])
    assert outcome == evaluator.FAILED
    assert "in_progress" in reason


def test_every_matrix_run_must_succeed() -> None:
    jobs = [_success("build (3.12)"), Job("build (3.13)", "completed", "failure")]
    outcome, reason = _outcome(_gate(), jobs)
    assert outcome == evaluator.FAILED
    assert "build (3.13): failure" in reason
    assert (
        _outcome(_gate(), [_success("build (3.12)"), _success("build (3.13)")])[0]
        == "passed"
    )


def test_job_of_called_workflow_is_matched_by_caller_name() -> None:
    gate = _gate(name="lint", workflow="quality.yml", job="lint")
    assert _outcome(gate, [_success("lint")])[0] == evaluator.FAILED
    assert _outcome(gate, [_success("quality / lint")])[0] == evaluator.PASSED


def test_implemented_gate_outside_ci_fails_with_hint() -> None:
    outcome, reason = _outcome(_gate(workflow="other.yml"), [_success("build")])
    assert outcome == evaluator.FAILED
    assert "not part of ci.yml" in reason


# Applicability (R2, R4)


def test_not_applicable_gate_passes_with_reason() -> None:
    gate = _gate(
        kind="required_when_applicable", conditions=Conditions(languages=("*",))
    )
    outcome, reason = _outcome(gate, [], Context("push"))
    assert outcome == evaluator.NOT_APPLICABLE
    assert reason == "project.yml lists no technology.languages"


def test_applicable_gate_that_was_skipped_fails() -> None:
    gate = _gate(
        kind="required_when_applicable", conditions=Conditions(languages=("*",))
    )
    jobs = [Job("build", "completed", "skipped")]
    assert _outcome(gate, jobs)[0] == evaluator.FAILED


@pytest.mark.parametrize(
    ("conditions", "context", "applies"),
    [
        (Conditions(events=("pull_request",)), Context("pull_request"), True),
        (Conditions(events=("pull_request",)), Context("push"), False),
        (Conditions(languages=("python",)), Context("push", ("python", "cpp")), True),
        (Conditions(languages=("python",)), Context("push", ("cpp",)), False),
        (Conditions(languages=("*",)), Context("push", ("cpp",)), True),
        (
            Conditions(changed_paths=("docs/*",)),
            Context("push", (), ("docs/a/b.md",)),
            True,
        ),
        (
            Conditions(changed_paths=("docs/*",)),
            Context("push", (), ("src/a.py",)),
            False,
        ),
        (
            Conditions(ignored_paths=("*.md",)),
            Context("push", (), ("README.md",)),
            False,
        ),
        (
            Conditions(ignored_paths=("*.md",)),
            Context("push", (), ("README.md", "a.py")),
            True,
        ),
        (
            Conditions(changed_paths=("src/*",), ignored_paths=("src/*.md",)),
            Context("push", (), ("src/notes.md",)),
            False,
        ),
        (Conditions(changed_paths=("src/*",)), Context("push", (), ()), False),
        # Unknown changed files never make a gate inapplicable.
        (Conditions(changed_paths=("src/*",)), Context("push", (), None), True),
    ],
)
def test_applicability_conditions(
    conditions: object, context: Context, applies: bool
) -> None:
    assert (evaluator.inapplicable_reason(conditions, context) is None) is applies


def test_all_conditions_must_hold() -> None:
    conditions = Conditions(events=("pull_request",), languages=("python",))
    assert (
        evaluator.inapplicable_reason(conditions, Context("pull_request", ("python",)))
        is None
    )
    reason = evaluator.inapplicable_reason(
        conditions, Context("pull_request", ("cpp",))
    )
    assert "languages" in reason


# Not implemented (R3) and review gates


def test_required_gate_not_implemented_fails() -> None:
    gate = _gate(name="lint", implemented=False)
    outcome, reason = _outcome(gate, [_success("build")])
    assert outcome == evaluator.FAILED
    assert reason == "gate lint is required but not implemented"


def test_applicable_gate_not_implemented_fails() -> None:
    gate = _gate(
        kind="required_for_code_changes",
        implemented=False,
        conditions=Conditions(languages=("*",)),
    )
    assert _outcome(gate, [])[0] == evaluator.FAILED


def test_not_applicable_gate_not_implemented_passes() -> None:
    gate = _gate(implemented=False, conditions=Conditions(events=("issues",)))
    assert _outcome(gate, [])[0] == evaluator.NOT_APPLICABLE


def test_review_gate_never_fails() -> None:
    gate = _gate(
        kind=evaluator.REVIEW_KIND,
        implemented=False,
        conditions=Conditions(changed_paths=("*.md",)),
    )
    assert (
        _outcome(gate, [], Context("pull_request", (), ("README.md",)))[0]
        == evaluator.REVIEW
    )
    assert (
        _outcome(gate, [], Context("pull_request", (), ("a.py",)))[0]
        == "not applicable"
    )


# Jobs that no gate lists


def test_failed_job_without_gate_fails_the_evaluation() -> None:
    jobs = [_success("build"), Job("extra", "completed", "failure")]
    results = evaluator.evaluate([_gate()], PULL_REQUEST, jobs, NAMES)
    assert [(r.gate, r.job, r.outcome) for r in results] == [
        ("build", "build", "passed"),
        ("(no gate)", "extra", "failed"),
    ]


def test_failed_job_of_failed_gate_is_reported_once() -> None:
    jobs = [Job("build", "completed", "failure")]
    results = evaluator.evaluate([_gate()], PULL_REQUEST, jobs, NAMES)
    assert [r.outcome for r in results] == ["failed"]


def test_skipped_job_without_gate_and_evaluator_job_are_ignored() -> None:
    jobs = [_success("build"), Job("extra", "completed", "skipped")]
    jobs.append(Job(evaluator.EVALUATOR_JOB, "in_progress", None))
    results = evaluator.evaluate([_gate()], PULL_REQUEST, jobs, NAMES)
    assert [r.outcome for r in results] == ["passed"]


def test_failed_job_of_inapplicable_gate_still_fails() -> None:
    gate = _gate(conditions=Conditions(events=("push",)))
    results = evaluator.evaluate(
        [gate], PULL_REQUEST, [Job("build", "completed", "failure")], NAMES
    )
    assert [r.outcome for r in results] == ["not applicable", "failed"]


# Input parsing


def test_parse_jobs_reads_concatenated_api_pages() -> None:
    pages = (
        '{"total_count": 2, "jobs": [{"name": "a", "status": "completed", "conclusion": "success"}]}'
        '\n{"total_count": 2, "jobs": [{"name": "b", "status": "queued", "conclusion": null}]}\n'
    )
    assert evaluator.parse_jobs(pages) == [
        Job("a", "completed", "success"),
        Job("b", "queued", None),
    ]
    assert evaluator.parse_jobs('[{"name": "a", "status": "completed"}]') == [
        Job("a", "completed", None)
    ]


def test_parse_jobs_rejects_other_json() -> None:
    with pytest.raises(ValueError, match="JSON objects or lists"):
        evaluator.parse_jobs("42")


def test_resolve_job_names_of_repository_workflows() -> None:
    names = evaluator.resolve_job_names(ROOT / ".github" / "workflows")
    assert names[("ci.yml", "repository-validation")] == "repository-validation"
    assert names[("quality.yml", "workflow-lint")] == "quality / workflow-lint"
    assert names[("security.yml", "secret-scan")] == "security / secret-scan"
    assert names[("pr-validation.yml", "commitlint")] == "pull-request / commitlint"


def test_load_gates_rejects_schema_1_0(tmp_path: Path) -> None:
    path = tmp_path / "quality-gates.yml"
    path.write_text(
        'schema_version: "1.0"\nquality_gates:\n  a:\n    required: true\n'
        '    workflow: "ci.yml"\n    job: "a"\n    status: "implemented"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="migrate to '1.1'"):
        evaluator.load_gates(path)


def test_load_gates_reads_flaky_tests(tmp_path: Path) -> None:
    data = yaml.safe_load(
        (ROOT / evaluator.QUALITY_GATES_PATH).read_text(encoding="utf-8")
    )
    data["flaky_tests"] = [
        {"test": "tests/test_a.py::test_b", "issue": "#7", "reason": "timing"}
    ]
    path = tmp_path / "quality-gates.yml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    _, flaky = evaluator.load_gates(path)
    assert flaky == [evaluator.FlakyTest("tests/test_a.py::test_b", "#7", "timing")]


# Repository configuration


def _repository_jobs(conclusion: str = "success") -> list[dict[str, str]]:
    """One job per implemented gate of the repository's quality-gates.yml."""
    gates, _ = evaluator.load_gates(ROOT / evaluator.QUALITY_GATES_PATH)
    names = evaluator.resolve_job_names(ROOT / ".github" / "workflows")
    return [
        {
            "name": names[(g.workflow, g.job)],
            "status": "completed",
            "conclusion": conclusion,
        }
        for g in gates
        if g.implemented and g.kind != evaluator.REVIEW_KIND
    ]


def test_every_implemented_gate_is_a_job_of_the_ci_run() -> None:
    gates, _ = evaluator.load_gates(ROOT / evaluator.QUALITY_GATES_PATH)
    names = evaluator.resolve_job_names(ROOT / ".github" / "workflows")
    missing = [
        g.name for g in gates if g.implemented and (g.workflow, g.job) not in names
    ]
    assert missing == []


@pytest.mark.parametrize(("event", "expected"), [("pull_request", 0), ("push", 0)])
def test_repository_gates_pass_when_all_jobs_succeed(
    tmp_path: Path, event: str, expected: int
) -> None:
    jobs = tmp_path / "jobs.json"
    jobs.write_text(json.dumps({"jobs": _repository_jobs()}), encoding="utf-8")
    code = evaluator.main(
        ["--repo", str(ROOT), "--jobs", str(jobs), "--event-name", event]
    )
    assert code == expected


def test_repository_gates_fail_when_a_required_job_is_skipped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    items = _repository_jobs()
    items[0]["conclusion"] = "skipped"
    jobs = tmp_path / "jobs.json"
    jobs.write_text(json.dumps({"jobs": items}), encoding="utf-8")
    code = evaluator.main(
        ["--repo", str(ROOT), "--jobs", str(jobs), "--event-name", "push"]
    )
    assert code == 1
    assert f"{items[0]['name']}: job result: skipped" in capsys.readouterr().out


def test_repository_gates_fail_when_a_language_is_set(tmp_path: Path) -> None:
    """Once a stack is declared, its not-implemented gates fail instead of passing silently."""
    shutil.copytree(ROOT / ".project", tmp_path / ".project")
    shutil.copytree(ROOT / ".github" / "workflows", tmp_path / ".github" / "workflows")
    project = tmp_path / evaluator.PROJECT_PATH
    data = yaml.safe_load(project.read_text(encoding="utf-8"))
    data["technology"]["languages"] = ["python"]
    project.write_text(yaml.safe_dump(data), encoding="utf-8")
    jobs = tmp_path / "jobs.json"
    jobs.write_text(json.dumps({"jobs": _repository_jobs()}), encoding="utf-8")
    code = evaluator.main(
        ["--repo", str(tmp_path), "--jobs", str(jobs), "--event-name", "push"]
    )
    assert code == 1


# Command line and summary


def _git(repo: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *arguments], capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    shutil.copytree(ROOT / ".project", tmp_path / ".project")
    shutil.copytree(ROOT / ".github" / "workflows", tmp_path / ".github" / "workflows")
    _git(tmp_path, "init", "-q", "-b", "develop")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "chore: initial commit")
    return tmp_path


def test_cli_reads_changed_files_from_push_event_and_writes_summary(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = _git(repo, "rev-parse", "HEAD")
    (repo / "docs").mkdir()
    (repo / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "docs: add guide")
    after = _git(repo, "rev-parse", "HEAD")
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"before": before, "after": after}), encoding="utf-8")
    jobs = tmp_path / "jobs.json"
    jobs.write_text(json.dumps({"jobs": _repository_jobs()}), encoding="utf-8")
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("GITHUB_SHA", after)

    code = evaluator.main(
        [
            "--repo",
            str(repo),
            "--jobs",
            str(jobs),
            "--event-name",
            "push",
            "--event",
            str(event),
            "--run-id",
            "4711",
        ]
    )

    assert code == 0
    text = summary.read_text(encoding="utf-8")
    assert f"Commit `{after}`, run `4711`" in text
    assert "| issue_validation | issue-validation | not applicable |" in text
    assert "| tests | test | not applicable |" in text


def test_cli_treats_first_push_as_unknown_changes(repo: Path, tmp_path: Path) -> None:
    event = tmp_path / "event.json"
    event.write_text(
        json.dumps({"before": "0" * 40, "after": _git(repo, "rev-parse", "HEAD")}),
        encoding="utf-8",
    )
    assert evaluator.changed_files_from_event(repo, "push", event) is None


def test_cli_reports_invalid_input(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    jobs = tmp_path / "jobs.json"
    jobs.write_text("not json", encoding="utf-8")
    code = evaluator.main(
        ["--repo", str(ROOT), "--jobs", str(jobs), "--event-name", "push"]
    )
    assert code == 2
    assert capsys.readouterr().err.startswith("error: ")


def test_cli_requires_an_event_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    jobs = tmp_path / "jobs.json"
    jobs.write_text("[]", encoding="utf-8")
    assert evaluator.main(["--repo", str(ROOT), "--jobs", str(jobs)]) == 2
    assert "--event-name" in capsys.readouterr().err


def test_cli_runs_isolated_from_the_command_line(tmp_path: Path) -> None:
    jobs = tmp_path / "jobs.json"
    jobs.write_text(json.dumps({"jobs": _repository_jobs()}), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(ROOT / "scripts" / "ci" / "evaluate_quality_gates.py"),
            "--repo",
            str(ROOT),
            "--jobs",
            str(jobs),
            "--event-name",
            "push",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "0 failed" in result.stdout
