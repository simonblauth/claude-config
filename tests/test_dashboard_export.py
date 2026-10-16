import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest

SCRIPT = Path(__file__).resolve().parent.parent / 'skills' / 'vault' / 'dashboard' / 'scripts' / 'export.py'

PROJECT = '''\
---
type: project
title: Parser rewrite
created: 2026-01-05
updated: 2026-01-07
status: active
focus: now
people: [ada]
---
## State

Fixes the slowdown in [[tokenizer]]s and [[lab]]s. More detail follows.

## Next

- [ ] profile with a fixed `size` @ada due:2026-01-09 every:friday
- [ ] merge the fix waiting:ada waiting:lab
  - first item
  - second item

## Log

- 2025-12 started
- 2026-01-06 done: reproduced the slowdown with **input 3**
- 2026-01-07 dropped: the second machine

## Ideas

- try a coarser grid
'''

DAILY = '''\
# 2026-01-05

## Brief

Outcomes for the week:

1. Slowdown fixed ([[parser-rewrite]]).

Today:

1. agent · [[parser-rewrite]]: profile with the fixed size, as [[ada|Ada]] asked.
2. user · [[parser-rewrite]]: mail the [[lab]].

Meetings: Jour fixe 11:00, Team 13:00.

Decisions: The rerun waits. Ada reviews.

## Captures

- New task: plot the slowdown ([[parser-rewrite]])

## Claude did

## Wrap

Done:

- Reproduced the slowdown ([[parser-rewrite]]).

Moves to tomorrow:

- Merge the fix.
'''


PARTS = ('Outcomes for the week:', 'Today:', 'Done:', 'Moves to tomorrow:')


def note(title, kind):
    return f'---\ntype: {kind}\ntitle: {title}\ncreated: 2026-01-05\nupdated: 2026-01-05\n---\n'


@unittest.skipUnless(shutil.which('uv'), 'needs uv')
class ExportTests(unittest.TestCase):
    @classmethod
    def export(cls, daily):
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        vault = Path(tmp.name) / 'vault'
        files = {
            'projects/parser-rewrite.md': PROJECT,
            'people/ada.md': note('Ada Lovelace (Al)', 'person'),
            'orgs/lab.md': note('The Lab', 'org'),
            'concepts/tokenizer.md': note('Tokenizers', 'concept'),
            'daily/2026-01-05.md': daily,
        }
        for rel, text in files.items():
            (vault / rel).parent.mkdir(parents=True, exist_ok=True)
            (vault / rel).write_text(text)
        out = Path(tmp.name) / 'out'
        stdout = subprocess.run(['uv', 'run', '--quiet', '--script', SCRIPT, vault, out],
                                capture_output=True, text=True, check=True).stdout
        return stdout, {n: json.loads((out / f'vault-{n}.json').read_text()) for n in ('projects', 'tasks', 'log', 'days')}

    @classmethod
    def setUpClass(cls):
        cls.stdout, cls.rows = cls.export(DAILY)

    def test_prints_row_counts(self):
        self.assertEqual(self.stdout.split('\n')[:4], ['projects 1', 'tasks 2', 'log 3', 'days 10'])

    def test_project_row_counts_and_resolves_links(self):
        p = self.rows['projects'][0]
        self.assertEqual((p['slug'], p['status'], p['focus']), ('parser-rewrite', 'active', 'now'))
        self.assertEqual(p['summary'], 'Fixes the slowdown in Tokenizers and The Labs.')
        self.assertEqual(p['people'], 'Ada Lovelace')
        self.assertEqual((p['open_tasks'], p['waiting_tasks'], p['log_entries'], p['ideas']), (2, 1, 3, 1))
        self.assertEqual(p['last_activity'], '2026-01-07')

    def test_task_tags_become_fields(self):
        first, second = self.rows['tasks']
        self.assertEqual(first['text'], 'profile with a fixed size')
        self.assertEqual((first['owner'], first['due'], first['every']), ('ada', '2026-01-09', 'friday'))
        self.assertEqual(second['waiting_on'], 'Ada Lovelace, The Lab')
        self.assertEqual(second['details'], 'first item; second item')

    def test_log_kinds_and_plain_text(self):
        kinds = [(e['date'], e['kind'], e['text']) for e in self.rows['log']]
        self.assertEqual(kinds, [
            ('2025-12', 'event', 'started'),
            ('2026-01-06', 'done', 'reproduced the slowdown with input 3'),
            ('2026-01-07', 'dropped', 'the second machine'),
        ])

    def test_daily_note_sections(self):
        by = {}
        for r in self.rows['days']:
            by.setdefault(r['section'], []).append(r)
        self.assertEqual([r['text'] for r in by['outcome']], ['Slowdown fixed (Parser rewrite).'])
        agent, user = by['brief']
        self.assertEqual((agent['who'], agent['project'], agent['text']), ('agent', 'parser-rewrite', 'profile with the fixed size, as Ada asked.'))
        self.assertEqual((user['who'], user['text']), ('user', 'mail the The Lab.'))
        self.assertEqual([r['text'] for r in by['meeting']], ['Jour fixe 11:00', 'Team 13:00'])
        self.assertEqual([r['text'] for r in by['decision']], ['The rerun waits.', 'Ada reviews.'])
        self.assertEqual(by['capture'][0]['project'], 'parser-rewrite')
        self.assertEqual([r['text'] for r in by['done']], ['Reproduced the slowdown (Parser rewrite).'])
        self.assertEqual([r['text'] for r in by['moves']], ['Merge the fix.'])
        self.assertNotIn('claude_did', by)

    def test_part_labels_after_a_lead_in_sentence(self):
        daily = DAILY
        for label in PARTS:
            daily = daily.replace(f'\n{label}', f'\nPlan confirmed. {label}')
        self.assertEqual(daily.count('Plan confirmed.'), len(PARTS))
        _, rows = self.export(daily)
        self.assertEqual(rows['days'], self.rows['days'])

    def test_part_label_words_inside_a_sentence_are_content(self):
        daily = DAILY.replace('Decisions: The rerun waits. Ada reviews.',
                              'Decisions: The rerun waits. Today stays free. Outcomes for the week stay.')
        _, rows = self.export(daily)
        decisions = [r['text'] for r in rows['days'] if r['section'] == 'decision']
        self.assertEqual(decisions, ['The rerun waits.', 'Today stays free.', 'Outcomes for the week stay.'])


if __name__ == '__main__':
    unittest.main()
