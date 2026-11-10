"""Plan and apply changes through pluggable resources.

A resource reads the actual state, states the desired state, computes the changes between them
and applies one change at a time. The engine contains no GitHub specifics, so resources can be
tested with fakes. It runs resources in dependency order and keeps going for independent
resources when one fails.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Any, Protocol

logger = logging.getLogger(__name__)

# Key of a change that concerns a resource as a whole, for example when reading it failed.
RESOURCE_KEY = "*"


class Action(StrEnum):
    """What a change does, or why it did nothing."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    NOOP = "noop"
    SKIPPED = "skipped"
    FAILED = "failed"


WRITE_ACTIONS = frozenset({Action.CREATE, Action.UPDATE, Action.DELETE})


@dataclass(frozen=True)
class Change:
    """One planned, applied, skipped or failed change.

    Attributes:
        resource: Name of the resource that produced the change.
        key: Identifier of the changed item inside the resource, for example a label name.
        action: The planned action; ``skipped`` or ``failed`` when it was not carried out.
        reason: Human-readable explanation.
        details: JSON-serializable data the resource needs to apply the change, for example the
            desired values. It must never contain secrets.
        applied: True once the change was written.
    """

    resource: str
    key: str
    action: Action
    reason: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)
    applied: bool = False


class Resource(Protocol):
    """A kind of setting that the engine can plan and apply.

    Attributes:
        name: Unique name, used in reports and in ``depends_on`` of other resources.
        depends_on: Names of resources that must succeed before this one runs.
    """

    name: str
    depends_on: Sequence[str]

    def read_actual(self) -> Any:
        """Return the current state."""
        ...

    def desired(self) -> Any:
        """Return the state the configuration asks for."""
        ...

    def diff(self, actual: Any, desired: Any) -> list[Change]:
        """Return the changes from ``actual`` to ``desired``; ``noop`` for matching items."""
        ...

    def apply(self, change: Change) -> None:
        """Write one change of action ``create``, ``update`` or ``delete``."""
        ...


def order_resources(resources: Sequence[Resource]) -> list[Resource]:
    """Sort resources so that each comes after its dependencies.

    Resources without a mutual dependency keep their given order.

    Args:
        resources: The resources to run.

    Returns:
        The resources in execution order.

    Raises:
        ValueError: If names are duplicated, a dependency is unknown or dependencies form a
            cycle.
    """
    by_name: dict[str, Resource] = {}
    for resource in resources:
        if resource.name in by_name:
            raise ValueError(f"duplicate resource name {resource.name!r}")
        by_name[resource.name] = resource
    for resource in resources:
        for dependency in resource.depends_on:
            if dependency not in by_name:
                raise ValueError(f"resource {resource.name!r} depends on unknown {dependency!r}")
    ordered: list[Resource] = []
    done: set[str] = set()
    pending = list(resources)
    while pending:
        ready = next((r for r in pending if set(r.depends_on) <= done), None)
        if ready is None:
            names = ", ".join(sorted(r.name for r in pending))
            raise ValueError(f"dependency cycle between resources: {names}")
        ordered.append(ready)
        done.add(ready.name)
        pending.remove(ready)
    return ordered


class Engine:
    """Run resources as a plan (dry run) or apply their changes.

    Args:
        resources: The resources to run.
        allow_destructive: Apply ``delete`` changes. Without it they are reported as
            ``skipped``, so that a run never removes something unless asked to.

    Raises:
        ValueError: See :func:`order_resources`.
    """

    def __init__(self, resources: Sequence[Resource], *, allow_destructive: bool = False) -> None:
        self._resources = order_resources(resources)
        self._allow_destructive = allow_destructive

    def run(self, *, apply: bool) -> list[Change]:
        """Plan every resource and, if ``apply`` is true, write the planned changes.

        A resource whose reading, planning or applying fails is reported with ``failed``
        changes; resources that depend on it are ``skipped``, all others still run.

        Args:
            apply: Write changes; otherwise only report what would change.

        Returns:
            All changes in execution order. In apply mode, written changes have
            ``applied=True``, so a partial run can be reviewed and rolled back.
        """
        changes: list[Change] = []
        unsuccessful: set[str] = set()
        for resource in self._resources:
            blocked = [name for name in resource.depends_on if name in unsuccessful]
            if blocked:
                unsuccessful.add(resource.name)
                reason = f"dependency {', '.join(blocked)} did not succeed"
                changes.append(Change(resource.name, RESOURCE_KEY, Action.SKIPPED, reason))
                continue
            resource_changes = self._run_resource(resource, apply=apply)
            if any(change.action is Action.FAILED for change in resource_changes):
                unsuccessful.add(resource.name)
            changes.extend(resource_changes)
        return changes

    def _run_resource(self, resource: Resource, *, apply: bool) -> list[Change]:
        try:
            planned = resource.diff(resource.read_actual(), resource.desired())
        except Exception as exc:
            # Any error of one resource must not stop independent resources.
            logger.debug("planning %s failed", resource.name, exc_info=True)
            reason = f"planning failed: {exc}"
            return [Change(resource.name, RESOURCE_KEY, Action.FAILED, reason)]
        results = []
        for change in planned:
            if change.action not in WRITE_ACTIONS:
                results.append(change)
            elif change.action is Action.DELETE and not self._allow_destructive:
                reason = f"delete not allowed without destructive mode: {change.reason}"
                results.append(replace(change, action=Action.SKIPPED, reason=reason))
            elif not apply:
                results.append(change)
            else:
                results.append(self._apply(resource, change))
        return results

    @staticmethod
    def _apply(resource: Resource, change: Change) -> Change:
        try:
            resource.apply(change)
        except Exception as exc:
            logger.debug("applying %s %s failed", resource.name, change.key, exc_info=True)
            reason = f"{change.action} failed: {exc}"
            return replace(change, action=Action.FAILED, reason=reason)
        return replace(change, applied=True)
