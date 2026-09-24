#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Vendor, install and drift-check Claude Code and Codex skills.

  vendor [name ...]   fetch upstream into skills/, record sha, copy licenses
  install --target claude|codex|all   copy instructions, skills and settings
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
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent
SOURCES = REPO / "sources.tsv"
SUPPORT_SOURCES = REPO / "support-sources.tsv"
SKILLS = REPO / "skills"
RULES = REPO / "rules"
PATCHES = REPO / "patches"
CACHE = REPO / ".cache"
LICENSES = REPO / "licenses"
NOTICE = REPO / "NOTICE.md"

HEADER = "# canonical\trepo\tpath\tref\tsha\tcontent"
MANIFEST_NAME = ".claude-config-manifest.json"
STAMP_NAME = ".claude-config-stamp"
LICENSE_NAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")
COPYRIGHT = re.compile(r"^[ \t]*(Copyright\b.*?)[ \t]*$", re.MULTILINE)


def today() -> str:
    return time.strftime("%Y-%m-%d")


def config_dir(target: str = "claude") -> Path:
    env = os.environ.get("CLAUDE_CONFIG_DIR" if target == "claude" else "CODEX_HOME")
    return Path(env).expanduser().resolve() if env else Path.home() / f".{target}"


def install_roots(target: str) -> dict[str, Path]:
    cfg = config_dir(target)
    if target == "claude":
        return {"config": cfg}
    skills = os.environ.get("CODEX_SKILLS_DIR")
    return {"config": cfg, "skills": Path(skills).expanduser().resolve() if skills
            else Path.home() / ".agents" / "skills"}


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


def read_sources(path: Path = SOURCES) -> list[Source]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        out.append(Source(*line.split("\t")))
    return out


def write_sources(sources: list[Source], path: Path = SOURCES) -> None:
    rows = [HEADER]
    rows += ["\t".join([s.name, s.repo, s.path, s.ref, s.sha, s.content]) for s in sources]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def run(cmd: list[str], cwd: Path | None = None) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if r.returncode:
        raise RuntimeError(f"{' '.join(cmd)}\n{r.stderr.strip()}")
    return r.stdout.strip()


def tree_hash(root: Path) -> str:
    """Stable hash of a directory's contents, independent of mtimes."""
    if root.is_file():
        return hashlib.sha256(root.read_bytes()).hexdigest()[:16]
    h = hashlib.sha256()
    # Sorted as strings: WindowsPath orders case-insensitively, PosixPath does
    # not, and the two orders hash the same bytes to different digests.
    files = {f.relative_to(root).as_posix(): f for f in root.rglob("*") if f.is_file()}
    for rel in sorted(files):
        h.update(rel.encode())
        h.update(b"\0")
        h.update(files[rel].read_bytes())
        h.update(b"\0")
    return h.hexdigest()[:16]


# A checkout that translates line endings would leave tree_hash, and with it
# the content column of sources.tsv, disagreeing between Windows and Linux.
CLONE_CONFIG = ("core.autocrlf=false", "core.eol=lf")


def wipe(path: Path) -> None:
    """git leaves its pack files read-only, which Windows reads as undeletable."""
    for f in path.rglob("*"):
        if f.is_file():
            f.chmod(stat.S_IWRITE | stat.S_IREAD)
    shutil.rmtree(path)


def verbatim(dest: Path) -> bool:
    """Was this cached clone taken with the line endings upstream has?"""
    try:
        have = run(["git", "-C", str(dest), "config", "--local", "--list"]).splitlines()
    except RuntimeError:
        return False
    return all(c in have for c in CLONE_CONFIG)


def clone(repo: str, ref: str) -> Path:
    """Shallow clone into the cache, or update an existing one."""
    CACHE.mkdir(exist_ok=True)
    dest = CACHE / hashlib.sha256(repo.encode()).hexdigest()[:12]
    # Setting the config leaves a checkout made before it untouched, endings
    # and all, so such a cache has to go.
    if dest.exists() and not verbatim(dest):
        wipe(dest)
    if dest.exists():
        run(["git", "-C", str(dest), "fetch", "--depth", "1", "--quiet", "origin", ref])
        run(["git", "-C", str(dest), "checkout", "--quiet", "--force", "FETCH_HEAD"])
    else:
        config = [arg for c in CLONE_CONFIG for arg in ("--config", c)]
        run(["git", "clone", *config, "--depth", "1", "--branch", ref, "--quiet",
             repo, str(dest)])
    return dest


def remote_sha(repo: str, ref: str) -> str:
    """Commit at one exact ref. A bare name also matches ls-remote at slash
    boundaries, so refs/heads/<something>/main answers to `main` too."""
    out = run(["git", "ls-remote", repo, ref])
    by_name = {}
    for line in out.splitlines():
        sha, _, name = line.partition("\t")
        by_name[name] = sha
    # An annotated tag's own sha is not the commit clone would check out.
    for name in (f"refs/tags/{ref}^{{}}", f"refs/heads/{ref}", f"refs/tags/{ref}", ref):
        if name in by_name:
            return by_name[name]
    return ""


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


# rewrite_refs has already renamed every superpowers: ref we vendored, so a
# surviving prefix is itself the evidence. Refs that name a skill bare need
# looking up instead.
PREFIXED_REF = re.compile(r"superpowers:[a-z0-9-]+")
NAMED_REF = (
    re.compile(r'Skill tool with "([a-z0-9-]+)"'),
    re.compile(r'load and follow the skill "([a-z0-9-]+)"', re.IGNORECASE),
    # A slash ref needs a hyphen to be a skill name rather than `/tmp`.
    re.compile(r"`/([a-z0-9-]+-[a-z0-9-]+)`"),
)


def find_dangling(root: Path, canonical: set[str]) -> set[str]:
    """Refs to skills we did not vendor, left pointing at nothing."""
    found = set()
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        found |= set(PREFIXED_REF.findall(text))
        for pattern in NAMED_REF:
            found |= {n for n in pattern.findall(text) if n not in canonical}
    return found


def apply_patch(name: str, dest: Path, layer: str = "content") -> str:
    patch = PATCHES / layer / f"{name}.patch"
    if not patch.exists():
        return ""
    # git apply matches context byte for byte and the skill it is patching
    # carries upstream's line endings, so a patch checked out with CRLF has
    # to be fed back as LF.
    tmp = Path(tempfile.mkdtemp()) / patch.name
    tmp.write_bytes(patch.read_bytes().replace(b"\r\n", b"\n"))
    try:
        run(["git", "apply", "--check", str(tmp)], cwd=dest)
        run(["git", "apply", str(tmp)], cwd=dest)
        return "patched"
    except RuntimeError as e:
        raise RuntimeError(f"{patch}: PATCH FAILED\n{e}") from e
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def repo_slug(repo: str) -> str:
    """https://github.com/obra/superpowers.git -> obra-superpowers"""
    parts = repo.rstrip("/").removesuffix(".git").split("/")
    return "-".join(parts[-2:])


def copy_license(repo_dir: Path, repo: str) -> str:
    """Upstream's own license file, copied verbatim. MIT and its relatives
    require the notice to travel with the copy, so it ships here too."""
    for name in LICENSE_NAMES:
        src = repo_dir / name
        if src.is_file():
            LICENSES.mkdir(exist_ok=True)
            dest = LICENSES / f"{repo_slug(repo)}.txt"
            shutil.copyfile(src, dest)
            return dest.name
    return ""


def render_notice(sources: list[Source]) -> bytes:
    """Attribution built from sources.tsv and the license texts on disk, so a
    new source cannot ship unattributed."""
    groups: dict[str, list[Source]] = {}
    for s in sources + read_sources(SUPPORT_SOURCES):
        groups.setdefault(s.repo, []).append(s)

    rows, notes = [], []
    for repo, group in sorted(groups.items()):
        slug = repo_slug(repo)
        path = LICENSES / f"{slug}.txt"
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        # The first non-empty line of an MIT or Apache file names the license.
        title = next((l.strip() for l in text.splitlines() if l.strip()), "")
        holders = "; ".join(COPYRIGHT.findall(text)) or "see the license file"
        names = ", ".join(f"`{s.name}`" for s in sorted(group, key=lambda s: s.name))
        link = f"[{title}](licenses/{slug}.txt)" if text else f"**missing** licenses/{slug}.txt"
        rows.append(f"| {names} | <{repo.removesuffix('.git')}> | {holders} | {link} |")
        note = LICENSES / f"{slug}.note.md"
        if note.exists():
            notes.append(note.read_text(encoding="utf-8").strip())

    body = [
        "# NOTICE",
        "",
        "`cc.py vendor` writes this file from `sources.tsv`, `support-sources.tsv`,",
        "and the license texts under `licenses/`. Edits here are overwritten.",
        "",
        "Most skills under `skills/` come from the repositories below. Each",
        "upstream license is reproduced verbatim in `licenses/` and covers the",
        "skills named beside it. Everything else, `cc.py`, `instructions/`, and any",
        "skill with no row here, is covered by `LICENSE`.",
        "",
        "| Skills | Upstream | Copyright | License |",
        "| --- | --- | --- | --- |",
        *rows,
    ]
    for note in notes:
        body += ["", note]
    return ("\n".join(body) + "\n").encode("utf-8")


def same_text(a: bytes, b: bytes) -> bool:
    """Generated text against text on disk. git rewrites line endings on
    checkout where core.autocrlf is on, so they carry no information."""
    return a.replace(b"\r\n", b"\n") == b.replace(b"\r\n", b"\n")


def cmd_vendor(args) -> int:
    sources = read_sources()
    support = read_sources(SUPPORT_SOURCES)
    wanted = set(args.names) if args.names else {s.name for s in sources}
    unknown = wanted - {s.name for s in sources}
    if unknown:
        raise RuntimeError("unknown skills: " + ", ".join(sorted(unknown)))
    mapping = rename_map(sources)
    canonical = {s.name for s in sources}
    changed = False
    licensed: dict[str, Path] = {}
    prepared = []
    clones = {}

    def checkout(repo: str, ref: str) -> Path:
        key = (repo, ref)
        if key not in clones:
            clones[key] = clone(repo, ref)
        return clones[key]

    # Validate the entire batch before replacing any shared skill or pin.
    with tempfile.TemporaryDirectory() as tmp:
        for source in sources:
            if source.name not in wanted:
                continue
            repo_dir = checkout(source.repo, source.ref)
            licensed[source.repo] = repo_dir
            src = repo_dir / source.path
            if not src.is_dir():
                raise RuntimeError(f"{source.name}: missing upstream path {source.path}")
            sha = run(["git", "-C", str(repo_dir), "rev-parse", "HEAD"])
            pristine = tree_hash(src)
            stage = Path(tmp) / "shared" / source.name
            shutil.copytree(src, stage)
            for asset in support:
                owner, _, rel = asset.name.partition("/")
                if owner != source.name:
                    continue
                asset_repo = checkout(asset.repo, asset.ref)
                licensed[asset.repo] = asset_repo
                asset_src = asset_repo / asset.path
                if not asset_src.is_file():
                    raise RuntimeError(f"missing support file: {asset.path}")
                asset_dest = safe_path(stage, rel)
                asset_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(asset_src, asset_dest)
                asset_sha = run(["git", "-C", str(asset_repo), "rev-parse", "HEAD"])
                asset_hash = tree_hash(asset_src)
                changed |= (asset.sha, asset.content) != (asset_sha, asset_hash)
                asset.sha, asset.content = asset_sha, asset_hash
            touched = rewrite_refs(stage, mapping, Path(source.path).name, source.name)
            layers = []
            for layer in ("content", "compat/shared"):
                if apply_patch(source.name, stage, layer):
                    layers.append(layer)
            for target in ("claude", "codex"):
                rendered = Path(tmp) / target / source.name
                shutil.copytree(stage, rendered)
                apply_patch(source.name, rendered, f"compat/{target}")
            dangling = find_dangling(stage, canonical)
            changed |= (source.sha, source.content) != (sha, pristine)
            source.sha, source.content = sha, pristine
            bits = [sha[:12]]
            if touched:
                bits.append(f"{touched} file(s) rewritten")
            bits.extend(layers)
            if dangling:
                bits.append("DANGLING -> " + ", ".join(sorted(dangling)))
            prepared.append((source.name, stage, ", ".join(bits)))

        for repo, repo_dir in licensed.items():
            if not any((repo_dir / name).is_file() for name in LICENSE_NAMES):
                raise RuntimeError(f"no license file in {repo}")
        for repo, repo_dir in licensed.items():
            copy_license(repo_dir, repo)
        SKILLS.mkdir(exist_ok=True)
        for name, stage, message in prepared:
            dest = SKILLS / name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(stage, dest)
            print(f"  {name:<32} {message}")

    write_sources(sources)
    write_sources(support, SUPPORT_SOURCES)
    notice = render_notice(sources)
    if not NOTICE.exists() or not same_text(NOTICE.read_bytes(), notice):
        NOTICE.write_bytes(notice)
        print("NOTICE.md updated")
    print("source pins updated" if changed else "no upstream changes")
    return 0


def render_instructions(target: str) -> bytes:
    base = REPO / "instructions"
    return ("\n\n".join((base / name).read_text(encoding="utf-8").strip()
                        for name in ("shared.md", f"{target}.md")) + "\n").encode()


def skill_files(target: str) -> dict[str, bytes]:
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        for source in sorted(SKILLS.iterdir()):
            if not source.is_dir():
                continue
            stage = Path(tmp) / source.name
            shutil.copytree(source, stage)
            apply_patch(source.name, stage, f"compat/{target}")
            for f in sorted(stage.rglob("*")):
                if f.is_file():
                    out[f"{source.name}/{f.relative_to(stage).as_posix()}"] = f.read_bytes()
    return out


def planned_files(cfg: Path, target: str = "claude") -> dict[str, dict[str, bytes]]:
    skills = skill_files(target)
    if target == "codex":
        return {"skills": skills, "config": {
            "AGENTS.md": render_instructions(target),
            "config.toml": render_codex_settings(cfg),
            "hooks.json": render_codex_hooks(cfg),
        }}
    out = {f"skills/{rel}": data for rel, data in skills.items()}
    for f in sorted(RULES.rglob("*")):
        if f.is_file() and f.name != ".gitkeep":
            out[f"rules/{f.relative_to(RULES).as_posix()}"] = f.read_bytes()
    out["CLAUDE.md"] = render_instructions(target)
    out["settings.json"] = render_settings(cfg)
    return {"config": out}


def render_codex_settings(cfg: Path) -> bytes:
    """Merge managed root keys without rewriting unrelated TOML or comments."""
    template = (REPO / "settings" / "codex.toml").read_text(encoding="utf-8")
    managed = tomllib.loads(template)
    if any(isinstance(v, dict) for v in managed.values()):
        raise RuntimeError("settings/codex.toml supports root settings only")
    path = cfg / "config.toml"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    installed = tomllib.loads(text)
    # Preserve the user's other fallback names, with their existing precedence.
    key = "project_doc_fallback_filenames"
    if key in managed:
        existing = installed.get(key, [])
        if not isinstance(existing, list) or not all(isinstance(x, str) for x in existing):
            raise RuntimeError(f"{path}: {key} must be an array of strings")
        managed[key] = list(dict.fromkeys(existing + managed[key]))
    # Complete TOML statements can span lines; parse before looking for a table
    # header so brackets inside arrays and multiline strings remain untouched.
    lines = text.splitlines(keepends=True)
    kept, pending = [], ""
    for i, line in enumerate(lines):
        if not pending and line.lstrip().startswith("["):
            kept.extend(lines[i:])
            break
        pending += line
        try:
            statement = tomllib.loads(pending)
        except tomllib.TOMLDecodeError:
            continue
        if not (set(statement) & set(managed)):
            kept.append(pending)
        pending = ""
    else:
        if pending:
            raise RuntimeError(f"{path}: cannot parse root settings")
    # These tracked settings use JSON-compatible TOML scalars/arrays only.
    prefix = "".join(f"{k} = {json.dumps(v, ensure_ascii=False)}\n" for k, v in managed.items())
    rendered = prefix + "".join(kept)
    tomllib.loads(rendered)
    return rendered.encode()


def uv_executable() -> str:
    # Under `uv run --script`, sys.executable is a fresh temporary venv per
    # run; uv's own path is what stays stable between install and check.
    uv = os.environ.get("UV") or shutil.which("uv")
    if not uv:
        raise RuntimeError("uv not found; install it from https://docs.astral.sh/uv/")
    return uv


def hook_command(target: str) -> str:
    argv = [uv_executable(), "run", "--script", str(REPO / "cc.py"), "check",
            "--target", target, "--daily", "--quiet", "--hook"]
    return subprocess.list2cmdline(argv) if os.name == "nt" else shlex.join(argv)


def render_codex_hooks(cfg: Path) -> bytes:
    path = cfg / "hooks.json"
    installed = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    groups = installed.setdefault("hooks", {}).setdefault("SessionStart", [])
    marker = "claude-config drift check"
    # A stable statusMessage identifies our handler even if the checkout moves.
    for group in groups:
        group["hooks"] = [h for h in group.get("hooks", []) if h.get("statusMessage") != marker]
    groups[:] = [g for g in groups if g.get("hooks")]
    groups.append({"matcher": "startup|resume", "hooks": [{
        "type": "command", "command": hook_command("codex"),
        "timeout": 120, "statusMessage": marker,
    }]})
    return (json.dumps(installed, indent=2) + "\n").encode()


# Claude Code rewrites these in the installed settings.json (the /model
# picker persists model and effort level, per-model under modelSettings).
# Repo values seed fresh installs; after that the installed values win and
# never count as drift.
SETTINGS_LOCAL_KEYS = ("model", "effortLevel", "modelSettings")


def render_settings(cfg: Path) -> bytes:
    """Repo settings for this machine, keeping keys Claude Code owns."""
    text = (REPO / "settings.json").read_text(encoding="utf-8")
    text = text.replace("{{UV}}", json_escape(uv_executable()))
    text = text.replace("{{REPO}}", json_escape(str(REPO)))
    planned = json.loads(text)
    installed = read_json(cfg / "settings.json")
    for key in SETTINGS_LOCAL_KEYS:
        if key in installed:
            planned[key] = installed[key]
    return (json.dumps(planned, indent=2) + "\n").encode("utf-8")


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def in_sync(rel: str, target: Path, data: bytes) -> bool:
    """Settings formatting is local; compare their parsed values."""
    if rel in ("settings.json", "hooks.json"):
        installed = read_json(target)
        return bool(installed) and installed == json.loads(data)
    if rel == "config.toml":
        return tomllib.loads(target.read_text(encoding="utf-8")) == tomllib.loads(data.decode())
    return target.read_bytes() == data


def json_escape(s: str) -> str:
    return json.dumps(s)[1:-1]


def safe_path(root: Path, rel: str) -> Path:
    path = root / rel
    if Path(rel).is_absolute() or ".." in Path(rel).parts or not path.resolve().is_relative_to(root.resolve()):
        raise RuntimeError(f"manifest path escapes install root: {rel}")
    return path


def install_target(target: str, planned: dict[str, dict[str, bytes]]) -> None:
    roots = install_roots(target)
    for label, files in planned.items():
        root = roots[label]
        root.mkdir(parents=True, exist_ok=True)
        manifest_name = MANIFEST_NAME if target == "claude" else ".codex-config-manifest.json"
        manifest_path = root / manifest_name
        manifest = read_json(manifest_path)
        previous = set(manifest.get("paths", []))
        # Validate the complete manifest before writing or deleting anything.
        for rel in previous | set(files):
            safe_path(root, rel)
        written = 0
        for rel, data in sorted(files.items()):
            path = safe_path(root, rel)
            if path.exists() and in_sync(rel, path, data):
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            written += 1
        for rel in sorted(previous - set(files)):
            path = safe_path(root, rel)
            if path.exists():
                path.unlink()
            parent = path.parent
            while parent != root and parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
        manifest_path.write_text(json.dumps({"version": 1, "repo": str(REPO),
                                             "paths": sorted(files)}, indent=2) + "\n", encoding="utf-8")
        print(f"{target}/{label}: {written} file(s) written, {len(files)} tracked, {root}")
    if target == "claude":
        (roots["config"] / "rules").mkdir(exist_ok=True)


def targets(args) -> tuple[str, ...]:
    return ("claude", "codex") if args.target == "all" else (args.target,)


def cmd_install(args) -> int:
    # Render every target first, so patch/config failures cannot leave a partial
    # installation across the two runtimes.
    plans = {t: planned_files(config_dir(t), t) for t in targets(args)}
    for target, planned in plans.items():
        install_target(target, planned)
    if "codex" in plans:
        print("Codex: review and trust the drift-check hook with /hooks.")
    return 0


def cmd_check(args) -> int:
    for target in targets(args):
        check_target(args, target)
    return 0


def check_target(args, target: str) -> int:
    cfg = config_dir(target)
    stamp = cfg / (STAMP_NAME if target == "claude" else ".codex-config-stamp")
    # Once per calendar day, not per rolling 24h. A rolling window starts at
    # whatever hour it last ran, so it drifts later each day and skips the
    # next morning entirely.
    if args.daily and stamp.exists() and stamp.read_text(encoding="utf-8").strip() == today():
        return 0

    repo = check_repo(args.local_only)
    notice = check_notice()
    local = check_local(cfg, target)
    upstream = check_upstream() if not args.local_only else []

    # Stamped only once the checks are through: a fetch killed by the hook
    # timeout must not spend the day.
    cfg.mkdir(parents=True, exist_ok=True)
    stamp.write_text(today(), encoding="utf-8")

    if not repo and not notice and not local and not upstream:
        report = "" if args.quiet else f"claude-config ({target}): no drift"
    else:
        lines = [f"claude-config drift ({target})"]
        lines += [f"  repo      {line}" for line in repo]
        lines += [f"  notice    {line}" for line in notice]
        lines += [f"  local     {line}" for line in local]
        lines += [f"  upstream  {line}" for line in upstream]
        lines.append(f"  at        {REPO}")
        report = "\n".join(lines)

    if not report:
        return 0
    if args.hook:
        # Plain SessionStart stdout is documented to become model context but
        # was observed dropped (2026-09-02), and it never shows in the
        # fullscreen TUI. JSON is explicit on both channels: systemMessage for
        # the user, additionalContext for the model. The VS Code extension
        # ignores systemMessage (anthropics/claude-code#15344, closed "not
        # planned"), so the context also asks Claude to relay the report.
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": report + (
                    "\n\nRepeat this drift report verbatim to the user in "
                    "your first reply. Some GUIs render no systemMessage, so "
                    "this may be the only way the user sees it."
                ),
            },
            "systemMessage": report,
        }))
    else:
        print(report)
    return 0


def check_notice() -> list[str]:
    """Is the attribution still in step with sources.tsv? Needs no network."""
    sources = read_sources()
    out = [f"licenses/{slug}.txt missing, run vendor"
           for slug in sorted({repo_slug(s.repo) for s in sources + read_sources(SUPPORT_SOURCES)})
           if not (LICENSES / f"{slug}.txt").exists()]
    if not NOTICE.exists():
        out.append("NOTICE.md missing, run vendor")
    elif not same_text(NOTICE.read_bytes(), render_notice(sources)):
        out.append("NOTICE.md out of date, run vendor")
    return out


def check_repo(offline: bool) -> list[str]:
    """Is this repo dirty, or out of step with its remote?"""
    out = []
    try:
        dirty = run(["git", "status", "--porcelain"], cwd=REPO)
    except RuntimeError:
        return ["not a git repo, skipping repo checks"]
    if dirty:
        out.append(f"{len(dirty.splitlines())} uncommitted change(s) here")
    if offline:
        return out
    try:
        tracked = run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name",
                       "@{upstream}"], cwd=REPO)
    except RuntimeError:
        out.append("branch tracks no remote, nothing to compare")
        return out
    try:
        run(["git", "fetch", "--quiet"], cwd=REPO)
    except RuntimeError as e:
        out.append(f"fetch failed ({e.args[0].splitlines()[-1]})")
        return out
    behind, ahead = run(["git", "rev-list", "--left-right", "--count",
                         f"{tracked}...HEAD"], cwd=REPO).split()
    if int(behind):
        out.append(f"{behind} commit(s) behind {tracked}, git pull then install")
    if int(ahead):
        out.append(f"{ahead} commit(s) ahead of {tracked}, not pushed")
    return out


def check_local(cfg: Path, target: str = "claude") -> list[str]:
    out = []
    roots = install_roots(target)
    for label, files in planned_files(cfg, target).items():
        root = roots[label]
        for rel, data in sorted(files.items()):
            path = safe_path(root, rel)
            if not path.exists():
                out.append(f"{label}/{rel} missing, run install --target {target}")
            elif not in_sync(rel, path, data):
                out.append(f"{label}/{rel} differs from repo")
        manifest_name = MANIFEST_NAME if target == "claude" else ".codex-config-manifest.json"
        for rel in set(read_json(root / manifest_name).get("paths", [])) - set(files):
            if safe_path(root, rel).exists():
                out.append(f"{label}/{rel} stale, run install --target {target}")
    return out


def check_upstream() -> list[str]:
    out = []
    sources = read_sources() + read_sources(SUPPORT_SOURCES)
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
            if not src.exists():
                out.append(f"{s.name} vanished upstream at {s.path}")
            elif tree_hash(src) != s.content:
                out.append(f"{s.name} changed upstream, vendor {s.name.split('/')[0]} to review")
    return out


def main() -> int:
    p = argparse.ArgumentParser(prog="cc.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("vendor", help="fetch upstream skills into skills/")
    v.add_argument("names", nargs="*")
    v.set_defaults(func=cmd_vendor)

    i = sub.add_parser("install", help="copy instructions, skills and settings to selected runtimes")
    i.add_argument("--target", choices=("claude", "codex", "all"), default="claude")
    i.set_defaults(func=cmd_install)

    c = sub.add_parser("check", help="report drift, change nothing")
    c.add_argument("--daily", action="store_true", help="no-op if already run today")
    c.add_argument("--quiet", action="store_true", help="print only when there is drift")
    c.add_argument("--local-only", action="store_true", help="skip the network")
    c.add_argument("--hook", action="store_true",
                   help="emit SessionStart hook JSON instead of plain text")
    c.add_argument("--target", choices=("claude", "codex", "all"), default="claude")
    c.set_defaults(func=cmd_check)

    args = p.parse_args()
    if getattr(args, "hook", False) and args.target == "all":
        p.error("--hook requires one target")
    try:
        return args.func(args)
    except (RuntimeError, ValueError, OSError) as e:
        print(f"cc.py: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
