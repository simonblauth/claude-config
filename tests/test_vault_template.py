import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

SKILLS = Path(__file__).resolve().parent.parent / 'skills' / 'vault'
TEMPLATE = SKILLS / 'setup-vault' / 'assets' / 'vault'
EXPORT = SKILLS / 'dashboard' / 'scripts' / 'export.py'


def note(kind, title, extra='', body=''):
    return f'---\ntype: {kind}\ntitle: {title}\ncreated: 2026-01-05\nupdated: 2026-01-05\n{extra}---\n{body}'


@unittest.skipUnless(shutil.which('uv'), 'needs uv')
class TemplateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.vault = Path(tmp.name) / 'vault'
        shutil.copytree(TEMPLATE, self.vault)
        (self.vault / 'vault-rules.md').rename(self.vault / 'CLAUDE.md')

    def run_check(self):
        return subprocess.run(['uv', 'run', '--quiet', '--script', self.vault / 'tools' / 'check.py'],
                              capture_output=True, text=True)

    def test_checker_suite_passes(self):
        result = subprocess.run(['uv', 'run', '--quiet', '--no-project', '--with', 'pyyaml',
                                 'python', '-m', 'unittest', 'test_check'],
                                cwd=TEMPLATE / 'tools', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_fresh_vault_passes_the_checker(self):
        result = self.run_check()
        self.assertEqual((result.returncode, result.stdout), (0, ''))

    def test_example_daily_note_exports_every_section(self):
        rules = (self.vault / 'CLAUDE.md').read_text()
        daily = re.search(r'```markdown\n(# (\d{4}-\d{2}-\d{2})\n.*?)```', rules, re.S)
        files = {
            f'daily/{daily.group(2)}.md': daily.group(1),
            'projects/parser-rewrite.md': note('project', 'Parser rewrite', 'status: active\nfocus: now\n',
                                               '## State\n\n## Next\n\n## Log\n\n## Ideas\n'),
            'people/ada.md': note('person', 'Ada'),
            'orgs/lab.md': note('org', 'The Lab'),
        }
        for rel, text in files.items():
            (self.vault / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.vault / rel).write_text(text)
        self.assertEqual(self.run_check().stdout, '')

        out = self.vault.parent / 'out'
        subprocess.run(['uv', 'run', '--quiet', '--script', EXPORT, self.vault, out], check=True, capture_output=True)
        days = json.loads((out / 'vault-days.json').read_text())
        sections = {r['section'] for r in days}
        self.assertEqual(sections, {'outcome', 'brief', 'meeting', 'decision', 'capture', 'claude_did', 'done', 'moves'})
        self.assertEqual([r['who'] for r in days if r['section'] == 'brief'], ['agent', 'user'])


if __name__ == '__main__':
    unittest.main()
