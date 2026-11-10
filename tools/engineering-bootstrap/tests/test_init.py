"""Tests for ``project-bootstrap init`` on a real Git clone with a fake GitHub API."""

from __future__ import annotations

import datetime
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import httpx
import pytest
from conftest import REPOSITORY_ROOT

from engineering_bootstrap.cli import EXIT_FAILED, EXIT_OK, EXIT_USAGE, main
from engineering_bootstrap.engine import Action, Change
from engineering_bootstrap.git import Git
from engineering_bootstrap.resources import init as project_init

REPO = "octo/demo"
TEMPLATE = "BenBotsch/UniversalProjectTemplate"
YEAR = datetime.datetime.now(datetime.UTC).year
MIT_BODY = (
    "MIT License\n\nCopyright (c) [year] [fullname]\n\n"
    "Permission is hereby granted, free of charge.\n"
)
APACHE_BODY = "Apache License\nVersion 2.0\n\nCopyright [yyyy] [name of copyright owner]\n"
PASSING_VALIDATOR = 'import json\nprint(json.dumps({"findings": []}))\n'
FAILING_VALIDATOR = (
    "import json\n"
    'finding = {"rule": "REPO-X", "file": "a.md", "line": 3, "message": "bad", '
    '"severity": "error"}\n'
    'print(json.dumps({"findings": [finding]}))\n'
)
README = """\
# PROJECT_NAME

PROJECT_DESCRIPTION

<!-- template-only:start -->
## Using this template

Run project-bootstrap init.
<!-- template-only:end -->

## Contributing

See https://github.com/OWNER/REPOSITORY and MY_PROJECT_NAME.

## License

The template is licensed under the [MIT License](LICENSE).
"""
CODEOWNERS = """\
# template-only:start
# The template names its maintainer.
# template-only:end
*        @BenBotsch
/docs/   @BenBotsch/docs
"""


class FakeGitHubAPI:
    """Serves the repository, the owner's profile and two license texts."""

    def __init__(self) -> None:
        self.repository: dict[str, Any] = {
            "full_name": REPO,
            "name": "demo",
            "owner": {"login": "octo", "type": "User"},
            "description": "A demo project",
            "visibility": "public",
            "is_template": False,
            "template_repository": {"full_name": TEMPLATE},
        }
        self.profile: dict[str, Any] = {"login": "octo", "name": "Octo Cat"}
        self.requests: list[tuple[str, str]] = []

    @property
    def transport(self) -> httpx.MockTransport:
        """Return an httpx transport that serves this fake."""
        return httpx.MockTransport(self)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.requests.append((request.method, path))
        if request.method != "GET":
            return httpx.Response(405, json={"message": "read only"})
        if path == f"/repos/{REPO}":
            return httpx.Response(200, json=self.repository)
        if path == "/users/octo":
            return httpx.Response(200, json=self.profile)
        if path == "/licenses/mit":
            return httpx.Response(
                200, json={"spdx_id": "MIT", "name": "MIT License", "body": MIT_BODY}
            )
        if path == "/licenses/apache-2.0":
            body = {"spdx_id": "Apache-2.0", "name": "Apache License 2.0", "body": APACHE_BODY}
            return httpx.Response(200, json=body)
        return httpx.Response(404, json={"message": "Not Found"})


def git(root: Path, *args: str) -> str:
    """Run Git in ``root`` with a fixed identity and without signing."""
    result = subprocess.run(  # noqa: S603
        [shutil.which("git") or "git", "-C", str(root), *args],
        capture_output=True,
        check=True,
        text=True,
    )
    return result.stdout


def write(root: Path, path: str, content: str | bytes) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        target.write_bytes(content)
    else:
        target.write_bytes(content.encode("utf-8"))


@pytest.fixture
def clone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return a committed clone of ``octo/demo`` as a repository created from the template."""
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    root = tmp_path / "clone"
    shutil.copytree(REPOSITORY_ROOT / ".project", root / ".project")
    write(root, "README.md", README)
    write(root, "CONTRIBUTING.md", "git clone https://github.com/OWNER/REPOSITORY.git\n")
    write(root, ".github/CODEOWNERS", CODEOWNERS)
    write(root, "LICENSE", "MIT License\n\nCopyright (c) 2026 Benny Botsch\n\nPermission.\n")
    write(root, "template-dev/notes.md", "PROJECT_NAME template notes\n")
    write(root, "tools/engineering-bootstrap/tool.py", "print('PROJECT_NAME')\n")
    write(root, "tests/ci/test_tokens.py", "TOKEN = 'PROJECT_NAME'\n")
    write(root, "logo.bin", b"PROJECT_NAME\0binary")
    write(root, "scripts/ci/validate_repository.py", PASSING_VALIDATOR)
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
    return root


@pytest.fixture
def api() -> FakeGitHubAPI:
    return FakeGitHubAPI()


def run(clone: Path, api: FakeGitHubAPI, *options: str) -> int:
    argv = ["init", f"--repo={REPO}", "--path", str(clone), "--format", "json", *options]
    return main(argv, transport=api.transport)


def report(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    return json.loads(capsys.readouterr().out)


def by_key(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {change["key"]: change for change in document["changes"]}


def read(root: Path, path: str) -> str:
    return (root / path).read_bytes().decode("utf-8")


# Text transformations


def test_template_blocks_are_removed_with_their_markers() -> None:
    text = (
        "a\n<!-- template-only:start -->\nb\n<!-- template-only:end -->\nc\n"
        "# template-only:start\nd\n# template-only:end\n"
    )

    result, blocks = project_init.remove_template_blocks(text)

    assert result == "a\nc\n"
    assert blocks == 2


def test_removed_block_leaves_no_double_blank_line() -> None:
    text = "a\n\n<!-- template-only:start -->\nb\n<!-- template-only:end -->\n\nc\n"

    assert project_init.remove_template_blocks(text) == ("a\n\nc\n", 1)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("template-only:start\n", "without template-only:end"),
        ("template-only:end\n", "without template-only:start"),
        ("template-only:start\ntemplate-only:start\n", "inside the block of line 1"),
    ],
)
def test_unbalanced_template_blocks_are_rejected(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        project_init.remove_template_blocks(text)


def test_placeholders_respect_token_boundaries() -> None:
    pattern = project_init.token_pattern(["OWNER/", "OWNER/REPOSITORY", "PROJECT_NAME"])
    assert pattern is not None
    values = {"OWNER/": "octo/", "OWNER/REPOSITORY": "octo/demo", "PROJECT_NAME": "Demo"}

    text, counts = project_init.replace_placeholders(
        "PROJECT_NAME MY_PROJECT_NAME OWNER/REPOSITORY OWNER/x", pattern, values
    )

    assert text == "Demo MY_PROJECT_NAME octo/demo octo/x"
    assert counts == {"PROJECT_NAME": 1, "OWNER/REPOSITORY": 1, "OWNER/": 1}


def test_license_section_is_replaced_or_appended() -> None:
    text = "# T\n\n## License\n\nold\ntext\n\n## Next\n\nkept\n"

    assert project_init.set_section(text, "## License", "new") == (
        "# T\n\n## License\n\nnew\n\n## Next\n\nkept\n"
    )
    assert project_init.set_section("# T\n", "## License", "new") == "# T\n\n## License\n\nnew\n"


def test_code_owner_replaces_only_the_template_owner() -> None:
    text = "* @BenBotsch\n/docs/ @BenBotsch/docs\n# mail ben@BenBotsch.example\n"

    result, count = project_init.replace_code_owner(text, "BenBotsch", "octo")

    assert result == "* @octo\n/docs/ @BenBotsch/docs\n# mail ben@BenBotsch.example\n"
    assert count == 1


def test_yaml_scalars_keep_comments_and_layout() -> None:
    text = (
        '# head\nproject:\n  name: "X"  # the name\n  # flag\n  is_template: true\n'
        'other:\n  name: "Y"\n'
    )

    result = project_init.set_yaml_scalars(
        text, {("project", "name"): 'Demo "quoted"', ("project", "is_template"): False}
    )

    assert result == (
        '# head\nproject:\n  name: "Demo \\"quoted\\""  # the name\n  # flag\n'
        '  is_template: false\nother:\n  name: "Y"\n'
    )


def test_yaml_scalars_report_a_missing_key() -> None:
    with pytest.raises(ValueError, match=r"cannot find template\.source"):
        project_init.set_yaml_scalars("project:\n  name: x\n", {("template", "source"): "a/b"})


# Values and refusal


class StaticClient:
    def __init__(self, api: FakeGitHubAPI) -> None:
        self.api = api

    def get_json(self, url: str, *, params: Any = None) -> Any:
        response = self.api(httpx.Request("GET", f"https://api.github.com{url}"))
        if response.status_code == 404:
            raise project_init.NotFoundError(url)
        return response.json()


def values(api: FakeGitHubAPI, **options: Any) -> project_init.InitValues:
    return project_init.values_from_github(
        StaticClient(api),
        REPO,
        api.repository,
        {"license": "MIT"},
        project_init.InitOptions(**options),
        2030,
    )


def test_values_come_from_github_and_the_owner_profile(api: FakeGitHubAPI) -> None:
    result = values(api)

    assert (result.name, result.description, result.code_owner) == (
        "demo",
        "A demo project",
        "octo",
    )
    assert result.template_source == TEMPLATE
    assert result.copyright_holder == "Octo Cat"
    assert result.license_text() == (
        "MIT License\n\nCopyright (c) 2030 Octo Cat\n\n"
        "Permission is hereby granted, free of charge.\n"
    )


def test_options_override_github(api: FakeGitHubAPI) -> None:
    result = values(
        api, name="Demo", description="Other", code_owner="@octo-org/team", license="none"
    )

    assert (result.name, result.description, result.code_owner) == (
        "Demo",
        "Other",
        "octo-org/team",
    )
    assert result.license is None
    assert result.license_sentence() == "Copyright (c) Octo Cat. All rights reserved."


@pytest.mark.parametrize(
    ("change", "options", "message"),
    [
        ({"description": None}, {}, "no description"),
        ({"template_repository": None}, {}, "--template-source"),
        ({"owner": {"login": "octo", "type": "Organization"}}, {}, "--code-owner"),
        ({}, {"license": "WTFPL"}, "GitHub offers no license"),
        ({}, {"code_owner": "not a team!"}, "invalid code owner"),
        ({}, {"description": "two\nlines"}, "one line"),
        ({}, {"copyright_holder": "[x]"}, "must not contain"),
    ],
)
def test_invalid_values_are_rejected(
    api: FakeGitHubAPI, change: dict[str, Any], options: dict[str, Any], message: str
) -> None:
    api.repository.update(change)

    with pytest.raises(ValueError, match=message):
        values(api, **options)


def test_profile_without_name_uses_the_login(api: FakeGitHubAPI) -> None:
    api.profile["name"] = None

    assert values(api).copyright_holder == "octo"


def test_check_target_refuses_a_template_on_github(clone: Path, api: FakeGitHubAPI) -> None:
    api.repository["is_template"] = True

    with pytest.raises(project_init.InitRefusedError, match="template repository on GitHub"):
        project_init.check_target(Git.in_directory(clone), REPO, api.repository, {})


def test_check_target_refuses_the_template_source(clone: Path, api: FakeGitHubAPI) -> None:
    project_file = {"project": {"is_template": True}, "template": {"source": REPO}}

    with pytest.raises(project_init.InitRefusedError, match="template source"):
        project_init.check_target(Git.in_directory(clone), REPO, api.repository, project_file)


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/octo/demo.git",
        "git@github.com:Octo/Demo.git",
        "https://github.com/octo/demo/",
    ],
)
def test_check_target_accepts_matching_origins(clone: Path, api: FakeGitHubAPI, url: str) -> None:
    git(clone, "remote", "set-url", "origin", url)

    project_init.check_target(Git.in_directory(clone), REPO, api.repository, {})


def test_check_target_refuses_another_origin(clone: Path, api: FakeGitHubAPI) -> None:
    git(clone, "remote", "set-url", "origin", "https://github.com/octo/demo-other.git")

    with pytest.raises(project_init.InitRefusedError, match="is not octo/demo"):
        project_init.check_target(Git.in_directory(clone), REPO, api.repository, {})


# Command line


def test_dry_run_plans_every_change_and_writes_nothing(
    clone: Path, api: FakeGitHubAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run(clone, api)

    changes = by_key(report(capsys))
    assert code == EXIT_OK
    assert changes["template-dev/"]["action"] == "delete"
    assert changes["tools/engineering-bootstrap/"]["action"] == "delete"
    assert changes[".project/project.yml"]["action"] == "update"
    assert changes["LICENSE"]["action"] == "update"
    assert changes["README.md"]["details"] == {
        "template_blocks": 1,
        "placeholders": {"OWNER/REPOSITORY": 1, "PROJECT_DESCRIPTION": 1, "PROJECT_NAME": 1},
        "license_section": True,
    }
    assert changes["scripts/ci/validate_repository.py"]["action"] == "skipped"
    assert changes["chore/<issue>-project-init"]["action"] == "create"
    assert "tests/ci/test_tokens.py" not in changes
    assert "logo.bin" not in changes
    assert git(clone, "status", "--porcelain") == ""
    assert all(method == "GET" for method, _ in api.requests)


def test_apply_commits_on_a_branch_and_a_rerun_is_noop(
    clone: Path, api: FakeGitHubAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run(clone, api, "--apply", "--issue", "7")

    captured = capsys.readouterr()
    changes = by_key(json.loads(captured.out))
    assert code == EXIT_OK
    assert changes["chore/7-project-init"]["action"] == "create"
    assert "next: git push --set-upstream origin chore/7-project-init" in captured.err
    assert "next: gh pr create --base develop" in captured.err
    assert git(clone, "branch", "--show-current").strip() == "chore/7-project-init"
    assert git(clone, "status", "--porcelain") == ""
    assert git(clone, "log", "-1", "--format=%B").strip() == (
        "chore: initialize project from template\n\nRefs: #7"
    )
    assert not (clone / "template-dev").exists()
    assert not (clone / "tools").exists()
    readme = read(clone, "README.md")
    assert readme.startswith("# demo\n\nA demo project\n\n## Contributing")
    assert "Using this template" not in readme
    assert "https://github.com/octo/demo and MY_PROJECT_NAME" in readme
    assert readme.endswith(
        "## License\n\nThis project is licensed under the [MIT License](LICENSE).\n"
    )
    assert read(clone, ".github/CODEOWNERS") == "*        @octo\n/docs/   @BenBotsch/docs\n"
    assert read(clone, "LICENSE") == (
        f"MIT License\n\nCopyright (c) {YEAR} Octo Cat\n\n"
        "Permission is hereby granted, free of charge.\n"
    )
    project = read(clone, ".project/project.yml")
    assert 'name: "demo"' in project
    assert 'description: "A demo project"' in project
    assert 'visibility: "public"' in project
    assert "is_template: false" in project
    assert f'source: "{TEMPLATE}"' in project
    assert "# true only in the template repository" in project
    assert read(clone, "tests/ci/test_tokens.py") == "TOKEN = 'PROJECT_NAME'\n"

    code = run(clone, api, "--apply", "--issue", "7")

    rerun = report(capsys)
    assert code == EXIT_OK
    actions = {change["key"]: change["action"] for change in rerun["changes"]}
    assert actions.pop("scripts/ci/validate_repository.py") == "noop"
    assert set(actions.values()) == {"noop"}


def test_apply_without_issue_changes_nothing(
    clone: Path, api: FakeGitHubAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run(clone, api, "--apply")

    changes = by_key(report(capsys))
    assert code == EXIT_FAILED
    assert "--issue" in changes["chore/<issue>-project-init"]["reason"]
    assert (clone / "template-dev").exists()
    assert git(clone, "branch", "--show-current").strip() == "develop"


def test_apply_refuses_a_dirty_working_tree(
    clone: Path, api: FakeGitHubAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    write(clone, "notes.txt", "local change\n")

    code = run(clone, api, "--apply", "--issue", "7")

    changes = by_key(report(capsys))
    assert code == EXIT_FAILED
    assert "not clean" in changes["chore/7-project-init"]["reason"]
    assert (clone / "template-dev").exists()


def test_failed_validation_leaves_the_changes_uncommitted(
    clone: Path, api: FakeGitHubAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    write(clone, "scripts/ci/validate_repository.py", FAILING_VALIDATOR)
    git(clone, "commit", "--quiet", "--all", "--message", "test: failing validator")

    code = run(clone, api, "--apply", "--issue", "7")

    changes = by_key(report(capsys))
    assert code == EXIT_FAILED
    validation = changes["scripts/ci/validate_repository.py"]
    assert validation["details"]["errors"] == ["REPO-X a.md:3: bad"]
    assert "not committed" in changes["chore/7-project-init"]["reason"]
    assert git(clone, "log", "-1", "--format=%s").strip() == "test: failing validator"
    assert git(clone, "branch", "--show-current").strip() == "chore/7-project-init"


def test_license_none_removes_the_license(
    clone: Path, api: FakeGitHubAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run(clone, api, "--apply", "--issue", "7", "--license", "none")

    changes = by_key(report(capsys))
    assert code == EXIT_OK
    assert changes["LICENSE"]["action"] == "delete"
    assert not (clone / "LICENSE").exists()
    assert read(clone, "README.md").endswith(
        "## License\n\nCopyright (c) Octo Cat. All rights reserved.\n"
    )


def test_other_license_is_written_from_github(
    clone: Path, api: FakeGitHubAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run(clone, api, "--apply", "--issue", "7", "--license", "Apache-2.0")

    assert code == EXIT_OK
    assert read(clone, "LICENSE") == APACHE_BODY
    assert "[Apache License 2.0](LICENSE)" in read(clone, "README.md")


def test_unbalanced_marker_fails_the_plan(
    clone: Path, api: FakeGitHubAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    write(clone, "SUPPORT.md", "<!-- template-only:start -->\n")
    git(clone, "add", "SUPPORT.md")
    git(clone, "commit", "--quiet", "--message", "test: broken marker")

    code = run(clone, api, "--apply", "--issue", "7")

    changes = by_key(report(capsys))
    assert code == EXIT_FAILED
    assert changes["SUPPORT.md"]["action"] == "failed"
    assert changes["chore/7-project-init"]["action"] == "skipped"
    assert (clone / "template-dev").exists()


def test_init_refuses_the_template_repository(
    clone: Path, api: FakeGitHubAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    api.repository["is_template"] = True

    code = run(clone, api, "--apply", "--issue", "7")

    assert code == EXIT_FAILED
    assert "init refused" in capsys.readouterr().err
    assert (clone / "template-dev").exists()


def test_invalid_value_is_a_usage_error(
    clone: Path, api: FakeGitHubAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    api.repository["description"] = ""

    code = run(clone, api)

    assert code == EXIT_USAGE
    assert "--description" in capsys.readouterr().err


def test_path_outside_a_git_root_fails(
    tmp_path: Path, api: FakeGitHubAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "plain").mkdir()

    code = main(
        ["init", f"--repo={REPO}", "--path", str(tmp_path / "plain")], transport=api.transport
    )

    assert code == EXIT_FAILED
    assert api.requests == []


def test_template_checkout_initializes_to_a_valid_project(
    tmp_path: Path,
    api: FakeGitHubAPI,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Every placeholder and marker of the real template is handled, and validation passes."""
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    root = tmp_path / "project"
    # Tracked and new, not ignored files: the working tree as it would be committed.
    listing = git(REPOSITORY_ROOT, "ls-files", "--cached", "--others", "--exclude-standard")
    for path in listing.splitlines():
        source = REPOSITORY_ROOT / path
        if source.is_file():
            write(root, path, source.read_bytes())
    git(tmp_path, "init", "--quiet", "--initial-branch=develop", str(root))
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

    code = run(root, api, "--apply", "--issue", "1")

    changes = by_key(report(capsys))
    assert code == EXIT_OK, [c for c in changes.values() if c["action"] == "failed"]
    assert changes[project_init.VALIDATOR]["details"]["errors"] == []
    assert changes["chore/1-project-init"]["applied"] is True
    assert not [key for key in changes if key.startswith("placeholder:")]


# Validation runner


def test_validation_reports_broken_output(tmp_path: Path) -> None:
    write(tmp_path, "scripts/ci/validate_repository.py", "print('not json')\n")

    change = project_init.run_validation(tmp_path)

    assert change.action is Action.FAILED
    assert change.reason.startswith("validator did not run")


def test_validation_reports_a_missing_validator(tmp_path: Path) -> None:
    assert project_init.run_validation(tmp_path) == Change(
        "validation", project_init.VALIDATOR, Action.FAILED, "validator is missing"
    )


def test_validation_counts_warnings(tmp_path: Path) -> None:
    script = (
        "import json\n"
        'print(json.dumps({"findings": [{"rule": "R", "file": "f", "message": "m", '
        '"severity": "warning"}]}))\n'
    )
    write(tmp_path, "scripts/ci/validate_repository.py", script)

    change = project_init.run_validation(tmp_path)

    assert change.action is Action.NOOP
    assert change.reason == "passed with 1 warning(s)"
