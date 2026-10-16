"""List the Claude Code sessions running on this machine, one JSON object per line.

Reads the session registry in $CLAUDE_CONFIG_DIR/sessions (default ~/.claude/sessions).
The registry is Claude Code's internal state, not a documented interface. The *.key
files beside each record are credentials and are never opened.
"""

import datetime
import json
import os
from pathlib import Path
import subprocess

DESCRIPTION_FILES = ('CLAUDE.md', 'AGENTS.md', 'README.md')
DESCRIPTION_LIMIT = 400


def config_dir():
    return Path(os.environ.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude')


def stat_fields(pid):
    stat = Path(f'/proc/{pid}/stat')
    if not stat.exists():
        return None
    # The command name in field 2 may contain spaces; fields after it start at field 3.
    return stat.read_text().rsplit(')', 1)[1].split()


def alive(pid, proc_start):
    fields = stat_fields(pid)
    if fields is not None:
        # procStart is the process start time (field 22), so a reused PID does not match.
        return proc_start is None or fields[19] == str(proc_start)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    return True


def parent(pid):
    fields = stat_fields(pid)
    if fields is not None:
        return int(fields[1])
    out = subprocess.run(['ps', '-o', 'ppid=', '-p', str(pid)], capture_output=True, text=True)
    return int(out.stdout.strip() or 0)


def ancestors():
    pids, pid = set(), os.getpid()
    while pid > 1:
        pid = parent(pid)
        pids.add(pid)
    return pids


def description(cwd):
    for name in DESCRIPTION_FILES:
        path = cwd / name
        if path.is_file():
            break
    else:
        return None
    heading, paragraph = None, []
    for line in path.read_text(errors='replace').splitlines():
        text = line.strip()
        if text.startswith('#'):
            if paragraph:
                break
            heading = heading or text.lstrip('#').strip()
        elif text:
            paragraph.append(text)
        elif paragraph and not paragraph[-1].endswith(':'):
            break
    parts = [heading.rstrip('.') + '.'] if heading else []
    text = ' '.join(parts + paragraph)
    return text[:DESCRIPTION_LIMIT] or None


def remote(repo):
    out = subprocess.run(['git', '-C', str(repo), 'remote', '-v'], capture_output=True, text=True)
    urls = [line.split()[1] for line in out.stdout.splitlines() if line.startswith('origin\t')]
    urls = urls or [line.split()[1] for line in out.stdout.splitlines() if '\t' in line]
    return urls[0] if urls else None


def repos(cwd):
    candidates = [(cwd, '.')] + [
        (child, child.name) for child in sorted(cwd.iterdir()) if not child.name.startswith('.') and child.is_dir()
    ]
    return [{'dir': name, 'remote': remote(path)} for path, name in candidates if (path / '.git').exists()]


def sessions():
    me = ancestors()
    found = []
    for path in (config_dir() / 'sessions').glob('*.json'):
        try:
            record = json.loads(path.read_text())
            pid = int(record['pid'])
        except (OSError, ValueError, KeyError):
            continue
        if not alive(pid, record.get('procStart')):
            continue
        cwd = Path(record.get('cwd', ''))
        started = record.get('startedAt')
        found.append({
            'name': record.get('name'),
            'status': record.get('status'),
            'remote_id': record.get('bridgeSessionId'),
            'cwd': str(cwd),
            'started': started and datetime.datetime.fromtimestamp(started / 1000).isoformat(timespec='minutes'),
            'self': pid in me,
            'description': description(cwd) if cwd.is_dir() else None,
            'repos': repos(cwd) if cwd.is_dir() else [],
        })
    return sorted(found, key=lambda s: s['started'] or '')


if __name__ == '__main__':
    for session in sessions():
        print(json.dumps(session, ensure_ascii=False))
