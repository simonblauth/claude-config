import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parent.parent / 'skills' / 'threads' / 'scripts' / 'sessions.py'


def proc_start(pid):
    return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]


@unittest.skipUnless(Path('/proc/self/stat').exists(), 'needs /proc')
class SessionsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.config = self.base / 'config'
        (self.config / 'sessions').mkdir(parents=True)
        self.workspace = self.base / 'dose-calc'
        self.workspace.mkdir()
        self.sleeper = subprocess.Popen(['sleep', '60'])
        self.addCleanup(self.sleeper.wait)
        self.addCleanup(self.sleeper.kill)

    def register(self, pid, name, start=None, cwd=None):
        record = {
            'pid': pid, 'name': name, 'status': 'idle', 'cwd': str(cwd or self.workspace),
            'startedAt': 1791295030275, 'procStart': start or proc_start(pid),
            'bridgeSessionId': f'session_{name}',
        }
        (self.config / 'sessions' / f'{pid}.json').write_text(json.dumps(record))
        (self.config / 'sessions' / f'{pid}.secret.key').write_text('must stay unread')

    def run_script(self):
        env = {**os.environ, 'CLAUDE_CONFIG_DIR': str(self.config)}
        out = subprocess.run([sys.executable, SCRIPT], env=env, capture_output=True, text=True, check=True)
        return {s['name']: s for s in map(json.loads, out.stdout.splitlines())}

    def test_live_session_carries_workspace_description_and_repos(self):
        (self.workspace / 'CLAUDE.md').write_text('# Workspace: dose-calc\n\nFixes the dose drift.\nBoth twins.\n\n## More\n')
        repo = self.base / 'dosecalc-repo'
        subprocess.run(['git', 'init', '-q', repo], check=True)
        subprocess.run(['git', '-C', repo, 'remote', 'add', 'origin', 'git@github.com:org/DoseCalc.jl.git'], check=True)
        (self.workspace / 'DoseCalc').symlink_to(repo)
        self.register(self.sleeper.pid, 'dose')

        session = self.run_script()['dose']

        self.assertEqual(session['cwd'], str(self.workspace))
        self.assertEqual(session['remote_id'], 'session_dose')
        self.assertFalse(session['self'])
        self.assertEqual(session['description'], 'Workspace: dose-calc. Fixes the dose drift. Both twins.')
        self.assertEqual(session['repos'], [{'dir': 'DoseCalc', 'remote': 'git@github.com:org/DoseCalc.jl.git'}])

    def test_description_keeps_the_list_a_colon_introduces(self):
        (self.workspace / 'README.md').write_text('Moves the engine to newer releases:\n\n1. 1.5 to 1.7.\n2. 1.7 to 1.8.\n\nOther text.\n')
        self.register(self.sleeper.pid, 'dose')
        self.assertEqual(self.run_script()['dose']['description'], 'Moves the engine to newer releases: 1. 1.5 to 1.7. 2. 1.7 to 1.8.')

    def test_dead_and_reused_pids_are_skipped(self):
        done = subprocess.Popen(['true'])
        done.wait()
        (self.config / 'sessions' / f'{done.pid}.json').write_text(json.dumps({'pid': done.pid, 'name': 'dead'}))
        self.register(self.sleeper.pid, 'reused', start='1')
        self.assertEqual(self.run_script(), {})

    def test_ancestor_session_is_marked_self(self):
        self.register(os.getpid(), 'me')
        self.assertTrue(self.run_script()['me']['self'])


if __name__ == '__main__':
    unittest.main()
