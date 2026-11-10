"""Protect the default and development branch and the release tags with repository rulesets.

The desired rulesets come from three files:

- ``project.yml``: the names of the default and development branch.
- ``workflow.yml``: the allowed merge methods, from ``pull_requests.merge_strategy``.
- ``bootstrap.yml``: ``protection`` with the review mode, the required status checks and the
  release tag pattern; ``bootstrap.configure_rulesets`` switches the resource off.

Each ruleset is one change and is identified by its name, so the tool owns the rulesets named in
:data:`RULESET_NAMES` and replaces their content as a whole. Other rulesets are reported but never
changed. No ruleset has bypass actors: the rules apply to administrators as well.

Before anything is planned, the resource checks whether GitHub offers rulesets for the
repository. Private repositories on GitHub Free have neither rulesets nor classic branch
protection. The run then reports every ruleset as ``UNPROTECTED`` and fails, unless the caller
accepts that with ``allow_unprotected``.

A required status check is added only after it has reported once on the protected branch:
GitHub blocks every merge on a required check that never runs. Until then it is ``skipped``. A
check that a ruleset already requires is kept.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Protocol

from engineering_bootstrap.engine import Action, Change
from engineering_bootstrap.github import GitHubError, NotFoundError, PermissionDeniedError
from engineering_bootstrap.resources.repo_settings import MERGE_FIELDS

RESOURCE_NAME = "rulesets"
# Stable ruleset names, independent of the branch names, so that renaming a branch updates the
# ruleset instead of leaving an orphan.
RULESET_NAMES = {
    "default": "bootstrap-default-branch",
    "development": "bootstrap-development-branch",
    "tags": "bootstrap-release-tags",
}
# GitHub answers 403 with this text when the plan or visibility has no rulesets.
UNAVAILABLE_MARKERS = ("Upgrade to GitHub Pro", "make this repository public")
PROTECTION_DOC = "docs/governance/branch-protection.md"


class RulesetsClient(Protocol):
    """The part of :class:`~engineering_bootstrap.github.GitHubClient` this resource uses."""

    def get_json(self, url: str, *, params: Mapping[str, Any] | None = None) -> Any:
        """Return the JSON body of a GET request."""
        ...

    def paginate(self, url: str, *, params: Mapping[str, Any] | None = None) -> Any:
        """Yield the items of a paginated list endpoint."""
        ...

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        """Send a request and raise on an error status."""
        ...


@dataclass(frozen=True)
class RulesetSpec:
    """One desired ruleset.

    Attributes:
        name: Ruleset name on GitHub and key of the change.
        target: ``branch`` or ``tag``.
        include: Ref patterns the ruleset applies to, for example ``refs/heads/main``.
        rules: Rules without the status check rule, as the rulesets API expects them.
        required_checks: Status check names to require once they have reported on ``branch``.
        branch: Branch on which the required checks must have reported.
        skip_reason: Set if the ruleset is not managed.
    """

    name: str
    target: str
    include: tuple[str, ...]
    rules: tuple[Mapping[str, Any], ...]
    required_checks: tuple[str, ...] = ()
    branch: str | None = None
    skip_reason: str | None = None


@dataclass
class ActualRulesets:
    """Current state read from GitHub.

    Attributes:
        unavailable: GitHub's reason why the repository cannot have rulesets, or None.
        managed: Full ruleset by name, for the rulesets this resource owns.
        others: Names of all other rulesets that apply to the repository.
        check_apps: GitHub App ID per ``(branch, check)`` of the latest run on the branch head;
            missing if the check never reported there.
    """

    unavailable: str | None = None
    managed: dict[str, dict[str, Any]] = field(default_factory=dict)
    others: list[str] = field(default_factory=list)
    check_apps: dict[tuple[str, str], int | None] = field(default_factory=dict)


def rulesets_from_config(files: Mapping[str, Mapping[str, Any]]) -> list[RulesetSpec]:
    """Build the desired rulesets from the parsed configuration files.

    Args:
        files: Parsed ``.project`` files by name, as in
            :attr:`~engineering_bootstrap.config.ProjectConfig.files`.

    Raises:
        ValueError: If ``bootstrap.yml`` has no ``protection`` section (schema before 1.2).
    """
    bootstrap_file = files["bootstrap"]
    if "protection" not in bootstrap_file:
        raise ValueError(
            "bootstrap.yml has no protection section; migrate it to schema_version 1.2"
        )
    protection = bootstrap_file["protection"]
    repository = files["project"]["repository"]
    merge_strategy = files["workflow"]["pull_requests"]["merge_strategy"]
    methods = sorted({m for m in merge_strategy.values() if m in MERGE_FIELDS})
    checks = tuple(protection["required_status_checks"])
    branch_rules = (
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        {"type": "pull_request", "parameters": _review_parameters(protection["mode"], methods)},
    )
    specs = [
        RulesetSpec(
            RULESET_NAMES[kind],
            "branch",
            (f"refs/heads/{branch}",),
            branch_rules,
            required_checks=checks,
            branch=branch,
        )
        for kind, branch in (
            ("default", repository["default_branch"]),
            ("development", repository["development_branch"]),
        )
    ]
    tag_pattern = protection.get("release_tag_pattern")
    specs.append(
        RulesetSpec(
            RULESET_NAMES["tags"],
            "tag",
            (f"refs/tags/{tag_pattern}",) if tag_pattern else (),
            ({"type": "deletion"}, {"type": "update"}),
            skip_reason=None if tag_pattern else "protection.release_tag_pattern not set",
        )
    )
    if not files["bootstrap"].get("bootstrap", {}).get("configure_rulesets", True):
        disabled = "disabled by bootstrap.configure_rulesets"
        specs = [replace(spec, skip_reason=disabled) for spec in specs]
    return specs


def _review_parameters(mode: str, methods: Sequence[str]) -> dict[str, Any]:
    """Return the parameters of the pull request rule.

    Solo mode requires no approval, because authors cannot approve their own pull requests; the
    pull request and the status checks stay required.
    """
    team = mode == "team"
    return {
        "required_approving_review_count": 1 if team else 0,
        "dismiss_stale_reviews_on_push": team,
        "require_code_owner_review": team,
        "require_last_push_approval": False,
        "required_review_thread_resolution": True,
        "allowed_merge_methods": list(methods),
    }


@dataclass
class RulesetResource:
    """Engine resource for the repository rulesets.

    Args:
        client: GitHub client.
        repo: Repository as ``OWNER/NAME``.
        specs: Desired rulesets, see :func:`rulesets_from_config`.
        allow_unprotected: Report a repository without rulesets as ``skipped`` instead of
            ``failed``.
    """

    client: RulesetsClient
    repo: str
    specs: Sequence[RulesetSpec]
    allow_unprotected: bool = False
    name: str = RESOURCE_NAME
    depends_on: Sequence[str] = field(default_factory=tuple)

    def read_actual(self) -> ActualRulesets:
        """Read the rulesets and whether the required checks have reported.

        Raises:
            PermissionDeniedError: If the token has no administration access, or GitHub denies
                the rulesets for another reason than the plan.
        """
        repository = self.client.get_json(self._url())
        permissions = repository.get("permissions")
        if isinstance(permissions, dict) and not permissions.get("admin"):
            raise PermissionDeniedError(
                f"the token needs administration access to {self.repo} to read and change its"
                " rulesets",
                403,
            )
        actual = ActualRulesets()
        managed = {spec.name for spec in self.specs if spec.skip_reason is None}
        if not managed:
            return actual
        try:
            listed = list(self.client.paginate(self._url("/rulesets")))
        except PermissionDeniedError as exc:
            reason = _unavailable_reason(str(exc))
            if reason is None:
                raise
            actual.unavailable = reason
            return actual
        for summary in listed:
            name = summary.get("name")
            if name in managed and summary.get("source_type", "Repository") == "Repository":
                actual.managed[name] = self.client.get_json(self._url(f"/rulesets/{summary['id']}"))
            else:
                actual.others.append(str(name))
        for spec in self.specs:
            if spec.skip_reason is not None or spec.branch is None:
                continue
            for check in spec.required_checks:
                ran, app_id = self._check_ran(spec.branch, check)
                if ran:
                    actual.check_apps[(spec.branch, check)] = app_id
        return actual

    def desired(self) -> Sequence[RulesetSpec]:
        """Return the desired rulesets."""
        return self.specs

    def diff(self, actual: ActualRulesets, desired: Sequence[RulesetSpec]) -> list[Change]:
        """Compare the current with the desired rulesets.

        Returns:
            Per ruleset ``create``, ``update`` or ``noop``; ``skipped`` if it is unmanaged;
            ``failed`` with ``UNPROTECTED`` if the repository cannot have rulesets and
            ``allow_unprotected`` is not set. A required check that never reported adds a
            ``skipped`` change ``<ruleset>:<check>``. Other rulesets are reported as
            ``skipped``.
        """
        changes: list[Change] = []
        for spec in desired:
            if spec.skip_reason is not None:
                changes.append(Change(self.name, spec.name, Action.SKIPPED, spec.skip_reason))
            elif actual.unavailable is not None:
                changes.append(self._unprotected(spec, actual.unavailable))
            else:
                changes.extend(self._diff_one(spec, actual))
        for other in actual.others:
            reason = "not managed by bootstrap; left unchanged"
            changes.append(Change(self.name, f"other:{other}", Action.SKIPPED, reason))
        return changes

    def apply(self, change: Change) -> None:
        """Create or replace one ruleset."""
        body = dict(change.details["ruleset"])
        if change.action is Action.CREATE:
            self.client.request("POST", self._url("/rulesets"), json=body)
        elif change.action is Action.UPDATE:
            self.client.request("PUT", self._url(f"/rulesets/{change.details['id']}"), json=body)
        else:
            raise ValueError(f"cannot apply {change.action} to a ruleset")

    def _diff_one(self, spec: RulesetSpec, actual: ActualRulesets) -> list[Change]:
        current = actual.managed.get(spec.name)
        status_checks, check_changes = self._status_checks(spec, actual, current)
        rules = [dict(rule) for rule in spec.rules]
        if status_checks:
            rules.append(
                {
                    "type": "required_status_checks",
                    "parameters": {
                        "strict_required_status_checks_policy": False,
                        "required_status_checks": status_checks,
                    },
                }
            )
        body = {
            "name": spec.name,
            "target": spec.target,
            "enforcement": "active",
            "bypass_actors": [],
            "conditions": {"ref_name": {"include": list(spec.include), "exclude": []}},
            "rules": rules,
        }
        if current is None:
            change = Change(self.name, spec.name, Action.CREATE, "missing", {"ruleset": body})
        elif (now := _normalize(current, body)) == (wanted := _normalize(body, body)):
            change = Change(self.name, spec.name, Action.NOOP, "matches")
        else:
            differs = sorted(key for key, value in wanted.items() if now.get(key) != value)
            change = Change(
                self.name,
                spec.name,
                Action.UPDATE,
                f"differs in {', '.join(differs)}",
                {"ruleset": body, "id": current["id"]},
            )
        return [change, *check_changes]

    def _status_checks(
        self, spec: RulesetSpec, actual: ActualRulesets, current: Mapping[str, Any] | None
    ) -> tuple[list[dict[str, Any]], list[Change]]:
        """Return the status checks to require and a ``skipped`` change per pending check."""
        required = _required_checks(current)
        checks: list[dict[str, Any]] = []
        skipped: list[Change] = []
        for check in spec.required_checks:
            key = (spec.branch or "", check)
            if key in actual.check_apps:
                app_id = actual.check_apps[key]
                # The App ID binds the check to the app that ran it, so another app or a commit
                # status with the same name cannot satisfy it.
                entry: dict[str, Any] = {"context": check}
                if app_id is not None:
                    entry["integration_id"] = app_id
                checks.append(entry)
            elif check in required:
                checks.append(required[check])
            else:
                reason = (
                    f"never ran on '{spec.branch}'; not required yet. Run apply-rulesets again"
                    " after the check has reported once"
                )
                skipped.append(Change(self.name, f"{spec.name}:{check}", Action.SKIPPED, reason))
        return checks, skipped

    def _unprotected(self, spec: RulesetSpec, message: str) -> Change:
        reason = (
            f"UNPROTECTED: GitHub offers no rulesets for {self.repo} ({message}); see"
            f" {PROTECTION_DOC}"
        )
        if self.allow_unprotected:
            return Change(self.name, spec.name, Action.SKIPPED, f"{reason}; accepted")
        return Change(self.name, spec.name, Action.FAILED, reason)

    def _check_ran(self, branch: str, check: str) -> tuple[bool, int | None]:
        """Return whether ``check`` reported on the branch head, and the App ID of that run.

        A branch that does not exist yet counts as "never ran".
        """
        try:
            body = self.client.get_json(
                self._url(f"/commits/{branch}/check-runs"),
                params={"check_name": check, "filter": "latest", "per_page": 1},
            )
        except PermissionDeniedError:
            raise
        except GitHubError as exc:
            if isinstance(exc, NotFoundError) or exc.status == 422:
                return False, None
            raise
        runs = body.get("check_runs") if isinstance(body, dict) else None
        if not runs:
            return False, None
        app_id = (runs[0].get("app") or {}).get("id")
        return True, app_id if isinstance(app_id, int) else None

    def _url(self, suffix: str = "") -> str:
        return f"/repos/{self.repo}{suffix}"


def _unavailable_reason(message: str) -> str | None:
    """Return GitHub's explanation if ``message`` says the plan has no rulesets, else None.

    The client's message adds a hint about token permissions, which does not apply here.
    """
    for detail in re.findall(r"\(([^()]*)\)", message):
        if any(marker in detail for marker in UNAVAILABLE_MARKERS):
            return f"HTTP 403: {detail}"
    return None


def _required_checks(ruleset: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Return the status checks a ruleset already requires, by name."""
    checks: dict[str, dict[str, Any]] = {}
    for rule in (ruleset or {}).get("rules") or []:
        if rule.get("type") == "required_status_checks":
            for check in (rule.get("parameters") or {}).get("required_status_checks") or []:
                checks[check["context"]] = dict(check)
    return checks


def _normalize(ruleset: Mapping[str, Any], desired: Mapping[str, Any]) -> dict[str, Any]:
    """Return the comparable content of ``ruleset``.

    Rule parameters are reduced to the keys that ``desired`` sets, because GitHub adds new
    parameters with defaults over time; lists are sorted, since their order has no meaning.
    """
    wanted = {rule["type"]: rule.get("parameters") or {} for rule in desired["rules"]}
    rules: dict[str, Any] = {}
    for rule in ruleset.get("rules") or []:
        parameters = rule.get("parameters") or {}
        keys = wanted.get(rule["type"], parameters)
        rules[rule["type"]] = {key: _sorted(parameters.get(key)) for key in keys}
    ref_name = (ruleset.get("conditions") or {}).get("ref_name") or {}
    return {
        "target": ruleset.get("target"),
        "enforcement": ruleset.get("enforcement"),
        "bypass_actors": _sorted(ruleset.get("bypass_actors") or []),
        "include": sorted(ref_name.get("include") or []),
        "exclude": sorted(ref_name.get("exclude") or []),
        "rules": rules,
    }


def _sorted(value: Any) -> Any:
    if isinstance(value, list):
        return sorted(value, key=lambda item: json.dumps(item, sort_keys=True))
    return value
