"""Make the GitHub repository settings match the project configuration.

The desired values come from three files, so that no value has two sources:

- ``project.yml``: default branch, description and the template flag.
- ``workflow.yml``: the allowed merge methods, from ``pull_requests.merge_strategy``.
- ``bootstrap.yml``: issues and discussions switches, ``repository_settings`` for the wiki,
  auto-delete of head branches, topics, Actions permissions, the workflow token and the
  security features.

Each setting is one change. A setting that the configuration leaves unmanaged, or that GitHub
does not offer for the repository's plan or visibility, is ``skipped`` with the reason and never
fails the run. The template flag is only reported: marking a repository as template is a manual
decision.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from engineering_bootstrap.engine import Action, Change
from engineering_bootstrap.github import NotFoundError, PermissionDeniedError

RESOURCE_NAME = "repository-settings"

# Settings written with PATCH /repos/{repo}, one field per change.
REPOSITORY_FIELDS = (
    "default_branch",
    "description",
    "has_issues",
    "has_discussions",
    "has_wiki",
    "delete_branch_on_merge",
)
MERGE_FIELDS = {
    "squash": "allow_squash_merge",
    "merge": "allow_merge_commit",
    "rebase": "allow_rebase_merge",
}
SECRET_SCANNING_FIELDS = {
    "secret_scanning": "secret_scanning",
    "secret_scanning_push_protection": "secret_scanning_push_protection",
}
DEPENDABOT_KEYS = ("dependabot_alerts", "dependabot_security_updates")
SECURITY_KEYS = (*SECRET_SCANNING_FIELDS, "private_vulnerability_reporting")
# Products that make secret scanning available for private repositories.
SECRET_SCANNING_PRODUCTS = ("advanced_security", "secret_protection")


class SettingsClient(Protocol):
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
class Setting:
    """One desired setting.

    Attributes:
        key: Name in reports, for example ``has_wiki`` or ``merge_methods``.
        value: Desired JSON-serializable value; lists are sorted.
        skip_reason: Set when the configuration leaves the setting unmanaged.
        report_only: Compare and report the setting, but never change it.
    """

    key: str
    value: Any = None
    skip_reason: str | None = None
    report_only: bool = False


@dataclass(frozen=True)
class ActualSettings:
    """Current values of the managed settings.

    Attributes:
        values: Current value per setting key.
        unavailable: Reason per setting key that GitHub does not offer for this repository.
    """

    values: dict[str, Any]
    unavailable: dict[str, str]


def settings_from_config(files: Mapping[str, Mapping[str, Any]]) -> list[Setting]:
    """Build the desired settings from the parsed, schema-valid configuration.

    Args:
        files: Parsed configuration per name; ``bootstrap`` must use schema 1.1 or later.

    Returns:
        The settings in the order in which they are applied.

    Raises:
        ValueError: If ``bootstrap.yml`` has no ``repository_settings`` section.
    """
    bootstrap_file = files["bootstrap"]
    if "repository_settings" not in bootstrap_file:
        raise ValueError(
            "bootstrap.yml has no repository_settings section; migrate it to schema_version"
            " 1.1 as described in .project/README.md"
        )
    switches = bootstrap_file["bootstrap"]
    repository_settings = bootstrap_file["repository_settings"]
    project = files["project"]
    workflow = files["workflow"]

    settings = [
        Setting("default_branch", project["repository"]["default_branch"]),
        _description(project["project"]["description"], workflow),
        Setting("has_issues", switches["enable_issues"]),
        Setting("has_discussions", switches["enable_discussions"]),
        Setting("has_wiki", repository_settings["has_wiki"]),
        Setting("delete_branch_on_merge", repository_settings["delete_branch_on_merge"]),
        _merge_methods(workflow["pull_requests"]["merge_strategy"]),
        Setting("is_template", project["project"]["is_template"], report_only=True),
    ]
    if "topics" in repository_settings:
        settings.append(Setting("topics", sorted(repository_settings["topics"])))
    else:
        settings.append(Setting("topics", skip_reason="repository_settings.topics not set"))

    actions = repository_settings["actions"]
    settings.append(
        Setting(
            "actions_permissions", {"enabled": True, "allowed_actions": actions["allowed_actions"]}
        )
    )
    if actions["allowed_actions"] == "selected":
        selected = {
            "github_owned_allowed": actions["github_owned_allowed"],
            "verified_allowed": actions["verified_allowed"],
            "patterns_allowed": sorted(actions["patterns_allowed"]),
        }
        settings.append(Setting("actions_selected", selected))
    settings.append(
        Setting(
            "workflow_permissions",
            {
                "default_workflow_permissions": actions["default_workflow_permissions"],
                "can_approve_pull_request_reviews": actions["can_approve_pull_request_reviews"],
            },
        )
    )

    security = repository_settings["security"]
    for names, switch in (
        (DEPENDABOT_KEYS, "configure_dependabot"),
        (SECURITY_KEYS, "configure_security"),
    ):
        disabled = f"disabled by bootstrap.{switch}"
        for name in names:
            if switches[switch]:
                settings.append(Setting(name, security[name]))
            else:
                settings.append(Setting(name, skip_reason=disabled))
    return settings


def _description(description: str, workflow: Mapping[str, Any]) -> Setting:
    tokens = workflow.get("repository_validation", {}).get("placeholder_tokens", [])
    placeholder = next((token for token in tokens if token in description), None)
    if placeholder is not None:
        reason = f"project.description still contains the placeholder {placeholder!r}"
        return Setting("description", skip_reason=reason)
    return Setting("description", description)


def _merge_methods(merge_strategy: Mapping[str, str]) -> Setting:
    used = set(merge_strategy.values())
    return Setting(
        "merge_methods", {field_: method in used for method, field_ in MERGE_FIELDS.items()}
    )


@dataclass
class RepoSettingsResource:
    """Engine resource for the settings of one repository.

    Args:
        client: GitHub client.
        repo: Repository as ``OWNER/NAME``.
        settings: Desired settings, see :func:`settings_from_config`.
    """

    client: SettingsClient
    repo: str
    settings: Sequence[Setting]
    name: str = RESOURCE_NAME
    depends_on: Sequence[str] = field(default_factory=tuple)

    def read_actual(self) -> ActualSettings:
        """Read the current value of every managed setting.

        Raises:
            PermissionDeniedError: If the token has no administration access; GitHub then hides
                several settings, so a comparison would be wrong.
        """
        repository = self.client.get_json(self._url())
        permissions = repository.get("permissions")
        if isinstance(permissions, dict) and not permissions.get("admin"):
            raise PermissionDeniedError(
                f"the token needs administration access to {self.repo} to read and change its"
                " settings",
                403,
            )
        managed = {s.key for s in self.settings if s.skip_reason is None}
        values: dict[str, Any] = {}
        unavailable: dict[str, str] = {}
        public = (
            repository.get("visibility", "private" if repository.get("private") else "public")
            == "public"
        )

        for key in REPOSITORY_FIELDS:
            values[key] = repository.get(key)
        values["description"] = repository.get("description") or ""
        values["merge_methods"] = {f: repository.get(f) for f in MERGE_FIELDS.values()}
        values["is_template"] = repository.get("is_template")
        values["topics"] = sorted(repository.get("topics") or [])

        if managed & {"actions_permissions", "actions_selected"}:
            permissions_ = self.client.get_json(self._url("/actions/permissions"))
            values["actions_permissions"] = {
                "enabled": permissions_.get("enabled"),
                "allowed_actions": permissions_.get("allowed_actions"),
            }
            if "actions_selected" in managed and permissions_.get("allowed_actions") == "selected":
                selected = self.client.get_json(self._url("/actions/permissions/selected-actions"))
                values["actions_selected"] = {
                    "github_owned_allowed": selected.get("github_owned_allowed"),
                    "verified_allowed": selected.get("verified_allowed"),
                    "patterns_allowed": sorted(selected.get("patterns_allowed") or []),
                }
        if "workflow_permissions" in managed:
            workflow = self.client.get_json(self._url("/actions/permissions/workflow"))
            values["workflow_permissions"] = {
                "default_workflow_permissions": workflow.get("default_workflow_permissions"),
                "can_approve_pull_request_reviews": workflow.get(
                    "can_approve_pull_request_reviews"
                ),
            }

        if "dependabot_alerts" in managed:
            values["dependabot_alerts"] = self._exists("/vulnerability-alerts")
        if "dependabot_security_updates" in managed:
            values["dependabot_security_updates"] = self._enabled("/automated-security-fixes")

        analysis = repository.get("security_and_analysis") or {}
        scanning_available = public or any(
            _status(analysis, product) == "enabled" for product in SECRET_SCANNING_PRODUCTS
        )
        for key, analysis_field in SECRET_SCANNING_FIELDS.items():
            if key not in managed:
                continue
            if not scanning_available:
                unavailable[key] = (
                    "not available: private repositories need GitHub Secret Protection or"
                    " Advanced Security"
                )
            elif not analysis:
                unavailable[key] = "not available: GitHub does not report security_and_analysis"
            else:
                values[key] = _status(analysis, analysis_field) == "enabled"

        if "private_vulnerability_reporting" in managed:
            if public:
                values["private_vulnerability_reporting"] = self._enabled(
                    "/private-vulnerability-reporting"
                )
            else:
                unavailable["private_vulnerability_reporting"] = (
                    "not available: only public repositories support private vulnerability"
                    " reporting"
                )
        return ActualSettings(values, unavailable)

    def desired(self) -> Sequence[Setting]:
        """Return the desired settings."""
        return self.settings

    def diff(self, actual: ActualSettings, desired: Sequence[Setting]) -> list[Change]:
        """Compare the current with the desired settings.

        Returns:
            One change per setting: ``update`` if it differs, ``noop`` if it matches and
            ``skipped`` if it is unmanaged, unavailable or report-only and differs.
        """
        changes = []
        for setting in desired:
            if setting.skip_reason is not None:
                changes.append(Change(self.name, setting.key, Action.SKIPPED, setting.skip_reason))
                continue
            if setting.key in actual.unavailable:
                reason = actual.unavailable[setting.key]
                changes.append(Change(self.name, setting.key, Action.SKIPPED, reason))
                continue
            current = actual.values.get(setting.key)
            if current == setting.value:
                changes.append(Change(self.name, setting.key, Action.NOOP, "matches"))
            elif setting.report_only:
                reason = (
                    f"is {current!r}, configured {setting.value!r}; not changed automatically,"
                    " change it in the repository settings"
                )
                changes.append(Change(self.name, setting.key, Action.SKIPPED, reason))
            else:
                changes.append(
                    Change(
                        self.name,
                        setting.key,
                        Action.UPDATE,
                        f"is {current!r}, configured {setting.value!r}",
                        {"value": setting.value, "current": current},
                    )
                )
        return changes

    def apply(self, change: Change) -> None:
        """Write one setting."""
        if change.action is not Action.UPDATE:
            raise ValueError(f"cannot apply {change.action} to a repository setting")
        writer = self._writers().get(change.key)
        if writer is None:
            raise ValueError(f"unknown repository setting {change.key!r}")
        writer(change.details["value"])

    def _writers(self) -> dict[str, Callable[[Any], None]]:
        writers: dict[str, Callable[[Any], None]] = {
            key: (lambda value, key=key: self._patch({key: value})) for key in REPOSITORY_FIELDS
        }
        writers.update(
            {
                "merge_methods": self._patch,
                "topics": lambda value: self._put("/topics", {"names": list(value)}),
                "actions_permissions": lambda value: self._put("/actions/permissions", value),
                "actions_selected": lambda value: self._put(
                    "/actions/permissions/selected-actions", value
                ),
                "workflow_permissions": lambda value: self._put(
                    "/actions/permissions/workflow", value
                ),
                "dependabot_alerts": lambda value: self._toggle("/vulnerability-alerts", value),
                "dependabot_security_updates": lambda value: self._toggle(
                    "/automated-security-fixes", value
                ),
                "private_vulnerability_reporting": lambda value: self._toggle(
                    "/private-vulnerability-reporting", value
                ),
            }
        )
        for key, analysis_field in SECRET_SCANNING_FIELDS.items():
            writers[key] = lambda value, analysis_field=analysis_field: self._patch(
                {
                    "security_and_analysis": {
                        analysis_field: {"status": "enabled" if value else "disabled"}
                    }
                }
            )
        return writers

    def _url(self, suffix: str = "") -> str:
        return f"/repos/{self.repo}{suffix}"

    def _patch(self, body: Mapping[str, Any]) -> None:
        self.client.request("PATCH", self._url(), json=dict(body))

    def _put(self, suffix: str, body: Mapping[str, Any]) -> None:
        self.client.request("PUT", self._url(suffix), json=dict(body))

    def _toggle(self, suffix: str, enabled: bool) -> None:
        self.client.request("PUT" if enabled else "DELETE", self._url(suffix))

    def _exists(self, suffix: str) -> bool:
        """Return True if GET ``suffix`` succeeds and False on 404."""
        try:
            self.client.request("GET", self._url(suffix))
        except NotFoundError:
            return False
        return True

    def _enabled(self, suffix: str) -> bool:
        """Return the ``enabled`` field of GET ``suffix``; a 404 means disabled."""
        try:
            body = self.client.get_json(self._url(suffix))
        except NotFoundError:
            return False
        return bool(body.get("enabled")) if isinstance(body, dict) else False


def _status(analysis: Mapping[str, Any], name: str) -> str | None:
    entry = analysis.get(name)
    return entry.get("status") if isinstance(entry, dict) else None
