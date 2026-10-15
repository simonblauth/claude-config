# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Export a vault's projects, tasks, log and daily notes as JSON row files.

Usage: export.py VAULT OUT_DIR

Writes vault-projects.json, vault-tasks.json, vault-log.json and vault-days.json
to OUT_DIR, one array of row objects each, and prints one `name rows` line per file.
Text is plain: [[links]] become note titles, and markdown emphasis is dropped,
so the dashboard can show it with textContent.
"""

import datetime
import json
import re
import sys
from pathlib import Path

import yaml

LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\](s?)")
SECTION = re.compile(r"^## +(.+?)\s*$", re.MULTILINE)
TASK = re.compile(r"^- \[ \] (.*)$")
LOG = re.compile(r"^- (\d{4}-\d{2}(?:-\d{2})?) (.*)$")
TAG = re.compile(r"\s(?:@(\S+)|due:(\S+)|every:(\S+)|waiting:(\S+))")
NUMBERED = re.compile(r"^\d+\. (.*)$")
WHO = re.compile(r"^(agent|user) · \[\[([^\]|#]+)[^\]]*\]\]: (.*)$")


def frontmatter(text):
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    return yaml.safe_load(text[4:end]) or {}, text[end + 5 :]


def sections(body):
    parts = SECTION.split(body)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def short_title(title):
    # Person titles may end in a parenthesised short name, as in "Ada Lovelace (Al)".
    return re.sub(r"\s*\(.*?\)\s*$", "", str(title))


def iso(value):
    return value.isoformat() if isinstance(value, datetime.date) else str(value or "")


class Vault:
    def __init__(self, root):
        self.root = root
        self.titles = {}
        for path in root.glob("*/*.md"):
            fm, _ = frontmatter(path.read_text(encoding="utf-8"))
            if fm.get("title"):
                self.titles[path.stem] = short_title(fm["title"])
        self.project_files = sorted((root / "projects").glob("*.md"))
        self.project_slugs = {p.stem for p in self.project_files}

    def title(self, slug):
        return self.titles.get(slug, slug)

    def plain(self, text):
        def sub(m):
            label = m.group(2) or self.title(m.group(1))
            return label if label.endswith("s") else label + m.group(3)
        return LINK.sub(sub, text).replace("**", "").replace("`", "").strip()

    def linked_project(self, text):
        slugs = [m.group(1) for m in LINK.finditer(text) if m.group(1) in self.project_slugs]
        return slugs[-1] if slugs else ""


def parse_tasks(vault, slug, title, focus, next_section):
    tasks, current = [], None
    for line in next_section.splitlines():
        m = TASK.match(line)
        if m:
            raw = " " + m.group(1)
            owner, due, every, waiting = "", "", "", []
            for t in TAG.finditer(raw):
                owner = t.group(1) or owner
                due = t.group(2) or due
                every = t.group(3) or every
                if t.group(4):
                    waiting.append(vault.title(t.group(4)))
            current = {
                "id": f"{slug}-{len(tasks) + 1}",
                "project": slug,
                "project_title": title,
                "focus": focus,
                "text": vault.plain(TAG.sub("", raw)),
                "details": "",
                "owner": owner,
                "due": due,
                "every": every,
                "waiting_on": ", ".join(waiting),
            }
            tasks.append(current)
        elif current and line.startswith("  - "):
            current["details"] += ("; " if current["details"] else "") + vault.plain(line[4:])
    return tasks


def parse_log(vault, slug, title, log_section):
    entries = []
    for line in log_section.splitlines():
        m = LOG.match(line)
        if not m:
            continue
        date, text = m.groups()
        kind = next((k for k in ("done", "dropped") if text.startswith(k + ":")), "event")
        if kind != "event":
            text = text.split(":", 1)[1]
        entries.append({
            "id": f"{slug}-{len(entries) + 1}",
            "project": slug,
            "project_title": title,
            "date": date,
            "kind": kind,
            "text": vault.plain(text),
        })
    return entries


def export_projects(vault):
    projects, tasks, log = [], [], []
    for path in vault.project_files:
        fm, body = frontmatter(path.read_text(encoding="utf-8"))
        sec = sections(body)
        slug, title = path.stem, short_title(fm.get("title", path.stem))
        p_tasks = parse_tasks(vault, slug, title, fm.get("focus", ""), sec.get("Next", ""))
        p_log = parse_log(vault, slug, title, sec.get("Log", ""))
        state = vault.plain(sec.get("State", ""))
        projects.append({
            "slug": slug,
            "title": title,
            "status": fm.get("status", ""),
            "focus": fm.get("focus", ""),
            "created": iso(fm.get("created")),
            "updated": iso(fm.get("updated")),
            "summary": re.split(r"(?<=[.!?])\s", state, maxsplit=1)[0] if state else "",
            "state": state,
            "people": ", ".join(vault.title(s) for s in fm.get("people") or []),
            "waiting_on": ", ".join(vault.title(s) for s in fm.get("waiting_on") or []),
            "open_tasks": len(p_tasks),
            "waiting_tasks": sum(bool(t["waiting_on"]) for t in p_tasks),
            "log_entries": len(p_log),
            "last_activity": max((e["date"] for e in p_log if len(e["date"]) == 10), default=""),
            "ideas": sum(line.startswith("- ") for line in sec.get("Ideas", "").splitlines()),
        })
        tasks += p_tasks
        log += p_log
    return projects, tasks, log


def export_day(vault, path):
    date, rows = path.stem, []
    sec = sections(path.read_text(encoding="utf-8"))

    def add(section, text, who="", shown=None):
        rows.append({
            "id": f"{date}-{len(rows) + 1}",
            "date": date,
            "section": section,
            "who": who,
            "project": vault.linked_project(text),
            "text": vault.plain(text if shown is None else shown),
        })

    part = "brief"
    for line in sec.get("Brief", "").splitlines():
        if line.startswith("Outcomes for the week"):
            part = "outcome"
        elif line.startswith("Today"):
            part = "brief"
        elif line.startswith("Meetings:"):
            for meeting in line.removeprefix("Meetings:").strip().rstrip(".").split(", "):
                add("meeting", meeting)
        elif line.startswith("Decisions:"):
            for decision in re.split(r"(?<=\.)\s+", line.removeprefix("Decisions:").strip()):
                add("decision", decision)
        elif m := NUMBERED.match(line):
            who = WHO.match(m.group(1)) if part == "brief" else None
            if who:
                add("brief", f"[[{who.group(2)}]]", who.group(1), shown=who.group(3))
            else:
                add(part, m.group(1))

    for name, section in (("Captures", "capture"), ("Claude did", "claude_did")):
        for line in sec.get(name, "").splitlines():
            if line.startswith("- "):
                add(section, line[2:])

    part = None
    for line in sec.get("Wrap", "").splitlines():
        if line.startswith("Done"):
            part = "done"
        elif line.startswith("Moves to tomorrow"):
            part = "moves"
        elif part and line.startswith("- "):
            add(part, line[2:])
    return rows


def main(vault_dir, out_dir):
    vault = Vault(vault_dir)
    projects, tasks, log = export_projects(vault)
    days = [row for path in sorted((vault_dir / "daily").glob("*.md")) for row in export_day(vault, path)]
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in (("projects", projects), ("tasks", tasks), ("log", log), ("days", days)):
        (out_dir / f"vault-{name}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(name, len(rows))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(Path(sys.argv[1]).expanduser(), Path(sys.argv[2]).expanduser())
