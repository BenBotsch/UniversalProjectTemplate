"""Tests for scripts/ci/check_action_pinning.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "check_action_pinning", ROOT / "scripts" / "ci" / "check_action_pinning.py"
)
check_action_pinning = importlib.util.module_from_spec(_spec)
sys.modules["check_action_pinning"] = check_action_pinning
_spec.loader.exec_module(check_action_pinning)

SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
DIGEST = "a" * 64


def write_workflow(root: Path, body: str, name: str = "ci.yml") -> Path:
    """Write a workflow file below ``root/.github/workflows``."""
    path = root / ".github" / "workflows" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def steps(*uses_lines: str) -> str:
    """Build a minimal workflow with one step per ``uses:`` line."""
    lines = [
        "on: push",
        "jobs:",
        "  build:",
        "    runs-on: ubuntu-latest",
        "    steps:",
    ]
    lines += [f"      - {line}" for line in uses_lines]
    return "\n".join(lines) + "\n"


def test_repository_workflows_are_pinned() -> None:
    count, findings = check_action_pinning.check_repository(ROOT)
    assert count >= 1
    assert findings == []


@pytest.mark.parametrize(
    "line",
    [
        f"uses: actions/checkout@{SHA} # v7.0.1",
        f'uses: "actions/checkout@{SHA}" # v7.0.1',
        f"uses: octo/repo/path/to/action@{SHA} # v1",
        "uses: ./.github/actions/setup",
        f"uses: docker://alpine@sha256:{DIGEST}",
    ],
)
def test_pinned_references_pass(tmp_path: Path, line: str) -> None:
    write_workflow(tmp_path, steps(line))
    assert check_action_pinning.check_repository(tmp_path)[1] == []


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("uses: actions/checkout@v7", "not pinned to a full commit SHA"),
        ("uses: actions/checkout@v7.0.1", "not pinned to a full commit SHA"),
        ("uses: actions/checkout@main", "not pinned to a full commit SHA"),
        (f"uses: actions/checkout@{SHA[:12]} # v7", "not pinned to a full commit SHA"),
        (
            f"uses: actions/checkout@{SHA.upper()} # v7",
            "not pinned to a full commit SHA",
        ),
        ("uses: actions/checkout", "has no version"),
        (f"uses: actions/checkout@{SHA}", "has no version comment"),
        ("uses: docker://alpine:3.20", "not pinned to an image digest"),
    ],
)
def test_unpinned_references_fail(tmp_path: Path, line: str, expected: str) -> None:
    write_workflow(tmp_path, steps(line))
    findings = check_action_pinning.check_repository(tmp_path)[1]
    assert len(findings) == 1
    assert expected in findings[0].message
    assert findings[0].file == ".github/workflows/ci.yml"
    assert findings[0].line == 6


def test_reusable_workflow_reference_is_checked(tmp_path: Path) -> None:
    body = "on: push\njobs:\n  call:\n    uses: octo/repo/.github/workflows/ci.yml@v1\n"
    write_workflow(tmp_path, body)
    findings = check_action_pinning.check_repository(tmp_path)[1]
    assert [finding.line for finding in findings] == [4]


def test_composite_actions_are_scanned(tmp_path: Path) -> None:
    action = tmp_path / ".github" / "actions" / "setup" / "action.yaml"
    action.parent.mkdir(parents=True)
    action.write_text(
        "runs:\n  using: composite\n  steps:\n    - uses: actions/setup-python@v7\n",
        encoding="utf-8",
    )
    count, findings = check_action_pinning.check_repository(tmp_path)
    assert count == 1
    assert findings[0].file == ".github/actions/setup/action.yaml"


def test_commented_out_references_are_ignored(tmp_path: Path) -> None:
    write_workflow(
        tmp_path, steps("name: placeholder") + "      # - uses: actions/checkout@v7\n"
    )
    assert check_action_pinning.check_repository(tmp_path)[1] == []


def test_unparsable_reference_is_reported(tmp_path: Path) -> None:
    write_workflow(tmp_path, steps("uses: 'actions/checkout@v7"))
    findings = check_action_pinning.check_repository(tmp_path)[1]
    assert findings[0].message == "cannot parse 'uses:' reference"


def test_main_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_workflow(tmp_path, steps(f"uses: actions/checkout@{SHA} # v7.0.1"))
    assert check_action_pinning.main(["prog", str(tmp_path)]) == 0
    assert "all action references pinned" in capsys.readouterr().out

    write_workflow(tmp_path, steps("uses: actions/checkout@v7"), name="bad.yaml")
    assert check_action_pinning.main(["prog", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "error: .github/workflows/bad.yaml:6:" in err
    assert "1 unpinned action reference(s)" in err


def test_repository_without_workflows_passes(tmp_path: Path) -> None:
    assert check_action_pinning.check_repository(tmp_path) == (0, [])
