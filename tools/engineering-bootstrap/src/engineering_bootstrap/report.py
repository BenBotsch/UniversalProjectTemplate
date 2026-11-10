"""Human-readable and JSON reports of a run.

The JSON layout is versioned by ``report_version`` and described by
``schemas/report-<version>.schema.json`` in this package. A change that removes or renames a
field, or changes its meaning, needs a new major version.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from engineering_bootstrap import __version__
from engineering_bootstrap.engine import WRITE_ACTIONS, Action, Change

REPORT_VERSION = "1.0"
TOOL_NAME = "engineering-bootstrap"

Mode = Literal["dry-run", "apply"]


@dataclass(frozen=True)
class Report:
    """Result of one CLI run.

    Attributes:
        command: CLI subcommand, for example ``validate``.
        mode: ``dry-run`` or ``apply``.
        target: What the run worked on, for example a repository or a configuration directory.
        changes: All changes in execution order.
        generated_at: Time the report was created; injectable for tests.
    """

    command: str
    mode: Mode
    target: str
    changes: list[Change]
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def summary(self) -> dict[str, int]:
        """Number of changes per action, including actions with zero changes."""
        counts = Counter(change.action for change in self.changes)
        return {action.value: counts.get(action, 0) for action in Action}

    @property
    def failed(self) -> bool:
        """True if any change failed."""
        return any(change.action is Action.FAILED for change in self.changes)

    def to_dict(self) -> dict[str, Any]:
        """Return the report in the layout of the JSON schema."""
        return {
            "report_version": REPORT_VERSION,
            "tool": {"name": TOOL_NAME, "version": __version__},
            "command": self.command,
            "mode": self.mode,
            "target": self.target,
            "generated_at": self.generated_at.isoformat(timespec="seconds"),
            "summary": self.summary,
            "changes": [
                {
                    "resource": change.resource,
                    "key": change.key,
                    "action": change.action.value,
                    "reason": change.reason,
                    "details": dict(change.details),
                    "applied": change.applied,
                }
                for change in self.changes
            ],
        }


def render_json(report: Report) -> str:
    """Render the report as indented JSON with a trailing newline."""
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"


def render_text(report: Report) -> str:
    """Render the report for a terminal.

    Each change is one line; the footer states whether anything was written.
    """
    lines = [f"project-bootstrap {report.command} ({report.mode}): {report.target}"]
    width = max(len(action.value) for action in Action)
    for change in report.changes:
        marker = " (applied)" if change.applied else ""
        reason = f": {change.reason}" if change.reason else ""
        lines.append(
            f"  {change.action.value:<{width}}  {change.resource}/{change.key}{reason}{marker}"
        )
    summary = ", ".join(f"{count} {action}" for action, count in report.summary.items())
    lines.append(f"Summary: {summary}")
    if report.mode == "dry-run":
        if any(change.action in WRITE_ACTIONS for change in report.changes):
            lines.append("Dry run: nothing was changed. Run again with --apply to apply.")
        else:
            lines.append("Dry run: nothing was changed.")
    else:
        applied = sum(change.applied for change in report.changes)
        lines.append(f"Applied {applied} change(s).")
        if report.failed:
            lines.append(
                "Some changes failed. Changes marked (applied) were written; review them before"
                " you retry or roll back."
            )
    return "\n".join(lines) + "\n"
