"""Tests for scripts/ci/pr_validation/validator.py.

The rules and the pull request template are the repository's own files, so the tests fail if the
configuration and the validator drift apart.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "pr_validator", ROOT / "scripts" / "ci" / "pr_validation" / "validator.py"
)
validator = importlib.util.module_from_spec(_spec)
sys.modules["pr_validator"] = validator
_spec.loader.exec_module(validator)

RULES = validator.load_rules(ROOT)
TEMPLATE = (ROOT / validator.TEMPLATE_PATH).read_text(encoding="utf-8")

FILLED_BODY = """\
## Summary

Adds document cropping.

## Related Issues

Refs: #42

## Validation

- [x] Applicable tests were executed.

### Tests Executed

~~~text
python -I -m pytest tests -> 12 passed
~~~
"""


def make_pr(**changes: str) -> object:
    pr = validator.PullRequest(
        title="feat(scanner): add document cropping",
        body=FILLED_BODY,
        head_ref="feature/42-document-cropping",
        base_ref="develop",
        author="octocat",
    )
    return replace(pr, **changes)


def rules_of(findings: list) -> list[str]:
    return [finding.rule for finding in findings]


def test_complete_pull_request_passes() -> None:
    assert validator.check_pull_request(make_pr(), RULES, TEMPLATE) == []


# §21.6 cases and the target matrix


def test_feature_branch_into_main_fails() -> None:
    findings = validator.check_pull_request(make_pr(base_ref="main"), RULES, TEMPLATE)
    assert rules_of(findings) == ["target-branch"]
    assert "feature/ branches must target 'develop', not 'main'" in findings[0].message


def test_release_from_develop_into_main_passes() -> None:
    pr = make_pr(
        head_ref="develop", base_ref="main", title="chore(release): merge develop"
    )
    assert validator.check_pull_request(pr, RULES, TEMPLATE) == []


def test_invalid_title_fails() -> None:
    findings = validator.check_pull_request(
        make_pr(title="Add cropping"), RULES, TEMPLATE
    )
    assert rules_of(findings) == ["title"]
    assert "edit the pull request title" in findings[0].hint


@pytest.mark.parametrize(
    ("head_ref", "base_ref"),
    [
        ("fix/7-null-pointer", "develop"),
        ("chore/8-update-docs", "develop"),
        ("hotfix/9-crash-on-start", "main"),
        ("release/1.2.0", "main"),
        ("main", "develop"),
    ],
)
def test_allowed_targets_pass(head_ref: str, base_ref: str) -> None:
    assert (
        validator.check_target(make_pr(head_ref=head_ref, base_ref=base_ref), RULES)
        == []
    )


@pytest.mark.parametrize(
    ("head_ref", "base_ref", "expected"),
    [
        ("hotfix/9-crash-on-start", "develop", "hotfix/ branches must target 'main'"),
        ("release/1.2.0", "develop", "release/ branches must target 'main'"),
        ("fix/7-null-pointer", "main", "fix/ branches must target 'develop'"),
        ("feature/42-x", "feature/41-y", "not 'feature/41-y'"),
        ("experiment/1-try", "develop", "has no known branch type"),
        ("topic", "develop", "has no known branch type"),
    ],
)
def test_disallowed_targets_fail(head_ref: str, base_ref: str, expected: str) -> None:
    findings = validator.check_target(
        make_pr(head_ref=head_ref, base_ref=base_ref), RULES
    )
    assert rules_of(findings) == ["target-branch"]
    assert expected in findings[0].message


# Branch names


@pytest.mark.parametrize(
    "head_ref", ["feature/document-cropping", "feature/42_Cropping", "feature/42"]
)
def test_invalid_branch_name_fails(head_ref: str) -> None:
    findings = validator.check_branch_name(make_pr(head_ref=head_ref), RULES)
    assert rules_of(findings) == ["branch-name"]


def test_branch_without_issue_number_passes_with_no_issue_reason() -> None:
    body = FILLED_BODY.replace("Refs: #42", "No-Issue: typo fix in the README")
    pr = make_pr(head_ref="chore/fix-readme-typo", body=body)
    assert validator.check_pull_request(pr, RULES, TEMPLATE) == []


# Issue links


@pytest.mark.parametrize(
    "link",
    [
        "Refs: #42",
        "Closes #42",
        "fixes #42",
        "Resolves: octo/demo#42",
        "Refs: https://github.com/octo/demo/issues/42",
    ],
)
def test_issue_link_forms_are_accepted(link: str) -> None:
    pr = make_pr(body=FILLED_BODY.replace("Refs: #42", link))
    assert validator.check_issue_link(pr, RULES) == []


@pytest.mark.parametrize(
    ("related", "expected"),
    [
        ("Refs: #<issue-number>", "does not link an issue"),
        ("<!-- Refs: #42 -->\nSee the discussion.", "does not link an issue"),
        ("Prefix#42", "does not link an issue"),
        ("No-Issue:", "has no reason"),
        ("No-Issue: <reason>", "has no reason"),
    ],
)
def test_missing_issue_link_fails(related: str, expected: str) -> None:
    pr = make_pr(body=FILLED_BODY.replace("Refs: #42", related))
    findings = validator.check_issue_link(pr, RULES)
    assert rules_of(findings) == ["issue-link"]
    assert expected in findings[0].message


# Template sections


def test_unchanged_template_fails_every_required_section() -> None:
    findings = validator.check_sections(make_pr(body=TEMPLATE), RULES, TEMPLATE)
    assert [f.message for f in findings] == [
        f"section {name!r} still contains only the template text"
        for name in RULES.required_sections
    ]


def test_missing_and_empty_sections_fail() -> None:
    body = FILLED_BODY.replace("## Summary\n\nAdds document cropping.\n", "").replace(
        "python -I -m pytest tests -> 12 passed\n", ""
    )
    findings = validator.check_sections(make_pr(body=body), RULES, TEMPLATE)
    assert [f.message for f in findings] == [
        "section 'Summary' is missing",
        "section 'Tests Executed' is empty",
    ]


def test_heading_inside_code_fence_is_not_a_section() -> None:
    sections = validator.parse_sections("## Summary\n\n```\n## Validation\n```\n")
    assert list(sections) == ["Summary"]


def test_subsection_is_not_part_of_its_parent() -> None:
    sections = validator.parse_sections(
        "## Validation\n\n### Tests Executed\n\nran it\n"
    )
    assert sections["Validation"].strip() == ""
    assert sections["Tests Executed"].strip() == "ran it"


# Automation authors


def test_dependabot_pull_request_skips_branch_issue_and_section_checks() -> None:
    pr = validator.PullRequest(
        title="ci(deps): bump actions/checkout from 7.0.1 to 7.1.0",
        body="Bumps actions/checkout from 7.0.1 to 7.1.0.",
        head_ref="dependabot/github_actions/actions/checkout-7.1.0",
        base_ref="main",
        author="dependabot[bot]",
    )
    assert validator.check_pull_request(pr, RULES, TEMPLATE) == []


def test_automation_author_title_is_still_checked() -> None:
    pr = make_pr(author="dependabot[bot]", title="Bump actions/checkout", body="")
    assert rules_of(validator.check_pull_request(pr, RULES, TEMPLATE)) == ["title"]


def test_schema_1_0_configuration_uses_defaults(tmp_path: Path) -> None:
    shutil.copytree(ROOT / ".project", tmp_path / ".project")
    workflow = tmp_path / ".project" / "workflow.yml"
    text = workflow.read_text(encoding="utf-8")
    text = "\n".join(
        line
        for line in text.split("\n")
        if not line.startswith(("  required_sections:", "  automation_authors:"))
    )
    workflow.write_text(text, encoding="utf-8")
    rules = validator.load_rules(tmp_path)
    assert rules.required_sections == validator.DEFAULT_REQUIRED_SECTIONS
    assert rules.automation_authors == ()


# Elevated review paths


def test_elevated_review_paths_are_reported() -> None:
    changed = [".github/workflows/ci.yml", "SECURITY.md", "README.md", ".projectx/a"]
    assert validator.elevated_paths(changed, RULES) == [
        ".github/workflows/",
        "SECURITY.md",
    ]


# Commits


def test_merge_commits_are_skipped_and_bad_messages_reported() -> None:
    items = [
        validator.Commit("a" * 40, ("b" * 40,), "feat: add cropping\n"),
        validator.Commit("c" * 40, ("a" * 40, "d" * 40), "Merge branch 'develop'\n"),
        validator.Commit("e" * 40, ("c" * 40,), "WIP\n"),
    ]
    findings = validator.check_commits(items, RULES)
    assert len(findings) == 1
    assert findings[0].message.startswith(
        "commit eeeeeeeeeeee: 'WIP' is not a Conventional"
    )


# Command line with an event file and a real Git repository

needs_git = pytest.mark.skipif(
    shutil.which("git") is None, reason="git is not installed"
)


def _git(repo: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *arguments], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    shutil.copytree(ROOT / ".project", tmp_path / ".project")
    (tmp_path / ".github").mkdir()
    shutil.copy(ROOT / validator.TEMPLATE_PATH, tmp_path / validator.TEMPLATE_PATH)
    _git(tmp_path, "init", "-q", "-b", "develop")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "chore: initial commit")
    return tmp_path


def _commit(repo: Path, path: str, message: str) -> str:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(message, encoding="utf-8")
    _git(repo, "add", path)
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _event(repo: Path, base: str, head: str, **pr: object) -> Path:
    data = {
        "title": "feat(scanner): add document cropping",
        "body": FILLED_BODY,
        "user": {"login": "octocat"},
        "base": {"ref": "develop", "sha": base},
        "head": {"ref": "feature/42-document-cropping", "sha": head},
    }
    data.update(pr)
    path = repo.parent / "event.json"
    path.write_text(json.dumps({"pull_request": data}), encoding="utf-8")
    return path


@needs_git
def test_cli_pull_request_passes_and_reports_elevated_paths(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, ".github/workflows/x.yml", "ci: add workflow")
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    code = validator.main(
        ["--repo", str(repo), "pull-request", "--event", str(_event(repo, base, head))]
    )
    output = capsys.readouterr().out
    assert code == 0
    assert (
        "::notice title=Elevated review required::this pull request changes .github/workflows/"
        in output
    )
    assert "All rules passed." in summary.read_text(encoding="utf-8")


@needs_git
def test_cli_pull_request_lists_each_failed_rule_with_a_fix(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    event = _event(repo, base, base, title="Add cropping", body="")
    code = validator.main(["--repo", str(repo), "pull-request", "--event", str(event)])
    output = capsys.readouterr().out
    assert code == 1
    assert "error: [title]" in output
    assert "error: [issue-link]" in output
    assert output.count("  fix: ") == output.count("error: [")


@needs_git
def test_cli_commits_reports_a_bad_commit(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _commit(repo, "a.txt", "feat: add a")
    head = _commit(repo, "b.txt", "added b")
    code = validator.main(
        ["--repo", str(repo), "commits", "--event", str(_event(repo, base, head))]
    )
    output = capsys.readouterr().out
    assert code == 1
    assert "'added b' is not a Conventional Commits header" in output
    assert "1 problem(s)" in output


@needs_git
def test_cli_commits_accepts_a_local_range(repo: Path) -> None:
    _commit(repo, "a.txt", "feat: add a")
    assert (
        validator.main(["--repo", str(repo), "commits", "--range", "HEAD~1..HEAD"]) == 0
    )


@pytest.mark.parametrize("sha", ["HEAD", "--output=x", "a" * 39])
def test_cli_rejects_invalid_commit_ids_in_the_event(
    tmp_path: Path, sha: str, capsys: pytest.CaptureFixture[str]
) -> None:
    event = tmp_path / "event.json"
    event.write_text(
        json.dumps(
            {
                "pull_request": {
                    "base": {"ref": "develop", "sha": sha},
                    "head": {"ref": "x", "sha": "b" * 40},
                }
            }
        ),
        encoding="utf-8",
    )
    assert validator.main(["--repo", str(ROOT), "commits", "--event", str(event)]) == 2
    assert "invalid commit ID" in capsys.readouterr().err


def test_cli_rejects_an_option_as_range(capsys: pytest.CaptureFixture[str]) -> None:
    assert validator.main(["--repo", str(ROOT), "commits", "--range=--all..x"]) == 2
    assert "invalid revision range" in capsys.readouterr().err
