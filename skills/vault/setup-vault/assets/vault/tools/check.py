# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Check vault notes against schema.yaml. Exit 1 and list errors if any."""

import datetime
import re
import sys
from pathlib import Path

import yaml

LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
SECTION = re.compile(r"^## +(.+?)\s*$", re.MULTILINE)
TASK_LINE = re.compile(r"^\s*- \[[ xX]\] .*$", re.MULTILINE)
DUE = re.compile(r"\bdue:(\S+)")
EVERY = re.compile(r"\bevery:(\S+)")
WAITING = re.compile(r"\bwaiting:(\S+)")


def split_frontmatter(text):
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    return yaml.safe_load(text[4:end]) or {}, text[end + 5 :]


def note_files(root, schema):
    dirs = [t["dir"] for t in schema["types"].values()] + schema["untyped_dirs"]
    files = [p for d in dirs for p in sorted((root / d).glob("*.md"))]
    files += [root / f for f in schema["untyped_files"] if (root / f).exists()]
    return files


def as_list(value):
    return value if isinstance(value, list) else [value]


def is_date(value):
    if isinstance(value, datetime.date):
        return True
    try:
        datetime.date.fromisoformat(str(value))
        return True
    except ValueError:
        return False


def check_typed(meta, body, rel_dir, schema, slugs):
    errors = []
    name = meta.get("type")
    spec = schema["types"].get(name)
    if spec is None:
        return [f"unknown type '{name}'"]
    if spec["dir"] != rel_dir:
        return [f"type '{name}' belongs in {spec['dir']}/"]

    allowed = set(schema["common_fields"]) | set(spec["fields"]) | set(spec.get("optional", []))
    for field in schema["common_fields"] + spec["fields"]:
        if field not in meta:
            errors.append(f"missing field '{field}'")
    for field in meta:
        if field not in allowed:
            errors.append(f"unknown field '{field}'")
    for field in schema["date_fields"]:
        if field in meta and not is_date(meta[field]):
            errors.append(f"{field}: '{meta[field]}' is not a YYYY-MM-DD date")
    for field, values in spec.get("enums", {}).items():
        if field in meta and meta[field] not in values:
            errors.append(f"{field} '{meta[field]}' not in {values}")
    for rule in spec.get("when", []):
        if meta.get(rule["field"]) == rule["value"]:
            for field in rule["require"]:
                if field not in meta:
                    errors.append(f"{rule['field']} '{rule['value']}' requires field '{field}'")
    for field in spec.get("links", []):
        for target in as_list(meta.get(field, [])):
            if target not in slugs:
                errors.append(f"{field}: no note '{target}'")

    headings = set(SECTION.findall(body))
    for section in spec["sections"]:
        if section not in headings:
            errors.append(f"missing section '{section}'")
    return errors


def check_tasks(body, schema, slugs):
    errors = []
    for line in TASK_LINE.findall(body):
        for due in DUE.findall(line):
            if not is_date(due):
                errors.append(f"invalid due date '{due}'")
        for every in EVERY.findall(line):
            if every not in schema["task_every"]:
                errors.append(f"invalid recurrence '{every}'")
        for target in WAITING.findall(line):
            if target not in slugs:
                errors.append(f"waiting: no note '{target}'")
    return errors


def check(root):
    root = Path(root)
    schema = yaml.safe_load((root / "schema.yaml").read_text())
    files = note_files(root, schema)
    untyped = set(schema["untyped_dirs"])

    errors = []
    seen = {}
    for path in files:
        rel = path.relative_to(root).as_posix()
        if path.stem in seen:
            errors.append(f"{rel}: duplicate slug '{path.stem}' (also {seen[path.stem]})")
        else:
            seen[path.stem] = rel
    slugs = set(seen)

    for path in files:
        rel = path.relative_to(root)
        rel_dir = rel.parent.as_posix()
        meta, body = split_frontmatter(path.read_text())
        found = []
        if rel_dir != "." and rel_dir not in untyped:
            if meta is None:
                found.append("missing frontmatter")
            else:
                found += check_typed(meta, body, rel_dir, schema, slugs)
        found += check_tasks(body, schema, slugs)
        found += [f"broken link [[{t}]]" for t in LINK.findall(body) if t.strip() not in slugs]
        errors += [f"{rel.as_posix()}: {e}" for e in found]
    return errors


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
    errors = check(root)
    for error in errors:
        print(error)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
