"""Synchronize repository labels with ``.project/labels.yml``.

Labels are matched by name, case-insensitively as on GitHub. A configured label that is missing
is renamed from one of its ``aliases`` if such a label exists, so issues keep it; otherwise it is
created. Color, description and the spelling of the name are updated when they differ. Labels
that are not configured are reported and deleted only in prune mode.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import quote

from engineering_bootstrap.engine import Action, Change
from engineering_bootstrap.github import GitHubError

RESOURCE_NAME = "labels"


class LabelClient(Protocol):
    """The part of :class:`~engineering_bootstrap.github.GitHubClient` this resource uses."""

    def paginate(self, url: str, *, params: Mapping[str, Any] | None = None) -> Iterable[Any]:
        """Yield the items of a list endpoint."""
        ...

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
class LabelSpec:
    """A label as configured in ``labels.yml``.

    Attributes:
        name: Label name.
        color: 6-digit hex color without ``#``.
        description: Label description.
        aliases: Existing names that are renamed to ``name`` instead of creating it.
    """

    name: str
    color: str
    description: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class ActualLabel:
    """A label as it exists in the repository."""

    name: str
    color: str
    description: str


def specs_from_config(labels_file: Mapping[str, Any]) -> list[LabelSpec]:
    """Build label specifications from the parsed, schema-valid ``labels.yml``."""
    return [
        LabelSpec(
            name=entry["name"],
            color=entry["color"],
            description=entry["description"],
            aliases=tuple(entry.get("aliases", ())),
        )
        for entry in labels_file["labels"]
    ]


@dataclass
class LabelResource:
    """Engine resource for the labels of one repository.

    Args:
        client: GitHub client.
        repo: Repository as ``OWNER/NAME``.
        specs: Configured labels.
        prune: Plan deletions of labels that are not configured. The engine applies them only
            in destructive mode.
    """

    client: LabelClient
    repo: str
    specs: Sequence[LabelSpec]
    prune: bool = False
    name: str = RESOURCE_NAME
    depends_on: Sequence[str] = field(default_factory=tuple)

    def read_actual(self) -> list[ActualLabel]:
        """Return all labels of the repository."""
        return [
            ActualLabel(item["name"], item.get("color") or "", item.get("description") or "")
            for item in self.client.paginate(f"/repos/{self.repo}/labels")
        ]

    def desired(self) -> Sequence[LabelSpec]:
        """Return the configured labels."""
        return self.specs

    def diff(self, actual: Sequence[ActualLabel], desired: Sequence[LabelSpec]) -> list[Change]:
        """Compare repository labels with the configuration.

        Returns:
            One change per configured label (``create``, ``update`` or ``noop``) and one per
            unknown label: ``delete`` in prune mode, otherwise ``skipped``.
        """
        by_key = {label.name.lower(): label for label in actual}
        matched: set[str] = set()
        changes = []
        for spec in desired:
            current = by_key.get(spec.name.lower())
            renamed_from = None
            if current is None:
                current = next(
                    (
                        by_key[alias.lower()]
                        for alias in spec.aliases
                        if alias.lower() in by_key and alias.lower() not in matched
                    ),
                    None,
                )
                renamed_from = current
            if current is None:
                changes.append(self._change(spec, Action.CREATE, "missing", current_name=None))
                continue
            matched.add(current.name.lower())
            differences = _differences(current, spec)
            if renamed_from is not None:
                differences.remove("name")
                reason = f"rename from alias {current.name!r}"
                if differences:
                    reason += f"; {', '.join(differences)} differ"
                changes.append(self._change(spec, Action.UPDATE, reason, current.name))
            elif differences:
                reason = f"{', '.join(differences)} differ"
                changes.append(self._change(spec, Action.UPDATE, reason, current.name))
            else:
                changes.append(Change(self.name, spec.name, Action.NOOP, "matches"))
        alias_of = {alias.lower(): spec.name for spec in desired for alias in spec.aliases}
        for label in actual:
            if label.name.lower() in matched:
                continue
            unknown = "not in labels.yml"
            if label.name.lower() in alias_of:
                # Both the alias and the configured name exist; only one can be renamed.
                unknown = f"alias of {alias_of[label.name.lower()]!r}, which already exists"
            if self.prune:
                usage = self._usage(label.name)
                changes.append(
                    Change(
                        self.name,
                        label.name,
                        Action.DELETE,
                        f"{unknown}; used by {_describe_usage(usage)}",
                        {"current_name": label.name, "usage": usage},
                    )
                )
            else:
                changes.append(
                    Change(
                        self.name,
                        label.name,
                        Action.SKIPPED,
                        f"{unknown}; kept (delete with --prune)",
                    )
                )
        return changes

    def apply(self, change: Change) -> None:
        """Create, update, rename or delete one label."""
        details = change.details
        if change.action is Action.CREATE:
            body = {key: details[key] for key in ("name", "color", "description")}
            try:
                self.client.request("POST", f"/repos/{self.repo}/labels", json=body)
            except GitHubError as exc:
                # The label was created meanwhile, for example by a parallel run; update it.
                if exc.status != 422:
                    raise
                self._update(details["name"], body)
        elif change.action is Action.UPDATE:
            body = {
                "new_name": details["name"],
                "color": details["color"],
                "description": details["description"],
            }
            self._update(details["current_name"], body)
        elif change.action is Action.DELETE:
            self.client.request("DELETE", self._label_url(details["current_name"]))
        else:
            raise ValueError(f"cannot apply {change.action} to a label")

    def _update(self, current_name: str, body: Mapping[str, Any]) -> None:
        self.client.request("PATCH", self._label_url(current_name), json=dict(body))

    def _label_url(self, name: str) -> str:
        return f"/repos/{self.repo}/labels/{quote(name, safe='')}"

    def _change(
        self, spec: LabelSpec, action: Action, reason: str, current_name: str | None
    ) -> Change:
        details: dict[str, Any] = {
            "name": spec.name,
            "color": spec.color,
            "description": spec.description,
        }
        if current_name is not None:
            details["current_name"] = current_name
        return Change(self.name, spec.name, action, reason, details)

    def _usage(self, name: str) -> int | None:
        """Return the number of issues and pull requests with the label, or None if unknown."""
        if '"' in name:
            return None
        query = f'repo:{self.repo} label:"{name}"'
        try:
            result = self.client.get_json("/search/issues", params={"q": query, "per_page": 1})
        except GitHubError:
            return None
        count = result.get("total_count") if isinstance(result, dict) else None
        return count if isinstance(count, int) else None


def _differences(current: ActualLabel, spec: LabelSpec) -> list[str]:
    differences = []
    if current.name != spec.name:
        differences.append("name")
    if current.color.lower() != spec.color.lower():
        differences.append("color")
    if current.description != spec.description:
        differences.append("description")
    return differences


def _describe_usage(usage: int | None) -> str:
    if usage is None:
        return "an unknown number of issues and pull requests"
    return f"{usage} issue(s) and pull request(s)"
