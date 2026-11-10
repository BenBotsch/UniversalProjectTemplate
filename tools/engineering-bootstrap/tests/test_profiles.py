"""Tests of the profile mechanism with the noop fixture profile (FEAT-031)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPOSITORY_ROOT
from test_init import REPO, FakeGitHubAPI, git, write

from engineering_bootstrap.cli import EXIT_FAILED, EXIT_OK, main
from engineering_bootstrap.engine import Action
from engineering_bootstrap.resources import profiles
from engineering_bootstrap.resources.init import set_yaml_scalars

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "profiles"
BASE_FILES = (
    ".github/workflows/ci.yml",
    ".github/dependabot.yml",
)
NAME = "Demo Tool"
PACKAGE_INIT = "src/demo_tool/__init__.py"


@pytest.fixture
def source(tmp_path: Path) -> Path:
    """Return a profiles directory with the noop profile and the template's profile schema."""
    target = tmp_path / "profiles"
    shutil.copytree(FIXTURES, target)
    shutil.copytree(REPOSITORY_ROOT / "profiles" / "_schema", target / "_schema")
    return target


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Return a derived project with the template's base files and anchors."""
    root = tmp_path / "project"
    shutil.copytree(REPOSITORY_ROOT / ".project", root / ".project")
    for path in BASE_FILES:
        write(root, path, (REPOSITORY_ROOT / path).read_bytes())
    project_file = root / ".project" / "project.yml"
    text = set_yaml_scalars(
        project_file.read_text(encoding="utf-8"),
        {
            ("project", "name"): NAME,
            ("project", "description"): "A demo tool",
            ("project", "is_template"): False,
        },
    )
    project_file.write_text(text, encoding="utf-8")
    return root


def apply_profile(
    project: Path, source: Path, capsys: pytest.CaptureFixture[str], *options: str
) -> tuple[int, dict[str, dict[str, Any]]]:
    argv = [
        "apply-profile",
        "--profile",
        "noop",
        "--source",
        str(source),
        "--path",
        str(project),
        "--format",
        "json",
        *options,
    ]
    code = main(argv)
    document = json.loads(capsys.readouterr().out)
    return code, {change["key"]: change for change in document["changes"]}


def read(root: Path, path: str) -> str:
    return (root / path).read_text(encoding="utf-8")


def load(root: Path, path: str) -> Any:
    return yaml.safe_load(read(root, path))


# Applying


def test_dry_run_plans_every_file_and_writes_nothing(
    project: Path, source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = read(project, ".github/workflows/ci.yml")

    code, changes = apply_profile(project, source, capsys)

    assert code == EXIT_OK
    assert changes[PACKAGE_INIT]["action"] == "create"
    assert changes[".github/workflows/noop.yml"]["action"] == "create"
    assert changes[".github/workflows/ci.yml"]["action"] == "update"
    assert changes[".project/project.yml"]["action"] == "update"
    assert not (project / PACKAGE_INIT).exists()
    assert read(project, ".github/workflows/ci.yml") == before


def test_apply_writes_files_blocks_and_the_record(
    project: Path, source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, changes = apply_profile(project, source, capsys, "--apply")

    assert code == EXIT_OK, [c for c in changes.values() if c["action"] == "failed"]
    assert read(project, PACKAGE_INIT) == '"""A demo tool"""\n\nNAME = "Demo Tool"\n'
    ci = load(project, ".github/workflows/ci.yml")
    assert ci["jobs"]["noop"] == {"name": "noop", "uses": "./.github/workflows/noop.yml"}
    assert ci["jobs"]["quality-gate"]["needs"][-1] == "noop"
    gates = load(project, ".project/quality-gates.yml")["quality_gates"]
    assert gates["noop_lint"]["covers"] == "lint"
    updates = load(project, ".github/dependabot.yml")["updates"]
    assert updates[-1]["package-ecosystem"] == "pip"
    labels = load(project, ".project/labels.yml")["labels"]
    assert labels[-1]["name"] == "area:noop"
    record = load(project, ".project/project.yml")
    assert record["profiles"] == [{"id": "noop", "version": "0.1.0"}]
    assert record["technology"]["languages"] == ["noopscript"]
    assert record["technology"]["package_managers"] == ["noopget"]
    # The anchors stay below the blocks, so a second profile can be added.
    assert "  # bootstrap:profile-jobs" in read(project, ".github/workflows/ci.yml")


def test_rerun_after_apply_is_noop(
    project: Path, source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    apply_profile(project, source, capsys, "--apply")

    code, changes = apply_profile(project, source, capsys, "--apply")

    assert code == EXIT_OK
    assert {change["action"] for change in changes.values()} == {"noop"}


def test_applied_project_passes_the_configuration_validator(
    project: Path, source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    apply_profile(project, source, capsys, "--apply")
    validator = REPOSITORY_ROOT / "scripts" / "ci" / "validate_project.py"

    result = subprocess.run(  # noqa: S603
        [sys.executable, "-I", str(validator), str(project / ".project")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_edited_file_is_a_conflict_until_forced(
    project: Path, source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    apply_profile(project, source, capsys, "--apply")
    write(project, PACKAGE_INIT, "NAME = 'mine'\n")

    _, changes = apply_profile(project, source, capsys, "--apply")
    assert changes[PACKAGE_INIT]["action"] == "skipped"
    assert "conflict" in changes[PACKAGE_INIT]["reason"]
    assert read(project, PACKAGE_INIT) == "NAME = 'mine'\n"

    _, changes = apply_profile(project, source, capsys, "--apply", "--force")
    assert changes[PACKAGE_INIT]["action"] == "update"
    assert "Demo Tool" in read(project, PACKAGE_INIT)


def test_edited_block_is_a_conflict_until_forced(
    project: Path, source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    apply_profile(project, source, capsys, "--apply")
    path = project / ".project" / "quality-gates.yml"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            'job: "lint"\n    status: "implemented"\n  # profile',
            'job: "lint"\n    status: "not_implemented"\n  # profile',
        ),
        encoding="utf-8",
    )
    assert (
        load(project, ".project/quality-gates.yml")["quality_gates"]["noop_lint"]["status"]
        == "not_implemented"
    )

    _, changes = apply_profile(project, source, capsys, "--apply")
    assert changes[".project/quality-gates.yml"]["action"] == "skipped"

    _, changes = apply_profile(project, source, capsys, "--apply", "--force")
    assert changes[".project/quality-gates.yml"]["action"] == "update"
    gates = load(project, ".project/quality-gates.yml")["quality_gates"]
    assert gates["noop_lint"]["status"] == "implemented"
    assert read(project, ".project/quality-gates.yml").count("# profile:noop:start") == 1


def test_file_removed_after_apply_is_reported_not_recreated(
    project: Path, source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    apply_profile(project, source, capsys, "--apply")
    (project / PACKAGE_INIT).unlink()

    _, changes = apply_profile(project, source, capsys, "--apply")

    assert changes[PACKAGE_INIT]["action"] == "skipped"
    assert "removed since" in changes[PACKAGE_INIT]["reason"]
    assert not (project / PACKAGE_INIT).exists()


def test_missing_anchor_fails_with_a_hint(
    project: Path, source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = project / ".github" / "workflows" / "ci.yml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("# bootstrap:profile-needs", "# removed"),
        encoding="utf-8",
    )

    code, changes = apply_profile(project, source, capsys, "--apply")

    assert code == EXIT_FAILED
    change = changes[".github/workflows/ci.yml"]
    assert change["action"] == "failed"
    assert "bootstrap:profile-needs" in change["reason"]
    assert "restore it from the template" in change["reason"]


def test_profile_needing_another_profile_fails(
    project: Path, source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = source / "noop" / "profile.yml"
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    data["requires_profiles"] = ["docker"]
    manifest.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    code, changes = apply_profile(project, source, capsys, "--apply")

    assert code == EXIT_FAILED
    assert "docker" in changes[".project/project.yml"]["reason"]
    assert not (project / PACKAGE_INIT).exists()


def test_covering_an_unknown_gate_fails(
    project: Path, source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = source / "noop" / "profile.yml"
    text = manifest.read_text(encoding="utf-8").replace('covers: "lint"', 'covers: "linting"')
    manifest.write_text(text, encoding="utf-8")

    code, changes = apply_profile(project, source, capsys, "--apply")

    assert code == EXIT_FAILED
    assert "linting" in changes[".project/quality-gates.yml"]["reason"]


def test_template_checkout_is_refused(
    project: Path, source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = project / ".project" / "project.yml"
    path.write_text(
        set_yaml_scalars(path.read_text(encoding="utf-8"), {("project", "is_template"): True}),
        encoding="utf-8",
    )

    code = main(
        ["apply-profile", "--profile", "noop", "--source", str(source), "--path", str(project)]
    )

    assert code == EXIT_FAILED
    assert "template" in capsys.readouterr().err


def test_unknown_profile_names_the_available_ones(
    project: Path, source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        ["apply-profile", "--profile", "rust", "--source", str(source), "--path", str(project)]
    )

    assert code == EXIT_FAILED
    assert "available: noop" in capsys.readouterr().err


# Loading


def test_job_without_gate_is_rejected(source: Path) -> None:
    workflow = source / "noop" / "files" / ".github" / "workflows" / "noop.yml"
    data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    data["jobs"]["test"] = dict(data["jobs"]["lint"], name="test")
    workflow.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(profiles.ProfileError, match="without a quality gate: test"):
        profiles.load_profile(source, "noop")


def test_gate_of_another_workflow_is_rejected(source: Path) -> None:
    manifest = source / "noop" / "profile.yml"
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    data["quality_gates"]["noop_extra"] = dict(
        data["quality_gates"]["noop_lint"], workflow="ci.yml"
    )
    del data["quality_gates"]["noop_extra"]["covers"]
    manifest.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    with pytest.raises(profiles.ProfileError, match="no ci job of the profile calls"):
        profiles.load_profile(source, "noop")


def test_unlisted_file_is_rejected(source: Path) -> None:
    write(source / "noop" / "files", "extra.txt", "x\n")

    with pytest.raises(profiles.ProfileError, match=r"not listed.*extra\.txt"):
        profiles.load_profile(source, "noop")


def test_base_file_in_a_profile_is_rejected(source: Path) -> None:
    write(source / "noop" / "files", ".github/workflows/ci.yml", "name: x\n")
    manifest = source / "noop" / "profile.yml"
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    data["files"].append(".github/workflows/ci.yml")
    manifest.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    with pytest.raises(profiles.ProfileError, match="base file"):
        profiles.load_profile(source, "noop")


@pytest.mark.parametrize("profile_id", ["../noop", "Noop", ""])
def test_invalid_profile_id_is_rejected(source: Path, profile_id: str) -> None:
    with pytest.raises(profiles.ProfileError, match="invalid profile id"):
        profiles.load_profile(source, profile_id)


def test_schema_violation_names_its_location(source: Path) -> None:
    manifest = source / "noop" / "profile.yml"
    text = manifest.read_text(encoding="utf-8").replace('version: "0.1.0"', 'version: "1"')
    manifest.write_text(text, encoding="utf-8")

    with pytest.raises(profiles.ProfileError, match=r"profile\.yml:version"):
        profiles.load_profile(source, "noop")


def test_template_profiles_load() -> None:
    """Every profile shipped by the template is consistent."""
    source = REPOSITORY_ROOT / "profiles"
    for manifest in source.glob(f"*/{profiles.MANIFEST_NAME}"):
        profiles.load_profile(source, manifest.parent.name)


# Text helpers


def test_blocks_of_two_profiles_stack_above_the_anchor() -> None:
    text = "jobs:\n  a: 1\n  # bootstrap:profile-jobs\nend: 1\n"

    text, first = profiles.set_block(text, "# bootstrap:profile-jobs", "one", ["b: 2"])
    text, second = profiles.set_block(text, "# bootstrap:profile-jobs", "two", ["c: 3"])
    text, again = profiles.set_block(text, "# bootstrap:profile-jobs", "one", ["b: 2"])

    assert (first, second, again) == ("insert", "insert", "noop")
    assert yaml.safe_load(text) == {"jobs": {"a": 1, "b": 2, "c": 3}, "end": 1}
    assert text.index("profile:one:end") < text.index("profile:two:start")


def test_block_belongs_to_the_next_anchor() -> None:
    text = "a:\n  # bootstrap:profile-jobs\nb:\n  # bootstrap:profile-needs\n"
    text, _ = profiles.set_block(text, "# bootstrap:profile-jobs", "x", ["j: 1"])

    text, outcome = profiles.set_block(text, "# bootstrap:profile-needs", "x", ["n: 1"])

    assert outcome == "insert"
    assert yaml.safe_load(text) == {"a": {"j": 1}, "b": {"n": 1}}


def test_unterminated_block_is_rejected() -> None:
    text = "a:\n  # profile:x:start\n  j: 1\n  # bootstrap:profile-jobs\n"

    with pytest.raises(ValueError, match="has no"):
        profiles.set_block(text, "# bootstrap:profile-jobs", "x", ["j: 1"])


def test_render_yaml_matches_the_style_of_the_base_files() -> None:
    lines = profiles.render_yaml(
        [{"name": "a", "labels": ["x", "y"], "schedule": {"interval": "weekly"}, "on": True}]
    )

    assert lines == [
        '- name: "a"',
        '  labels: ["x", "y"]',
        "  schedule:",
        '    interval: "weekly"',
        "  on: true",
    ]


def test_profiles_list_keeps_comments_and_round_trips() -> None:
    text = '# head\nschema_version: "1.1"\n# applied profiles\nprofiles: []\nquality:\n  a: 1\n'
    entries = [{"id": "python", "version": "0.1.0"}]

    once = profiles.set_profiles(text, entries)
    twice = profiles.set_profiles(once, [*entries, {"id": "docker", "version": "1.0.0"}])

    assert "# applied profiles\nprofiles:\n" in once
    assert yaml.safe_load(twice)["quality"] == {"a": 1}
    assert profiles.set_profiles(twice, []) == text


def test_profiles_list_needs_schema_1_1() -> None:
    with pytest.raises(ValueError, match=r"migrate it to 1\.1"):
        profiles.set_profiles('schema_version: "1.0"\n', [])


@pytest.mark.parametrize(
    ("name", "package"),
    [("Demo Tool", "demo_tool"), ("my-lib.v2", "my_lib_v2"), ("PMM", "pmm")],
)
def test_package_name_is_importable(name: str, package: str) -> None:
    assert profiles.package_name(name) == package


@pytest.mark.parametrize("name", ["2fast", "---"])
def test_package_name_rejects_names_without_a_leading_letter(name: str) -> None:
    with pytest.raises(ValueError, match="cannot derive"):
        profiles.package_name(name)


def test_unsafe_target_path_fails_the_plan(project: Path, source: Path) -> None:
    profile = profiles.load_profile(source, "noop")
    resource = profiles.ProfileResource(
        project,
        profile,
        {"PROJECT_NAME": "x", "PROJECT_DESCRIPTION": "y", "PROJECT_PACKAGE": "../x"},
    )

    with pytest.raises(ValueError, match="unsafe path"):
        resource.desired()


# init --profile


def test_init_applies_the_profile_in_the_same_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    root = tmp_path / "clone"
    shutil.copytree(REPOSITORY_ROOT / ".project", root / ".project")
    for path in BASE_FILES:
        write(root, path, (REPOSITORY_ROOT / path).read_bytes())
    shutil.copytree(FIXTURES / "noop", root / "profiles" / "noop")
    shutil.copytree(REPOSITORY_ROOT / "profiles" / "_schema", root / "profiles" / "_schema")
    write(root, "README.md", "# PROJECT_NAME\n\nPROJECT_DESCRIPTION\n\n## License\n\nTBD\n")
    write(root, "scripts/ci/validate_repository.py", "print('{\"findings\": []}')\n")
    git(root.parent, "init", "--quiet", "--initial-branch=develop", str(root))
    for key, value in (
        ("user.name", "Test"),
        ("user.email", "test@example.invalid"),
        ("commit.gpgsign", "false"),
        ("core.autocrlf", "false"),
        ("core.hooksPath", str(tmp_path / "no-hooks")),
    ):
        git(root, "config", "--local", key, value)
    git(root, "remote", "add", "origin", f"https://github.com/{REPO}.git")
    git(root, "add", "--all")
    git(root, "commit", "--quiet", "--message", "chore: create from template")
    api = FakeGitHubAPI()

    code = main(
        [
            "init",
            f"--repo={REPO}",
            "--path",
            str(root),
            "--profile",
            "noop",
            "--apply",
            "--issue",
            "1",
            "--format",
            "json",
        ],
        transport=api.transport,
    )

    document = json.loads(capsys.readouterr().out)
    failed = [c for c in document["changes"] if c["action"] == Action.FAILED]
    assert code == EXIT_OK, failed
    assert not (root / "profiles").exists()
    committed = git(root, "show", "--name-only", "--format=", "HEAD").split()
    assert "src/demo/__init__.py" in committed
    assert ".github/workflows/noop.yml" in committed
    record = yaml.safe_load(read(root, ".project/project.yml"))
    assert record["project"]["is_template"] is False
    assert record["profiles"] == [{"id": "noop", "version": "0.1.0"}]
    assert git(root, "status", "--porcelain") == ""


# The python profile of the template (FEAT-032)


def test_python_profile_jobs_are_reported_into_the_quality_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every python gate resolves to a job of the CI run, and the generic gates are covered."""
    project = tmp_path / "project"
    shutil.copytree(REPOSITORY_ROOT / ".project", project / ".project")
    for path in BASE_FILES:
        write(project, path, (REPOSITORY_ROOT / path).read_bytes())
    path = project / ".project" / "project.yml"
    path.write_text(
        set_yaml_scalars(
            path.read_text(encoding="utf-8"),
            {
                ("project", "name"): NAME,
                ("project", "description"): "A demo tool.",
                ("project", "is_template"): False,
            },
        ),
        encoding="utf-8",
    )
    for workflow in ("quality.yml", "security.yml", "pr-validation.yml"):
        write(
            project,
            f".github/workflows/{workflow}",
            (REPOSITORY_ROOT / ".github" / "workflows" / workflow).read_bytes(),
        )

    code = main(
        [
            "apply-profile",
            "--profile",
            "python",
            "--source",
            str(REPOSITORY_ROOT / "profiles"),
            "--path",
            str(project),
            "--apply",
        ]
    )
    capsys.readouterr()

    assert code == EXIT_OK
    evaluator = _evaluator()
    gates, _ = evaluator.load_gates(project / evaluator.QUALITY_GATES_PATH)
    names = evaluator.resolve_job_names(project / ".github" / "workflows")
    python_gates = {gate.name: gate for gate in gates if gate.name.startswith("python_")}
    assert {names[(gate.workflow, gate.job)] for gate in python_gates.values()} == {
        "python / format",
        "python / lint",
        "python / type-check",
        "python / test",
        "python / build",
        "python / audit",
    }
    covered = {gate.covers for gate in python_gates.values()} - {None}
    assert covered == {"formatting", "lint", "tests", "build", "security"}
    pyproject = read(project, "pyproject.toml")
    assert 'name = "demo_tool"' in pyproject
    assert "PROJECT_" not in pyproject
    assert 'description = "A demo tool."' in pyproject
    assert (project / "src" / "demo_tool" / "py.typed").exists()
    monkeypatch.chdir(project)
    validator = REPOSITORY_ROOT / "scripts" / "ci" / "validate_project.py"
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-I", str(validator), str(project / ".project")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _evaluator() -> Any:
    """Import the quality-gate evaluator of the template's scripts."""
    import importlib.util

    path = REPOSITORY_ROOT / "scripts" / "ci" / "evaluate_quality_gates.py"
    spec = importlib.util.spec_from_file_location("evaluate_quality_gates", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _figure_step() -> str:
    """Return the script of the figure check in the python profile's lint job."""
    workflow = REPOSITORY_ROOT / "profiles" / "python" / "files" / ".github" / "workflows"
    jobs = yaml.safe_load((workflow / "python.yml").read_text(encoding="utf-8"))["jobs"]
    (step,) = [step for step in jobs["lint"]["steps"] if step.get("name") == "Check figures"]
    return str(step["run"])


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash, like the CI runner")
@pytest.mark.parametrize(
    ("figures", "lock", "uv_exit", "expected_exit", "expected_call"),
    [
        pytest.param([], True, 0, 0, None, id="guide-only"),
        pytest.param(["chart.svg"], True, 0, 0, "run --locked --group figures", id="figures"),
        pytest.param(["chart.png"], False, 0, 0, "run --group figures", id="no-lock"),
        pytest.param(["chart.svg"], True, 1, 1, "run --locked --group figures", id="finding"),
    ],
)
def test_python_figure_check_runs_only_with_figures(
    tmp_path: Path,
    figures: list[str],
    lock: bool,
    uv_exit: int,
    expected_exit: int,
    expected_call: str | None,
) -> None:
    """The check installs FigureKit only for a folder with figures and fails with figkit."""
    project = tmp_path / "project"
    write(project, "docs/figures/README.md", b"# Figures\n")
    for name in figures:
        write(project, f"docs/figures/{name}", b"<svg/>\n")
    if lock:
        write(project, "uv.lock", b"")
    calls = tmp_path / "calls.txt"
    write(
        tmp_path,
        "bin/uv",
        f'#!/usr/bin/env bash\necho "$*" >> "{calls.as_posix()}"\nexit {uv_exit}\n'.encode(),
    )
    (tmp_path / "bin" / "uv").chmod(0o755)
    script = tmp_path / "step.sh"
    script.write_bytes(_figure_step().encode())

    result = subprocess.run(  # noqa: S603
        [shutil.which("bash") or "bash", "-eo", "pipefail", script.as_posix()],
        cwd=project,
        env={"PATH": f"{(tmp_path / 'bin').as_posix()}:/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == expected_exit, result.stdout + result.stderr
    called = calls.read_text(encoding="utf-8").splitlines() if calls.exists() else []
    expected = [f"{expected_call} figkit check docs/figures"] if expected_call else []
    assert called == expected
