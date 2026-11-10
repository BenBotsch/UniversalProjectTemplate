"""Tests for scripts/ci/validate_repository.py.

Each test builds a small Git repository in a temporary directory, because the validator only
scans tracked files. The repository's own checkout is the template-mode fixture.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "validate_repository", ROOT / "scripts" / "ci" / "validate_repository.py"
)
validate_repository = importlib.util.module_from_spec(_spec)
sys.modules["validate_repository"] = validate_repository
_spec.loader.exec_module(validate_repository)

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None, reason="git is not installed"
)

REQUIRED = {
    "README.md": "# Example\n\nAn example project.\n",
    "AGENTS.md": "# AGENTS.md\n",
    "CONTRIBUTING.md": "# Contributing\n",
    "SECURITY.md": "# Security\n",
    "CHANGELOG.md": "# Changelog\n",
    ".github/PULL_REQUEST_TEMPLATE.md": "## Summary\n",
    # The real labels; make_repo also copies the real issue forms, so REPO-ISSUE-FORMS passes.
    ".project/labels.yml": (ROOT / ".project/labels.yml").read_text(encoding="utf-8"),
}


def project_yml(is_template: bool) -> str:
    return (
        f'schema_version: "1.0"\nproject:\n  is_template: {str(is_template).lower()}\n'
    )


BOOTSTRAP_YML = (
    'schema_version: "1.0"\nbootstrap:\n  template_only_paths:\n    - "template-dev/"\n'
)


def make_repo(root: Path, files: dict[str, str], is_template: bool = False) -> Path:
    """Write ``files`` plus a minimal .project/ into ``root``, then track them with Git."""
    forms = root / ".github/ISSUE_TEMPLATE"
    shutil.copytree(ROOT / ".github/ISSUE_TEMPLATE", forms)
    config = forms / "config.yml"
    # Drop the template-only blocks and replace the placeholders, as init does in a derived
    # repository.
    derived = re.sub(
        r"^[^\n]*template-only:start.*?template-only:end[^\n]*\n",
        "",
        config.read_text(encoding="utf-8"),
        flags=re.DOTALL | re.MULTILINE,
    )
    config.write_text(
        derived.replace("OWNER/REPOSITORY", "example/project"),
        encoding="utf-8",
        newline="\n",
    )
    content = {
        **REQUIRED,
        ".project/project.yml": project_yml(is_template),
        ".project/bootstrap.yml": BOOTSTRAP_YML,
        **files,
    }
    for relative, text in content.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-C", str(root), "add", "-A"], check=True
    )
    return root


def run(repo: Path) -> list:
    return validate_repository.validate_repository(repo)[1]


def rules(findings: list) -> set[str]:
    return {finding.rule for finding in findings}


def test_repository_itself_passes(capsys: pytest.CaptureFixture[str]) -> None:
    # Runs in the template and, after project-bootstrap init, in every derived project.
    project = (ROOT / ".project/project.yml").read_text(encoding="utf-8")
    is_template = (
        re.search(r"^\s*is_template:\s*true\b", project, re.MULTILINE) is not None
    )
    assert validate_repository.main([str(ROOT)]) == 0
    out = capsys.readouterr().out
    assert (validate_repository.TEMPLATE_MESSAGE in out) is is_template


def test_clean_derived_repository_passes(tmp_path: Path) -> None:
    assert run(make_repo(tmp_path, {})) == []


# REPO-REQUIRED


def test_missing_required_file_fails(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, {})
    (repo / "SECURITY.md").unlink()
    findings = run(repo)
    assert [(item.rule, item.file) for item in findings] == [
        ("REPO-REQUIRED", "SECURITY.md")
    ]


def test_required_files_come_from_configuration(tmp_path: Path) -> None:
    workflow = 'repository_validation:\n  required_files: ["LICENSE"]\n'
    findings = run(make_repo(tmp_path, {".project/workflow.yml": workflow}))
    assert [(item.rule, item.file) for item in findings] == [
        ("REPO-REQUIRED", "LICENSE")
    ]


def test_missing_project_file_is_required_and_treated_as_derived(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path, {"template-dev/plan.md": "# Plan\n"})
    (repo / ".project/project.yml").unlink()
    assert {"REPO-REQUIRED", "REPO-TEMPLATE-ONLY"} <= rules(run(repo))


# REPO-TEMPLATE-ONLY


def test_derived_repository_with_template_dev_fails(tmp_path: Path) -> None:
    findings = run(make_repo(tmp_path, {"template-dev/backlog.md": "# Backlog\n"}))
    assert [(item.rule, item.file) for item in findings] == [
        ("REPO-TEMPLATE-ONLY", "template-dev/")
    ]


def test_template_repository_may_contain_template_dev(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path, {"template-dev/backlog.md": "# Backlog\n"}, is_template=True
    )
    assert run(repo) == []


def test_untracked_template_dev_is_ignored(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, {})
    (repo / "template-dev").mkdir()
    (repo / "template-dev" / "notes.md").write_text("local\n", encoding="utf-8")
    assert run(repo) == []


def test_similar_prefix_is_not_template_only(tmp_path: Path) -> None:
    assert run(make_repo(tmp_path, {"template-development/x.txt": "x\n"})) == []


# REPO-PLACEHOLDER


def test_derived_repository_with_project_name_in_readme_fails(tmp_path: Path) -> None:
    findings = run(make_repo(tmp_path, {"README.md": "# PROJECT_NAME\n"}))
    assert [(item.rule, item.file, item.line) for item in findings] == [
        ("REPO-PLACEHOLDER", "README.md", 1)
    ]
    assert "'PROJECT_NAME'" in findings[0].message


@pytest.mark.parametrize(
    "text",
    [
        "PROJECT_DESCRIPTION\n",
        "See https://github.com/OWNER/REPOSITORY/issues\n",
        "* @OWNER_OR_TEAM\n",
        "source: OWNER/UniversalProjectTemplate\n",
    ],
)
def test_each_default_token_is_reported(tmp_path: Path, text: str) -> None:
    assert rules(run(make_repo(tmp_path, {"notes.txt": text}))) == {"REPO-PLACEHOLDER"}


def test_one_finding_per_line_with_longest_token(tmp_path: Path) -> None:
    findings = run(make_repo(tmp_path, {"notes.txt": "OWNER/REPOSITORY and OWNER/x\n"}))
    assert len(findings) == 1
    assert "'OWNER/REPOSITORY'" in findings[0].message


@pytest.mark.parametrize(
    "text", ["MY_PROJECT_NAME\n", "CODEOWNER/x\n", "project_name\n"]
)
def test_token_inside_longer_name_is_not_reported(tmp_path: Path, text: str) -> None:
    assert run(make_repo(tmp_path, {"notes.txt": text})) == []


def test_template_repository_skips_placeholder_check(tmp_path: Path) -> None:
    assert (
        run(make_repo(tmp_path, {"README.md": "# PROJECT_NAME\n"}, is_template=True))
        == []
    )


def test_allowlist_and_template_only_paths_are_skipped(tmp_path: Path) -> None:
    workflow = 'repository_validation:\n  placeholder_allowlist: ["notes/*"]\n'
    files = {
        ".project/workflow.yml": workflow,
        "notes/tokens.md": "Tokens: PROJECT_NAME\n",
        "template-dev/x.md": "PROJECT_NAME\n",
    }
    assert rules(run(make_repo(tmp_path, files))) == {"REPO-TEMPLATE-ONLY"}


def test_binary_files_are_skipped(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, {})
    (repo / "image.bin").write_bytes(b"\0PROJECT_NAME\0")
    subprocess.run(["git", "-C", str(repo), "add", "image.bin"], check=True)
    assert run(repo) == []


# REPO-TEMPLATE-MARKER


def test_leftover_template_marker_is_reported(tmp_path: Path) -> None:
    text = (
        "intro\n<!-- template-only:start -->\nonly here\n<!-- template-only:end -->\n"
    )
    findings = run(make_repo(tmp_path, {"notes.md": text}))
    assert [(item.rule, item.file, item.line) for item in findings] == [
        ("REPO-TEMPLATE-MARKER", "notes.md", 2),
        ("REPO-TEMPLATE-MARKER", "notes.md", 4),
    ]


def test_template_markers_are_allowed_in_the_template(tmp_path: Path) -> None:
    files = {"notes.md": "# template-only:start\nx\n# template-only:end\n"}
    assert run(make_repo(tmp_path, files, is_template=True)) == []


def test_template_markers_in_allowlist_and_template_only_paths_are_skipped(
    tmp_path: Path,
) -> None:
    workflow = 'repository_validation:\n  placeholder_allowlist: ["notes/*"]\n'
    files = {
        ".project/workflow.yml": workflow,
        "notes/markers.md": "template-only:start\n",
        "template-dev/x.md": "template-only:end\n",
    }
    assert rules(run(make_repo(tmp_path, files))) == {"REPO-TEMPLATE-ONLY"}


# REPO-DEAD-LINK-TEMPLATE


def test_readme_link_to_template_dev_fails(tmp_path: Path) -> None:
    readme = "# Example\n\nSee the [backlog](template-dev/backlog.md#ranks).\n"
    findings = run(make_repo(tmp_path, {"README.md": readme}, is_template=True))
    assert [(item.rule, item.file, item.line) for item in findings] == [
        ("REPO-DEAD-LINK-TEMPLATE", "README.md", 3)
    ]


@pytest.mark.parametrize(
    "link",
    [
        "[plan](../../template-dev/roadmap.md)",
        "[plan](/template-dev/roadmap.md)",
        "[plan]: ../../template-dev/roadmap.md",
    ],
)
def test_relative_absolute_and_reference_links_are_resolved(
    tmp_path: Path, link: str
) -> None:
    files = {
        "docs/governance/x.md": f"# X\n\n{link}\n",
        "docs/INDEX.md": "[x](governance/x.md)\n",
    }
    findings = run(make_repo(tmp_path, files, is_template=True))
    assert rules(findings) == {"REPO-DEAD-LINK-TEMPLATE"}


def test_links_inside_code_fences_and_external_links_are_ignored(
    tmp_path: Path,
) -> None:
    readme = (
        "# Example\n\n```text\n[x](template-dev/a.md)\n```\n\n"
        "[site](https://example.com/template-dev/a.md)\n"
    )
    assert run(make_repo(tmp_path, {"README.md": readme}, is_template=True)) == []


def test_links_within_template_only_paths_are_allowed(tmp_path: Path) -> None:
    files = {"template-dev/a.md": "[b](b.md)\n", "template-dev/b.md": "# B\n"}
    assert run(make_repo(tmp_path, files, is_template=True)) == []


# REPO-DOCS-INDEX


def test_document_missing_from_index_fails(tmp_path: Path) -> None:
    files = {"docs/INDEX.md": "# Index\n", "docs/governance/x.md": "# X\n"}
    findings = run(make_repo(tmp_path, files))
    assert [(item.rule, item.file, item.severity) for item in findings] == [
        ("REPO-DOCS-INDEX", "docs/governance/x.md", "error")
    ]


def test_readme_and_template_files_need_no_index_entry(tmp_path: Path) -> None:
    files = {
        "docs/INDEX.md": "# Index\n",
        "docs/features/README.md": "# Features\n",
        "docs/features/_template.md": "# Template\n",
    }
    assert run(make_repo(tmp_path, files)) == []


def test_broken_index_link_fails(tmp_path: Path) -> None:
    files = {"docs/INDEX.md": "# Index\n\n- [Gone](governance/gone.md)\n"}
    findings = run(make_repo(tmp_path, files))
    assert [(item.rule, item.file, item.line) for item in findings] == [
        ("REPO-DOCS-INDEX", "docs/INDEX.md", 3)
    ]


def test_missing_index_with_documents_fails(tmp_path: Path) -> None:
    findings = run(make_repo(tmp_path, {"docs/guide.md": "# Guide\n"}))
    assert [(item.rule, item.file) for item in findings] == [
        ("REPO-DOCS-INDEX", "docs/INDEX.md")
    ]


def test_docs_index_severity_warning_does_not_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = {
        ".project/workflow.yml": 'repository_validation:\n  docs_index_severity: "warning"\n',
        "docs/INDEX.md": "# Index\n",
        "docs/x.md": "# X\n",
    }
    repo = make_repo(tmp_path, files)
    assert validate_repository.main([str(repo)]) == 0
    assert "REPO-DOCS-INDEX docs/x.md: warning: not linked" in capsys.readouterr().err


def test_invalid_docs_index_severity_is_a_config_error(tmp_path: Path) -> None:
    workflow = 'repository_validation:\n  docs_index_severity: "fatal"\n'
    assert rules(run(make_repo(tmp_path, {".project/workflow.yml": workflow}))) == {
        "REPO-CONFIG"
    }


# REPO-ISSUE-FORMS and REPO-CONFIG


def test_issue_form_problems_are_reported_with_relative_paths(tmp_path: Path) -> None:
    labels = (
        'schema_version: "1.0"\nlabels:\n  - name: "type:bug"\n    color: "d73a4a"\n'
    )
    files = {
        ".project/labels.yml": labels,
        ".github/ISSUE_TEMPLATE/bug.yml": "name: Bug\n",
    }
    findings = [
        item
        for item in run(make_repo(tmp_path, files))
        if item.rule == "REPO-ISSUE-FORMS"
    ]
    assert findings
    assert all(not Path(item.file).is_absolute() for item in findings)


def test_invalid_yaml_is_a_config_error(tmp_path: Path) -> None:
    findings = run(make_repo(tmp_path, {".project/bootstrap.yml": "bootstrap: [\n"}))
    assert [(item.rule, item.file) for item in findings] == [
        ("REPO-CONFIG", ".project/bootstrap.yml")
    ]


def test_directory_without_git_is_a_config_error(tmp_path: Path) -> None:
    findings = run(tmp_path)
    assert [item.rule for item in findings] == ["REPO-CONFIG"]
    assert "git ls-files failed" in findings[0].message


# Output


def test_text_output_names_rule_and_exits_with_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = make_repo(tmp_path, {"README.md": "# PROJECT_NAME\n"})
    assert validate_repository.main([str(repo)]) == 1
    captured = capsys.readouterr()
    assert (
        "REPO-PLACEHOLDER README.md:1: placeholder 'PROJECT_NAME' was not replaced"
        in captured.err
    )
    assert "1 error(s), 0 warning(s)" in captured.out


def test_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = make_repo(tmp_path, {"template-dev/a.md": "# A\n"})
    assert validate_repository.main(["--format", "json", str(repo)]) == 1
    document = json.loads(capsys.readouterr().out)
    assert document["template_repository"] is False
    assert document["errors"] == 1
    assert document["findings"] == [
        {
            "rule": "REPO-TEMPLATE-ONLY",
            "file": "template-dev/",
            "message": "template-only path exists in a derived repository; remove it",
            "severity": "error",
            "line": None,
        }
    ]
