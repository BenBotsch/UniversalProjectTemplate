"""Ensure that the default and the development branch exist.

The development branch, ``develop`` by default, is created from the head of the default branch
when it is missing. An existing development branch is never moved or reset, even if it is behind
the default branch, because it may hold integrated work. A missing default branch cannot be
created through the API without a commit; it is reported as failed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import quote

from engineering_bootstrap.engine import Action, Change
from engineering_bootstrap.github import GitHubError, NotFoundError

RESOURCE_NAME = "branches"
# GitHub answers 409 for git endpoints of a repository without commits.
EMPTY_REPOSITORY_STATUS = 409


class BranchClient(Protocol):
    """The part of :class:`~engineering_bootstrap.github.GitHubClient` this resource uses."""

    def get_json(self, url: str, *, params: Mapping[str, Any] | None = None) -> Any:
        """Return the JSON body of a GET request."""
        ...

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        """Send a request."""
        ...


@dataclass(frozen=True)
class BranchState:
    """Head commits of the two branches; ``None`` if a branch does not exist.

    Attributes:
        default_sha: Head of the default branch.
        development_sha: Head of the development branch.
        empty: True if the repository has no commits at all.
    """

    default_sha: str | None
    development_sha: str | None
    empty: bool = False


@dataclass(frozen=True)
class BranchSpec:
    """The configured branch names, from ``repository`` in ``project.yml``."""

    default_branch: str
    development_branch: str


def spec_from_config(project_file: Mapping[str, Any]) -> BranchSpec:
    """Build the branch specification from the parsed, schema-valid ``project.yml``."""
    repository = project_file["repository"]
    return BranchSpec(repository["default_branch"], repository["development_branch"])


@dataclass
class BranchResource:
    """Engine resource for the default and development branch of one repository.

    Args:
        client: GitHub client.
        repo: Repository as ``OWNER/NAME``.
        spec: Configured branch names.
        create_development_branch: Value of ``bootstrap.create_develop_branch``; when false the
            development branch is neither checked nor created.
    """

    client: BranchClient
    repo: str
    spec: BranchSpec
    create_development_branch: bool = True
    name: str = RESOURCE_NAME
    depends_on: Sequence[str] = field(default_factory=tuple)

    def read_actual(self) -> BranchState:
        """Return the head commits of both branches."""
        try:
            default_sha = self._head(self.spec.default_branch)
        except GitHubError as exc:
            if exc.status != EMPTY_REPOSITORY_STATUS:
                raise
            return BranchState(None, None, empty=True)
        development_sha = None
        if self.create_development_branch:
            development_sha = self._head(self.spec.development_branch)
        return BranchState(default_sha, development_sha)

    def desired(self) -> BranchSpec:
        """Return the configured branch names."""
        return self.spec

    def diff(self, actual: BranchState, desired: BranchSpec) -> list[Change]:
        """Compare the existing branches with the configuration.

        Returns:
            One change for the default branch (``noop`` or ``failed``) and one for the
            development branch: ``create`` if it is missing, ``noop`` if it exists, ``skipped``
            if it is disabled and ``failed`` if it cannot be created.
        """
        default, development = desired.default_branch, desired.development_branch
        if actual.default_sha is not None:
            changes = [Change(self.name, default, Action.NOOP, "exists")]
        else:
            reason = (
                "repository has no commits; create it from the template or push a first commit"
                if actual.empty
                else "default branch does not exist; create it or fix repository.default_branch"
            )
            changes = [Change(self.name, default, Action.FAILED, reason)]
        if not self.create_development_branch:
            reason = "disabled by bootstrap.create_develop_branch"
            changes.append(Change(self.name, development, Action.SKIPPED, reason))
        elif actual.development_sha is not None:
            reason = "exists; left unchanged"
            changes.append(Change(self.name, development, Action.NOOP, reason))
        elif actual.default_sha is None:
            reason = f"missing, but cannot be created without {default!r}"
            changes.append(Change(self.name, development, Action.FAILED, reason))
        else:
            changes.append(
                Change(
                    self.name,
                    development,
                    Action.CREATE,
                    f"missing; create from {default!r} at {actual.default_sha[:12]}",
                    {"branch": development, "source": default, "sha": actual.default_sha},
                )
            )
        return changes

    def apply(self, change: Change) -> None:
        """Create the development branch at the planned commit."""
        if change.action is not Action.CREATE:
            raise ValueError(f"cannot apply {change.action} to a branch")
        body = {"ref": f"refs/heads/{change.details['branch']}", "sha": change.details["sha"]}
        try:
            self.client.request("POST", f"/repos/{self.repo}/git/refs", json=body)
        except GitHubError as exc:
            # 422: the branch was created meanwhile, for example by a parallel run. It is kept
            # as it is, like any existing development branch.
            if exc.status != 422:
                raise

    def _head(self, branch: str) -> str | None:
        """Return the head commit of ``branch``, or ``None`` if it does not exist."""
        url = f"/repos/{self.repo}/git/ref/heads/{quote(branch, safe='/')}"
        try:
            ref = self.client.get_json(url)
        except NotFoundError:
            return None
        sha = ref.get("object", {}).get("sha") if isinstance(ref, dict) else None
        if not isinstance(sha, str):
            raise GitHubError(f"GET {url}: unexpected response without a commit SHA")
        return sha
