"""Verify consistency of template-dev/. Usage: python -I template-dev/tools/verify_backlog.py [template-dev-dir]"""

import re
import sys
from pathlib import Path

ROOT = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent).resolve()
errors = []
REQUIRED = [
    "id",
    "title",
    "epic",
    "phase",
    "status",
    "priority",
    "effort",
    "target_repo",
    "spec_refs",
    "dependencies",
    "blocked_by_decisions",
    "agent_ready",
    "related_issues",
    "created_at",
    "updated_at",
]
ENUMS = {
    "status": {"draft", "planned", "active", "implemented", "deprecated", "archived"},
    "priority": {"critical", "high", "medium", "low"},
    "effort": {"xs", "s", "m", "l", "xl"},
    "target_repo": {
        "universal-project-template",
        "engineering-bootstrap",
        "engineering-workflows",
        "dashboard",
    },
    "agent_ready": {"true", "false"},
    "phase": {"1", "2", "3", "4", "5"},
}
SECTIONS = [
    "## Objective",
    "## Background",
    "## Scope",
    "### Out of Scope",
    "## Deliverables",
    "## Requirements",
    "## Tasks",
    "## Acceptance Criteria",
    "## Verification",
    "## Agent Notes",
]


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        key, sep, value = line.partition(":")
        if not sep:
            return None
        value = value.strip()
        if value.startswith("["):
            if not value.endswith("]"):
                return None
            fm[key] = [
                v.strip().strip('"') for v in value[1:-1].split(",") if v.strip()
            ]
        else:
            fm[key] = value.strip('"')
    return fm


feats = {}
for p in sorted((ROOT / "features").glob("FEAT-*.md")):
    text = p.read_text(encoding="utf-8")
    fm = frontmatter(text)
    if fm is None:
        errors.append(f"{p.name}: invalid frontmatter")
        continue
    missing = [k for k in REQUIRED if k not in fm]
    if missing:
        errors.append(f"{p.name}: missing keys {missing}")
    for k, allowed in ENUMS.items():
        if fm.get(k) not in allowed:
            errors.append(f"{p.name}: {k}={fm.get(k)!r} not allowed")
    if not p.name.startswith(fm.get("id", "?") + "-"):
        errors.append(f"{p.name}: id {fm.get('id')} does not match file name")
    if fm.get("id") in feats:
        errors.append(f"duplicate id {fm['id']}")
    if f"# {fm.get('id')}: {fm.get('title')}" not in text:
        errors.append(f"{p.name}: H1 does not match id/title")
    for s in SECTIONS:
        if f"\n{s}\n" not in text:
            errors.append(f"{p.name}: missing section {s}")
    if fm.get("blocked_by_decisions") and fm.get("agent_ready") == "true":
        errors.append(f"{p.name}: agent_ready true despite blocking decisions")
    fm["_text"], fm["_file"] = text, p.name
    feats[fm["id"]] = fm

decisions = set(
    re.findall(
        r"^\| (DEC-\d\d) \|",
        (ROOT / "open-decisions.md").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
)
for fid, fm in feats.items():
    for d in fm["dependencies"]:
        if d not in feats:
            errors.append(f"{fid}: unknown dependency {d}")
        elif int(feats[d]["phase"]) > int(fm["phase"]):
            errors.append(f"{fid}: depends on later-phase {d}")
    for d in fm["blocked_by_decisions"]:
        if d not in decisions:
            errors.append(f"{fid}: unknown decision {d}")

# cycles
state = {}


def visit(n, path):
    if state.get(n) == 1:
        errors.append("cycle: " + " -> ".join(path + [n]))
        return
    if state.get(n) == 2:
        return
    state[n] = 1
    for d in feats[n]["dependencies"]:
        if d in feats:
            visit(d, path + [n])
    state[n] = 2


for n in feats:
    visit(n, [])

# backlog: every feature exactly once, rank respects dependencies, cells match frontmatter
backlog = (ROOT / "backlog.md").read_text(encoding="utf-8")
rows = re.findall(
    r"^\| (\d+) \| \[(FEAT-\d{3})\]\(features/([^)]+)\) \|(.*)$", backlog, re.MULTILINE
)
order = [r[1] for r in rows]
for fid in feats:
    if order.count(fid) != 1:
        errors.append(f"{fid}: appears {order.count(fid)} times in backlog")
for i, fid in enumerate(order):
    for d in feats.get(fid, {}).get("dependencies", []):
        if d in order and order.index(d) > i:
            errors.append(f"backlog: {fid} ranked before its dependency {d}")
for rank, fid, file, rest in rows:
    cells = [c.strip() for c in rest.split("|")]
    if feats[fid]["_file"] != file or cells[-2] != feats[fid]["status"]:
        errors.append(f"backlog row {fid}: file or status mismatch")

# epics: every feature in exactly one epic table, matching its epic field
epic_files = sorted((ROOT / "epics").glob("EPIC-*.md"))
if len(epic_files) != 11:
    errors.append(f"expected 11 epics, found {len(epic_files)}")
seen = {}
for e in epic_files:
    eid = e.name[:7]
    for fid in re.findall(r"^\| \[(FEAT-\d{3})\]", e.read_text(encoding="utf-8"), re.MULTILINE):
        seen.setdefault(fid, []).append(eid)
for fid, fm in feats.items():
    if seen.get(fid) != [fm["epic"]]:
        errors.append(f"{fid}: epic tables {seen.get(fid)} vs frontmatter {fm['epic']}")

# roadmap: every feature mentioned at least once, explicitly or via a range
roadmap = (ROOT / "roadmap.md").read_text(encoding="utf-8")
covered = set(re.findall(r"FEAT-\d{3}", roadmap))
for a, b in re.findall(r"FEAT-(\d{3}) to FEAT-(\d{3})", roadmap):
    covered |= {f"FEAT-{n:03d}" for n in range(int(a), int(b) + 1)}
for fid in feats:
    if fid not in covered:
        errors.append(f"{fid}: missing in roadmap")


# links and anchors
def slug(h):
    h = h.strip().lower()
    h = re.sub(r"[^\w\- ]", "", h, flags=re.UNICODE)
    return h.replace(" ", "-")


anchor_cache = {}


def anchors(path):
    if path not in anchor_cache:
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        anchor_cache[path] = {slug(m) for m in re.findall(r"^#{1,6} (.*)$", text, re.MULTILINE)}
    return anchor_cache[path]


for md in ROOT.rglob("*.md"):
    text = re.sub(r"```.*?```", "", md.read_text(encoding="utf-8"), flags=re.DOTALL)
    for target in re.findall(r"\]\(([^)\s]+)\)", text):
        if re.match(r"[a-z]+:", target):
            continue
        file_part, _, frag = target.partition("#")
        dest = (md.parent / file_part).resolve() if file_part else md
        if not dest.exists():
            errors.append(f"{md.relative_to(ROOT)}: broken link {target}")
        elif frag and dest.is_file() and frag not in anchors(dest):
            errors.append(f"{md.relative_to(ROOT)}: missing anchor {target}")

# template-only requirements
checks = {
    "FEAT-003": ["template-dev"],
    "FEAT-013": ["template_only_paths", "is_template"],
    "FEAT-015": ["REPO-TEMPLATE-ONLY", "REPO-DEAD-LINK-TEMPLATE", "is_template"],
    "FEAT-028": ["template_only_paths", "is_template"],
    "FEAT-030": ["template-dev"],
}
for fid, needles in checks.items():
    for n in needles:
        if n not in feats[fid]["_text"]:
            errors.append(f"{fid}: template-only requirement '{n}' missing")

print(
    f"features: {len(feats)}, backlog rows: {len(rows)}, epics: {len(epic_files)}, decisions: {len(decisions)}"
)
for e in errors:
    print("ERROR", e)
print("OK" if not errors else f"{len(errors)} error(s)")
sys.exit(1 if errors else 0)
