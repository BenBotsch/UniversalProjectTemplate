"""Tests for the plan and apply engine, using an in-memory fake resource."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import pytest

from engineering_bootstrap.engine import RESOURCE_KEY, Action, Change, Engine, order_resources


@dataclass
class FakeResource:
    """Key/value store resource: creates, updates and deletes keys to match ``wanted``."""

    name: str
    wanted: dict[str, str]
    store: dict[str, str] = field(default_factory=dict)
    depends_on: Sequence[str] = ()
    fail_read: bool = False
    fail_keys: frozenset[str] = frozenset()
    applied: list[Change] = field(default_factory=list)

    def read_actual(self) -> dict[str, str]:
        if self.fail_read:
            raise RuntimeError("read failed")
        return dict(self.store)

    def desired(self) -> dict[str, str]:
        return dict(self.wanted)

    def diff(self, actual: dict[str, str], desired: dict[str, str]) -> list[Change]:
        changes = []
        for key, value in desired.items():
            if key not in actual:
                changes.append(Change(self.name, key, Action.CREATE, "missing", {"value": value}))
            elif actual[key] != value:
                changes.append(Change(self.name, key, Action.UPDATE, "differs", {"value": value}))
            else:
                changes.append(Change(self.name, key, Action.NOOP, "matches"))
        for key in actual.keys() - desired.keys():
            changes.append(Change(self.name, key, Action.DELETE, "not configured"))
        return changes

    def apply(self, change: Change) -> None:
        if change.key in self.fail_keys:
            raise RuntimeError(f"cannot write {change.key}")
        self.applied.append(change)
        if change.action is Action.DELETE:
            del self.store[change.key]
        else:
            self.store[change.key] = change.details["value"]


def actions(changes: list[Change]) -> dict[str, Action]:
    return {f"{c.resource}/{c.key}": c.action for c in changes}


def test_dry_run_reports_changes_without_writing() -> None:
    resource = FakeResource("labels", {"bug": "red", "docs": "blue"}, {"bug": "green"})

    changes = Engine([resource]).run(apply=False)

    assert actions(changes) == {"labels/bug": Action.UPDATE, "labels/docs": Action.CREATE}
    assert resource.store == {"bug": "green"}
    assert resource.applied == []
    assert not any(c.applied for c in changes)


def test_apply_writes_changes_and_marks_them_applied() -> None:
    resource = FakeResource("labels", {"bug": "red", "docs": "blue"}, {"bug": "green"})

    changes = Engine([resource]).run(apply=True)

    assert resource.store == {"bug": "red", "docs": "blue"}
    assert all(c.applied for c in changes)


def test_second_apply_with_unchanged_config_is_all_noop() -> None:
    resource = FakeResource("labels", {"bug": "red", "docs": "blue"}, {"bug": "green"})
    engine = Engine([resource])
    engine.run(apply=True)
    resource.applied.clear()

    second = engine.run(apply=True)

    assert {c.action for c in second} == {Action.NOOP}
    assert resource.applied == []
    assert resource.store == {"bug": "red", "docs": "blue"}


def test_delete_is_skipped_unless_destructive_mode() -> None:
    resource = FakeResource("labels", {}, {"old": "x"})

    changes = Engine([resource]).run(apply=True)

    assert actions(changes) == {"labels/old": Action.SKIPPED}
    assert "delete not allowed" in changes[0].reason
    assert resource.store == {"old": "x"}


def test_delete_is_applied_in_destructive_mode() -> None:
    resource = FakeResource("labels", {}, {"old": "x"})

    changes = Engine([resource], allow_destructive=True).run(apply=True)

    assert actions(changes) == {"labels/old": Action.DELETE}
    assert changes[0].applied
    assert resource.store == {}


def test_failed_read_continues_with_independent_resources_and_skips_dependants() -> None:
    broken = FakeResource("branches", {"develop": "main"}, fail_read=True)
    dependant = FakeResource("rulesets", {"r": "1"}, depends_on=["branches"])
    independent = FakeResource("labels", {"bug": "red"})

    changes = Engine([broken, dependant, independent]).run(apply=True)

    assert actions(changes) == {
        f"branches/{RESOURCE_KEY}": Action.FAILED,
        f"rulesets/{RESOURCE_KEY}": Action.SKIPPED,
        "labels/bug": Action.CREATE,
    }
    assert "read failed" in changes[0].reason
    assert dependant.applied == []
    assert independent.store == {"bug": "red"}


def test_failed_apply_keeps_completed_changes_in_the_result() -> None:
    resource = FakeResource("labels", {"a": "1", "b": "2", "c": "3"}, fail_keys=frozenset({"b"}))
    dependant = FakeResource("other", {"x": "1"}, depends_on=["labels"])

    changes = Engine([resource, dependant]).run(apply=True)

    by_key = {c.key: c for c in changes if c.resource == "labels"}
    assert by_key["a"].applied
    assert by_key["b"].action is Action.FAILED
    assert by_key["b"].reason == "create failed: cannot write b"
    assert not by_key["b"].applied
    assert by_key["c"].applied
    assert actions(changes)[f"other/{RESOURCE_KEY}"] is Action.SKIPPED


def test_resources_run_after_their_dependencies() -> None:
    order: list[str] = []

    class Recording(FakeResource):
        def read_actual(self) -> dict[str, Any]:
            order.append(self.name)
            return super().read_actual()

    first = Recording("rulesets", {}, depends_on=["branches"])
    second = Recording("branches", {})
    third = Recording("labels", {})

    Engine([first, second, third]).run(apply=False)

    assert order == ["branches", "rulesets", "labels"]


@pytest.mark.parametrize(
    ("resources", "message"),
    [
        ([FakeResource("a", {}), FakeResource("a", {})], "duplicate resource name"),
        ([FakeResource("a", {}, depends_on=["x"])], "depends on unknown"),
        (
            [FakeResource("a", {}, depends_on=["b"]), FakeResource("b", {}, depends_on=["a"])],
            "dependency cycle",
        ),
    ],
)
def test_invalid_resource_graphs_are_rejected(resources: list[FakeResource], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        order_resources(resources)
