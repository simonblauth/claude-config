#!/usr/bin/env python3
"""Vendor, install and drift-check Claude Code skills.

  vendor [name ...]   fetch upstream into skills/, record sha + content hash
  install             copy repo content into the Claude config dir
  check [--daily]     report upstream and local drift, change nothing

Nothing is symlinked and nothing auto-applies. Windows, WSL and Linux take
the same path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent
SOURCES = REPO / "sources.tsv"
SKILLS = REPO / "skills"
RULES = REPO / "rules"
PATCHES = REPO / "patches"
CACHE = REPO / ".cache"

HEADER = "# canonical\trepo\tpath\tref\tsha\tcontent"
MANIFEST_NAME = ".claude-config-manifest.json"
STAMP_NAME = ".claude-config-stamp"
STALE_SECONDS = 24 * 60 * 60


def config_dir() -> Path:
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(env).expanduser() if env else Path.home() / ".claude"


@dataclass
class Source:
    name: str
    repo: str
    path: str
    ref: str
    sha: str
    content: str

    @property
    def pinned(self) -> bool:
        return self.sha != "-"


def read_sources() -> list[Source]:
    out = []
    for line in SOURCES.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        out.append(Source(*line.split("\t")))
    return out


def write_sources(sources: list[Source]) -> None:
    rows = [HEADER]
    rows += ["\t".join([s.name, s.repo, s.path, s.ref, s.sha, s.content]) for s in sources]
    SOURCES.write_text("\n".join(rows) + "\n", encoding="utf-8")


def run(cmd: list[str], cwd: Path | None = None) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if r.returncode:
        raise RuntimeError(f"{' '.join(cmd)}\n{r.stderr.strip()}")
    return r.stdout.strip()


def tree_hash(root: Path) -> str:
    """Stable hash of a directory's contents, independent of mtimes."""
    h = hashlib.sha256()
    for f in sorted(p for p in root.rglob("*") if p.is_file()):
        h.update(f.relative_to(root).as_posix().encode())
        h.update(b"\0")
        h.update(f.read_bytes())
        h.update(b"\0")
    return h.hexdigest()[:16]


def clone(repo: str, ref: str) -> Path:
    """Shallow clone into the cache, or update an existing one."""
    CACHE.mkdir(exist_ok=True)
    dest = CACHE / hashlib.sha256(repo.encode()).hexdigest()[:12]
    if dest.exists():
        run(["git", "-C", str(dest), "fetch", "--depth", "1", "--quiet", "origin", ref])
        run(["git", "-C", str(dest), "checkout", "--quiet", "--force", "FETCH_HEAD"])
    else:
        run(["git", "clone", "--depth", "1", "--branch", ref, "--quiet", repo, str(dest)])
    return dest


def remote_sha(repo: str, ref: str) -> str:
    out = run(["git", "ls-remote", repo, ref])
    return out.split()[0] if out else ""


def rename_map(sources: list[Source]) -> dict[str, str]:
    """superpowers:<upstream-dir> -> our bare canonical name."""
    return {f"superpowers:{Path(s.path).name}": s.name for s in sources}


def rewrite_refs(root: Path, mapping: dict[str, str], upstream: str, canonical: str) -> int:
    """Point cross-references at our canonical names. Returns files touched."""
    touched = 0
    for f in sorted(p for p in root.rglob("*") if p.is_file()):
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        new = text
        for old, repl in mapping.items():
            new = new.replace(old, repl)
        if f.name == "SKILL.md" and upstream != canonical:
            new = new.replace(f"name: {upstream}", f"name: {canonical}", 1)
        if new != text:
            f.write_text(new, encoding="utf-8")
            touched += 1
    return touched


def find_dangling(root: Path) -> set[str]:
    """Refs to skills we did not vendor, left pointing at nothing."""
    found = set()
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for m in re.finditer(r"superpowers:[a-z0-9-]+", text):
            found.add(m.group(0))
    return found


def apply_patch(name: str, dest: Path) -> str:
    patch = PATCHES / f"{name}.patch"
    if not patch.exists():
        return ""
    try:
        run(["git", "apply", "--directory", dest.relative_to(REPO).as_posix(), str(patch)], cwd=REPO)
        return "patched"
    except RuntimeError as e:
        return f"PATCH FAILED ({e.args[0].splitlines()[-1] if e.args else 'unknown'})"


def cmd_vendor(args) -> int:
    sources = read_sources()
    wanted = set(args.names) if args.names else {s.name for s in sources}
    mapping = rename_map(sources)
    SKILLS.mkdir(exist_ok=True)
    changed = False

    for s in sources:
        if s.name not in wanted:
            continue
        repo_dir = clone(s.repo, s.ref)
        src = repo_dir / s.path
        if not src.is_dir():
            print(f"  {s.name}: MISSING upstream path {s.path}")
            continue
        sha = run(["git", "-C", str(repo_dir), "rev-parse", "HEAD"])
        pristine = tree_hash(src)

        dest = SKILLS / s.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)

        # SKILL.md frontmatter carries the upstream dir name; ours is canonical.
        touched = rewrite_refs(dest, mapping, Path(s.path).name, s.name)
        note = apply_patch(s.name, dest)
        dangling = find_dangling(dest)

        if s.sha != sha or s.content != pristine:
            changed = True
        s.sha, s.content = sha, pristine
        bits = [f"{sha[:12]}"]
        if touched:
            bits.append(f"{touched} file(s) rewritten")
        if note:
            bits.append(note)
        if dangling:
            bits.append("DANGLING -> " + ", ".join(sorted(dangling)))
        print(f"  {s.name:<32} {', '.join(bits)}")

    write_sources(sources)
    print("sources.tsv updated" if changed else "no upstream changes")
    return 0


def planned_files(cfg: Path) -> dict[str, bytes]:
    """Relative path under the config dir -> exact bytes we want there."""
    out: dict[str, bytes] = {}
    for base, prefix in ((SKILLS, "skills"), (RULES, "rules")):
        if not base.exists():
            continue
        for f in sorted(p for p in base.rglob("*") if p.is_file()):
            if f.name == ".gitkeep":
                continue
            out[f"{prefix}/{f.relative_to(base).as_posix()}"] = f.read_bytes()
    out["CLAUDE.md"] = (REPO / "CLAUDE.md").read_bytes()
    out["settings.json"] = render_settings()
    return out


def render_settings() -> bytes:
    """Substitute this machine's interpreter and repo path into the hook."""
    text = (REPO / "settings.json").read_text(encoding="utf-8")
    text = text.replace("{{PYTHON}}", json_escape(sys.executable))
    text = text.replace("{{REPO}}", json_escape(str(REPO)))
    return text.encode("utf-8")


def json_escape(s: str) -> str:
    return json.dumps(s)[1:-1]


def cmd_install(args) -> int:
    cfg = config_dir()
    cfg.mkdir(parents=True, exist_ok=True)
    # Always present, even when empty: rules/ is where machine-local files go.
    for keep in ("skills", "rules"):
        (cfg / keep).mkdir(exist_ok=True)
    manifest_path = cfg / MANIFEST_NAME
    previous = set()
    if manifest_path.exists():
        previous = set(json.loads(manifest_path.read_text(encoding="utf-8"))["paths"])

    planned = planned_files(cfg)
    written = 0
    for rel, data in sorted(planned.items()):
        target = cfg / rel
        if target.exists() and target.read_bytes() == data:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        written += 1
        print(f"  wrote   {rel}")

    # Only ever remove paths we put there ourselves.
    for rel in sorted(previous - set(planned)):
        target = cfg / rel
        if target.exists():
            target.unlink()
            print(f"  removed {rel}")
        parent = target.parent
        keep = {cfg, cfg / "skills", cfg / "rules"}
        while parent not in keep and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent

    manifest_path.write_text(
        json.dumps({"version": 1, "repo": str(REPO), "paths": sorted(planned)}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{written} file(s) written, {len(planned)} tracked, config dir {cfg}")
    return 0


def cmd_check(args) -> int:
    cfg = config_dir()
    stamp = cfg / STAMP_NAME
    if args.daily and stamp.exists():
        if time.time() - stamp.stat().st_mtime < STALE_SECONDS:
            return 0
    cfg.mkdir(parents=True, exist_ok=True)
    stamp.write_text(str(int(time.time())), encoding="utf-8")

    local = check_local(cfg)
    upstream = check_upstream() if not args.local_only else []

    if not local and not upstream:
        if not args.quiet:
            print("claude-config: no drift")
        return 0

    print("claude-config drift")
    for line in local:
        print(f"  local     {line}")
    for line in upstream:
        print(f"  upstream  {line}")
    print(f"  repo      {REPO}")
    return 0


def check_local(cfg: Path) -> list[str]:
    out = []
    planned = planned_files(cfg)
    for rel, data in sorted(planned.items()):
        target = cfg / rel
        if not target.exists():
            out.append(f"{rel} missing, run install")
        elif target.read_bytes() != data:
            out.append(f"{rel} differs from repo")
    return out


def check_upstream() -> list[str]:
    out = []
    sources = read_sources()
    by_repo: dict[tuple[str, str], list[Source]] = {}
    for s in sources:
        by_repo.setdefault((s.repo, s.ref), []).append(s)

    for (repo, ref), group in by_repo.items():
        try:
            head = remote_sha(repo, ref)
        except RuntimeError as e:
            out.append(f"{repo} unreachable ({e.args[0].splitlines()[-1]})")
            continue
        if not head or all(s.sha == head for s in group):
            continue
        # The repo moved. Only report skills whose own content actually changed.
        try:
            repo_dir = clone(repo, ref)
        except RuntimeError as e:
            out.append(f"{repo} fetch failed ({e.args[0].splitlines()[-1]})")
            continue
        for s in group:
            src = repo_dir / s.path
            if not src.is_dir():
                out.append(f"{s.name} vanished upstream at {s.path}")
            elif tree_hash(src) != s.content:
                out.append(f"{s.name} changed upstream, vendor {s.name} to review")
    return out


def main() -> int:
    p = argparse.ArgumentParser(prog="cc.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("vendor", help="fetch upstream skills into skills/")
    v.add_argument("names", nargs="*")
    v.set_defaults(func=cmd_vendor)

    i = sub.add_parser("install", help="copy repo content into the Claude config dir")
    i.set_defaults(func=cmd_install)

    c = sub.add_parser("check", help="report drift, change nothing")
    c.add_argument("--daily", action="store_true", help="no-op if run in the last 24h")
    c.add_argument("--quiet", action="store_true", help="print only when there is drift")
    c.add_argument("--local-only", action="store_true", help="skip the network")
    c.set_defaults(func=cmd_check)

    args = p.parse_args()
    try:
        return args.func(args)
    except RuntimeError as e:
        print(f"cc.py: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
