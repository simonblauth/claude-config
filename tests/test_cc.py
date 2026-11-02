import argparse
import contextlib
import io
import json
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import tomllib
import unittest
from unittest.mock import patch

import cc

# Tests never read this machine's own config file.
os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp()


class InstallBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.roots = {t: {'config': self.base / t} for t in ('claude', 'codex')}
        self.roots['codex']['skills'] = self.base / 'agents' / 'skills'
        for name, value in (
            ('config_dir', lambda target='claude': self.roots[target]['config']),
            ('install_roots', lambda target: self.roots[target]),
        ):
            p = patch.object(cc, name, value)
            p.start()
            self.addCleanup(p.stop)

    def install(self, target='all'):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            cc.cmd_install(argparse.Namespace(target=target))
        return output.getvalue()


class InstallTests(InstallBase):
    def test_both_targets_and_repeat_install(self):
        self.install()
        for target in self.roots:
            self.assertEqual(cc.check_local(cc.config_dir(target), target), [])
        codex = cc.config_dir('codex')
        self.assertTrue((codex / 'AGENTS.md').exists())
        self.assertFalse((codex / 'skills').exists())
        self.assertIn('project_doc_fallback_filenames', tomllib.loads((codex / 'config.toml').read_text()))
        again = self.install()
        self.assertEqual(again.count('0 file(s) written'), 3)
        skill_root = self.roots['codex']['skills']
        self.assertIn('allow_implicit_invocation: false', (skill_root / 'review-loop/agents/openai.yaml').read_text())
        self.assertNotIn('Claude Code reflection', (skill_root / 'reflect/references/runtime.md').read_text())
        self.assertIn('Claude Code reflection', (cc.config_dir() / 'skills/reflect/references/runtime.md').read_text())

    def test_codex_preserves_settings_comments_and_other_hooks(self):
        cfg = cc.config_dir('codex'); cfg.mkdir()
        local = '''# local settings
model = "my-model"
project_doc_fallback_filenames = [
  "TEAM.md", # preferred fallback
]
[projects."/work"]
trust_level = "trusted"
[mcp_servers.example]
command = "example"
'''
        (cfg / 'config.toml').write_text(local)
        other = {'type': 'command', 'command': 'echo unrelated'}
        (cfg / 'hooks.json').write_text(json.dumps({'hooks': {'SessionStart': [{'hooks': [other]}], 'Stop': []}}))
        self.install('codex')
        text = (cfg / 'config.toml').read_text()
        parsed = tomllib.loads(text)
        self.assertEqual(parsed['model'], 'my-model')
        self.assertEqual(parsed['project_doc_fallback_filenames'], ['TEAM.md', 'CLAUDE.md'])
        self.assertIn('# local settings', text)
        self.assertIn('[mcp_servers.example]\ncommand = "example"', text)
        self.assertEqual(json.loads((cfg / 'hooks.json').read_text())['hooks']['SessionStart'][0]['hooks'], [other])
        self.install('codex')
        self.assertEqual(cc.check_local(cfg, 'codex'), [])

    def test_multiline_toml_and_quoted_key(self):
        cfg = cc.config_dir('codex'); cfg.mkdir()
        local = '''"project_doc_fallback_filenames" = ["TEAM.md"]
model = "local"
notes = """a string
[not.a.table]
project_doc_fallback_filenames = not a key
"""
[features]
multi_agent = false
'''
        (cfg / 'config.toml').write_text(local)
        result = cc.render_codex_settings(cfg).decode()
        parsed = tomllib.loads(result)
        self.assertEqual(parsed['notes'], tomllib.loads(local)['notes'])
        self.assertFalse(parsed['features']['multi_agent'])
        self.assertEqual(parsed['project_doc_fallback_filenames'], ['TEAM.md', 'CLAUDE.md'])

    def test_hooks_run_through_uv_not_the_ephemeral_interpreter(self):
        uv = str(self.base / 'bin' / 'uv')
        with patch.dict(os.environ, {'UV': uv}):
            self.install()
        claude = json.loads((cc.config_dir() / 'settings.json').read_text())
        codex = json.loads((cc.config_dir('codex') / 'hooks.json').read_text())
        for command in (claude['hooks']['SessionStart'][0]['hooks'][0]['command'],
                        codex['hooks']['SessionStart'][-1]['hooks'][0]['command']):
            self.assertTrue(command.startswith(f'"{uv}" run --script ') or
                            command.startswith(f'{uv} run --script '), command)
            self.assertNotIn(cc.sys.executable, command)

    def test_install_without_uv_fails_clearly(self):
        # git's own directory, not a symlink: Windows grants symlinks only to admins
        git_dir = Path(shutil.which('git')).parent
        self.assertIsNone(shutil.which('uv', path=str(git_dir)))
        with patch.dict(os.environ, {'PATH': str(git_dir)}):
            os.environ.pop('UV', None)
            with self.assertRaisesRegex(RuntimeError, 'uv'):
                self.install()

    def test_settings_formatting_is_not_drift(self):
        self.install('codex')
        cfg = cc.config_dir('codex')
        (cfg / 'config.toml').write_text("# my comment\nproject_doc_fallback_filenames=['CLAUDE.md']\n")
        path = cfg / 'hooks.json'
        path.write_text(json.dumps(json.loads(path.read_text()), separators=(',', ':')))
        self.assertEqual(cc.check_local(cfg, 'codex'), [])
        before = (cfg / 'config.toml').read_bytes()
        self.install('codex')
        self.assertEqual((cfg / 'config.toml').read_bytes(), before)

    def test_invalid_codex_config_does_not_write_either_target(self):
        cfg = cc.config_dir('codex'); cfg.mkdir()
        (cfg / 'config.toml').write_text('broken = [')
        with self.assertRaises(ValueError):
            self.install()
        self.assertFalse(cc.config_dir('claude').exists())
        self.assertFalse((cfg / 'AGENTS.md').exists())

    def test_drift_and_owned_stale_cleanup_preserve_unowned_files(self):
        self.install()
        root = self.roots['codex']['skills']
        (root / 'local.txt').write_text('mine')
        (root / 'obsolete.txt').write_text('ours')
        manifest = root / '.codex-config-manifest.json'
        data = json.loads(manifest.read_text()); data['paths'].append('obsolete.txt')
        manifest.write_text(json.dumps(data))
        (root / 'tdd/SKILL.md').write_text('changed')
        drift = cc.check_local(cc.config_dir('codex'), 'codex')
        self.assertIn('skills/tdd/SKILL.md differs from repo', drift)
        self.assertIn('skills/obsolete.txt stale, run install --target codex', drift)
        self.install('codex')
        self.assertTrue((root / 'local.txt').exists())
        self.assertFalse((root / 'obsolete.txt').exists())
        self.assertEqual(cc.check_local(cc.config_dir('codex'), 'codex'), [])

    def test_legacy_claude_manifest_and_local_model(self):
        cfg = cc.config_dir(); cfg.mkdir()
        (cfg / 'old-file').write_text('old')
        (cfg / cc.MANIFEST_NAME).write_text(json.dumps({'paths': ['old-file']}))
        (cfg / 'settings.json').write_text(json.dumps({'model': 'local', 'effortLevel': 'high'}))
        self.install('claude')
        self.assertFalse((cfg / 'old-file').exists())
        settings = json.loads((cfg / 'settings.json').read_text())
        self.assertEqual(settings['model'], 'local')
        self.assertEqual(settings['effortLevel'], 'high')
        self.assertTrue((cfg / 'rules').is_dir())

    def test_manifest_cannot_delete_outside_root(self):
        cfg = cc.config_dir(); cfg.mkdir()
        victim = self.base / 'outside'; victim.write_text('keep')
        (cfg / cc.MANIFEST_NAME).write_text(json.dumps({'paths': ['../outside']}))
        with self.assertRaisesRegex(RuntimeError, 'escapes'):
            self.install('claude')
        self.assertEqual(victim.read_text(), 'keep')
        self.assertFalse((cfg / 'CLAUDE.md').exists())

    def test_daily_stamps_are_independent_and_hook_json_valid(self):
        self.install()
        args = argparse.Namespace(target='all', daily=True, quiet=False, local_only=True, hook=True)
        with patch.object(cc, 'check_repo', return_value=[]), contextlib.redirect_stdout(io.StringIO()) as output:
            cc.check_target(args, 'claude')
        report = json.loads(output.getvalue())
        self.assertEqual(report['hookSpecificOutput']['hookEventName'], 'SessionStart')
        self.assertFalse((cc.config_dir('codex') / '.codex-config-stamp').exists())
        with patch.object(cc, 'check_repo', return_value=[]), contextlib.redirect_stdout(io.StringIO()) as output:
            cc.check_target(args, 'codex')
        self.assertIn('(codex)', json.loads(output.getvalue())['systemMessage'])
        with contextlib.redirect_stdout(io.StringIO()) as output:
            cc.check_target(args, 'codex')
        self.assertEqual(output.getvalue(), '')

    def test_patch_failure_prevents_installation(self):
        patches = self.base / 'patches'
        p = patches / 'compat/codex/tdd.patch'; p.parent.mkdir(parents=True)
        p.write_text('--- a/SKILL.md\n+++ b/SKILL.md\n@@ -1 +1 @@\n-no such line\n+replacement\n')
        with patch.object(cc, 'PATCHES', patches), self.assertRaisesRegex(RuntimeError, 'PATCH FAILED'):
            self.install()
        self.assertFalse(cc.config_dir().exists())


class MachineConfigTests(InstallBase):
    """The per-machine config file adds sources of rules and skills, variables and a default reviewer."""

    def setUp(self):
        super().setUp()
        p = patch.object(cc, 'CACHE', self.base / 'cache')
        p.start()
        self.addCleanup(p.stop)
        self.config = self.base / 'config.toml'
        p = patch.object(cc, 'machine_config_path', lambda: self.config)
        p.start()
        self.addCleanup(p.stop)
        self.source = self.base / 'src'
        (self.source / 'rules').mkdir(parents=True)
        self.git('init', '-q', '-b', 'master')
        self.write('rules/julia.md', '---\npaths:\n  - "**/*.jl"\n  - "**/Project.toml"\n---\n\n# Julia\n\n- Use the project env.\n')
        self.write('rules/compute.md', '# Compute\n\n- Stage data in {{share_scratch}}.\n')
        self.write('skills/mine/SKILL.md', '---\nname: mine\ndescription: d\n---\n\nMine.\n')
        self.write('skills/mine/references/r.md', 'ref\n')
        self.write('skills/theirs/SKILL.md', '---\nname: theirs\ndescription: d\n---\n\nTheirs.\n')
        self.commit()

    def git(self, *args):
        subprocess.run(['git', '-C', str(self.source), '-c', 'commit.gpgsign=false', '-c', 'user.name=t',
                        '-c', 'user.email=t@t', *args], check=True, capture_output=True)

    def write(self, rel, text):
        path = self.source / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def commit(self):
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'change')

    def configure(self, text):
        self.config.write_text(text)

    def with_source(self, select='rules = "all"\nskills = "all"\n', extra=''):
        self.configure(extra + f'[[sources]]\nrepo = "{self.source.as_uri()}"\n' + select)

    def test_rules_reach_both_targets(self):
        self.with_source()
        self.install()
        claude = cc.config_dir()
        self.assertIn('# Julia', (claude / 'rules/julia.md').read_text())
        agents = (cc.config_dir('codex') / 'AGENTS.md').read_text()
        self.assertIn('_From rules/julia.md, scoped by its frontmatter:_\n\n```yaml\npaths:\n  - "**/*.jl"', agents)
        self.assertIn('- Use the project env.', agents)
        self.assertEqual(agents.count('---\npaths:'), 0)
        for target in self.roots:
            self.assertEqual(cc.check_local(cc.config_dir(target), target), [])

    def test_skills_reach_both_targets(self):
        self.with_source()
        self.install()
        self.assertIn('Mine.', (cc.config_dir() / 'skills/mine/SKILL.md').read_text())
        self.assertEqual((self.roots['codex']['skills'] / 'mine/references/r.md').read_text(), 'ref\n')

    def test_only_the_named_skills_and_rules_install(self):
        self.with_source('skills = ["theirs"]\nrules = ["julia"]\n')
        self.install()
        claude = cc.config_dir()
        self.assertTrue((claude / 'skills/theirs/SKILL.md').exists())
        self.assertFalse((claude / 'skills/mine').exists())
        self.assertTrue((claude / 'rules/julia.md').exists())
        self.assertFalse((claude / 'rules/compute.md').exists())

    def test_a_source_picks_nothing_by_default(self):
        self.with_source(select='')
        with self.assertRaisesRegex(ValueError, 'config.toml'):
            cc.machine_config()

    def test_a_source_without_rules_or_skills_folders_stops_the_install(self):
        self.git('mv', 'rules', 'rule')
        self.git('mv', 'skills', 'skill')
        self.commit()
        self.with_source()
        with self.assertRaisesRegex(RuntimeError, 'neither rules/ nor skills/'):
            self.install()

    def test_a_missing_name_stops_the_install(self):
        self.with_source('skills = ["nope"]\n')
        with self.assertRaisesRegex(RuntimeError, 'nope'):
            self.install()

    def test_vars_fill_rules_and_default_to_none(self):
        self.with_source(extra='[vars]\nshare_scratch = "/data/claude"\n\n')
        self.install()
        self.assertIn('Stage data in /data/claude.', (cc.config_dir() / 'rules/compute.md').read_text())
        self.assertIn('Stage data in /data/claude.', (cc.config_dir('codex') / 'AGENTS.md').read_text())
        self.with_source()
        self.install()
        self.assertIn('Stage data in none.', (cc.config_dir() / 'rules/compute.md').read_text())

    def test_two_refs_of_one_repo_keep_their_own_checkouts(self):
        self.git('checkout', '-q', '-b', 'dev')
        self.write('skills/theirs/SKILL.md', '---\nname: theirs\ndescription: d\n---\n\nTheirs on dev.\n')
        self.commit()
        self.git('checkout', '-q', 'master')
        uri = self.source.as_uri()
        self.configure(f'[[sources]]\nrepo = "{uri}"\nref = "master"\nskills = ["theirs"]\n\n'
                       f'[[sources]]\nrepo = "{uri}"\nref = "dev"\nskills = ["mine"]\n')
        self.install()
        self.assertIn('Theirs.', (cc.config_dir() / 'skills/theirs/SKILL.md').read_text())
        self.assertEqual(cc.check_sources(), [])

    def test_frontmatter_passes_through_as_written(self):
        for text, front, body in (
            ('---\npaths: [\n  "a",  # why\n  "b"\n]\n---\n# X\n', 'paths: [\n  "a",  # why\n  "b"\n]', '# X\n'),
            ('---\r\npaths:\r\n  - "a"\r\n---\r\nbody\r\n', 'paths:\r\n  - "a"', 'body\r\n'),
            ('---\npaths: "a"\n---', 'paths: "a"', ''),
            ('# No frontmatter\n', '', '# No frontmatter\n'),
            ('---\nunclosed\n', '', '---\nunclosed\n'),
        ):
            with self.subTest(text=text):
                self.assertEqual(cc.split_frontmatter(text), (front, body))

    def test_a_rule_without_paths_applies_everywhere_in_codex(self):
        self.with_source()
        self.install()
        self.assertIn('_From rules/compute.md, applies everywhere._', (cc.config_dir('codex') / 'AGENTS.md').read_text())

    def test_source_changes_show_upstream_then_install(self):
        self.with_source()
        self.install()
        self.assertEqual(cc.check_sources(), [])
        (self.source / 'rules' / 'compute.md').unlink()
        self.write('rules/julia.md', '# Julia\n\n- Changed.\n')
        self.commit()
        self.assertEqual(len(cc.check_sources()), 1)
        self.install()
        claude = cc.config_dir()
        self.assertIn('Changed.', (claude / 'rules/julia.md').read_text())
        self.assertFalse((claude / 'rules/compute.md').exists())

    def test_missing_clone_is_drift_not_a_crash(self):
        self.with_source()
        self.assertTrue(any('run install' in line for line in cc.check_local(cc.config_dir(), 'claude')))

    def test_default_reviewer_reaches_the_instructions(self):
        self.configure('[review]\ndefault = "codex"\n')
        self.install()
        for target, name in (('claude', 'CLAUDE.md'), ('codex', 'AGENTS.md')):
            self.assertIn('Default reviewer for `issue-to-pr` and `review-loop`: `codex`',
                          (cc.config_dir(target) / name).read_text())

    def test_vault_inputs_are_accepted(self):
        self.configure('[vault]\ninputs = ["calendar", "github"]\n')
        self.assertEqual(cc.machine_config()['vault'], {'inputs': ['calendar', 'github']})

    def test_no_config_adds_nothing(self):
        self.install()
        self.assertNotIn('Default reviewer', (cc.config_dir() / 'CLAUDE.md').read_text())
        self.assertNotIn('StopFailure', json.loads((cc.config_dir() / 'settings.json').read_text())['hooks'])

    def test_usage_limit_continue_hook_installs_when_configured(self):
        self.configure('[hooks]\nusage_limit_continue = true\n')
        self.install()
        [group] = json.loads((cc.config_dir() / 'settings.json').read_text())['hooks']['StopFailure']
        self.assertIn('hooks/usage_limit_continue.py', group['hooks'][0]['command'])
        self.configure('[hooks]\nusage_limit_continue = false\n')
        self.install()
        self.assertNotIn('StopFailure', json.loads((cc.config_dir() / 'settings.json').read_text())['hooks'])

    def test_invalid_config_is_refused(self):
        for text in ('[review]\ndefault = "nobody"\n', 'reviewer = "codex"\n', '[[sources]]\nskills = "all"\n',
                     '[[sources]]\nrepo = "x"\nskills = "some"\n', '[vars]\nn = 1\n',
                     '[vault]\ninputs = "mail"\n', '[vault]\nsources = ["mail"]\n',
                     'vars = ["a"]\n', 'review = "codex"\n', 'vault = "x"\n', 'sources = {repo = "x"}\n',
                     '[[sources]]\nrepo = "x"\nref = 1\nskills = "all"\n',
                     '[[sources]]\nrepo = "x"\nrules = []\nskills = []\n',
                     'hooks = true\n', '[hooks]\nusage_limit_continue = "yes"\n', '[hooks]\nother = true\n'):
            with self.subTest(text=text):
                self.configure(text)
                with self.assertRaisesRegex(ValueError, 'config.toml'):
                    cc.machine_config()

    def test_a_rule_from_two_places_fails(self):
        self.with_source()
        with patch.object(cc, 'RULES', self.source / 'rules'), self.assertRaisesRegex(RuntimeError, 'comes from both'):
            self.install()

    def test_a_skill_this_repo_has_fails(self):
        self.write('skills/tdd/SKILL.md', '---\nname: tdd\ndescription: d\n---\n')
        self.commit()
        self.with_source('skills = ["tdd"]\n')
        with self.assertRaisesRegex(RuntimeError, 'tdd'):
            self.install()


class SettingsTests(unittest.TestCase):
    def test_heredoc_guard_is_installed_on_every_platform(self):
        for windows in (True, False):
            with self.subTest(windows=windows), patch.object(cc, 'WINDOWS', windows), \
                    tempfile.TemporaryDirectory() as tmp:
                settings = cc.render_settings(Path(tmp)).decode()
                self.assertIn('heredoc_guard.py', settings)

    def repo_auto_mode(self):
        return json.loads((cc.REPO / 'settings.json').read_text()).get('autoMode')

    def test_owned_remotes_extend_the_auto_mode_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            rules = Path(tmp) / 'rules'
            rules.mkdir()
            (rules / 'owned-remotes.md').write_text(
                '- github.com/org/*\n- gitlab.example.com/team/tool\n')
            settings = json.loads(cc.render_settings(Path(tmp)))
        repo_env = (self.repo_auto_mode() or {}).get('environment', ['$defaults'])
        env = settings['autoMode']['environment']
        self.assertEqual(env[:-1], repo_env)
        self.assertIn('github.com/org/*, gitlab.example.com/team/tool', env[-1])

    def test_every_markdown_bullet_form_is_an_owned_remote(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'owned-remotes.md'
            path.write_text('# Owned remotes\n\n- a/*\n* b/*\n+ c/*\n-\td/*\n  - e/*\n')
            self.assertEqual(cc.owned_remotes(path), ['a/*', 'b/*', 'c/*', 'd/*', 'e/*'])

    def test_owned_remotes_listed_in_another_rules_file_are_ignored(self):
        # Only the one file defines ownership, so text that merely looks like
        # an owned-remotes list cannot widen the classifier's trust.
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'rules').mkdir()
            (Path(tmp) / 'rules' / 'git.md').write_text(
                '## Owned remotes\n\n- github.com/org/*\n')
            settings = json.loads(cc.render_settings(Path(tmp)))
        self.assertEqual(settings.get('autoMode'), self.repo_auto_mode())

    def test_private_owned_remotes_stay_out_of_the_auto_mode_environment(self):
        # The classifier cannot check visibility, so it would trust a public
        # repo under a `(private)` entry.
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'rules').mkdir()
            (Path(tmp) / 'rules' / 'owned-remotes.md').write_text(
                '## Owned remotes\n\n- github.com/me/* (private)\n')
            settings = json.loads(cc.render_settings(Path(tmp)))
        self.assertEqual(settings.get('autoMode'), self.repo_auto_mode())

    def test_without_owned_remotes_auto_mode_is_the_repo_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = json.loads(cc.render_settings(Path(tmp)))
        self.assertEqual(settings.get('autoMode'), self.repo_auto_mode())


class RepoCheckTests(unittest.TestCase):
    def git(self, *args):
        subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                        '-c', 'commit.gpgsign=false', *args], check=True, capture_output=True)

    def fork(self, root):
        """A clone of a fork of `source`, with `source` as its upstream remote."""
        source, fork, repo = root / 'source', root / 'fork.git', root / 'repo'
        self.git('init', '-q', '-b', 'main', str(source))
        self.git('-C', str(source), 'commit', '--allow-empty', '-qm', 'one')
        self.git('clone', '-q', '--bare', str(source), str(fork))
        self.git('clone', '-q', str(fork), str(repo))
        self.git('-C', str(repo), 'remote', 'add', 'upstream', str(source))
        return source, repo

    def test_fork_reports_commits_behind_its_upstream_remote(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, repo = self.fork(Path(tmp))
            with patch.object(cc, 'REPO', repo):
                self.assertEqual(cc.check_repo(False), [])
                self.git('-C', str(source), 'commit', '--allow-empty', '-qm', 'two')
                self.assertEqual(cc.check_repo(False),
                                 ['1 commit(s) behind upstream/main, merge it then install'])

    def test_unreachable_upstream_is_reported_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, repo = self.fork(Path(tmp))
            self.git('-C', str(repo), 'remote', 'set-url', 'upstream', str(Path(tmp) / 'gone'))
            with patch.object(cc, 'REPO', repo):
                [line] = cc.check_repo(False)
            self.assertRegex(line, r'^upstream fetch failed \(.+\)$')

    def test_fork_branch_that_upstream_lacks_reports_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, repo = self.fork(Path(tmp))
            self.git('-C', str(repo), 'checkout', '-q', '-b', 'fix-x')
            self.git('-C', str(repo), 'push', '-q', '-u', 'origin', 'fix-x')
            self.git('-C', str(source), 'commit', '--allow-empty', '-qm', 'two')
            with patch.object(cc, 'REPO', repo):
                self.assertEqual(cc.check_repo(False), [])

    def test_clone_without_upstream_remote_skips_the_fork_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, repo = Path(tmp) / 'source', Path(tmp) / 'repo'
            self.git('init', '-q', '-b', 'main', str(source))
            self.git('-C', str(source), 'commit', '--allow-empty', '-qm', 'one')
            self.git('clone', '-q', str(source), str(repo))
            with patch.object(cc, 'REPO', repo):
                self.assertEqual(cc.check_repo(False), [])

    def test_branch_tracking_upstream_reports_drift_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, repo = Path(tmp) / 'source', Path(tmp) / 'repo'
            self.git('init', '-q', '-b', 'main', str(source))
            self.git('-C', str(source), 'commit', '--allow-empty', '-qm', 'one')
            self.git('clone', '-q', '-o', 'upstream', str(source), str(repo))
            self.git('-C', str(source), 'commit', '--allow-empty', '-qm', 'two')
            with patch.object(cc, 'REPO', repo):
                self.assertEqual(cc.check_repo(False),
                                 ['1 commit(s) behind upstream/main, git pull then install'])

    def test_branch_tracking_a_local_branch_checks_upstream_for_that_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, repo = self.fork(Path(tmp))
            self.git('-C', str(repo), 'checkout', '-q', '-b', 'topic')
            self.git('-C', str(repo), 'branch', '-q', '--set-upstream-to=main')
            self.git('-C', str(source), 'commit', '--allow-empty', '-qm', 'two')
            with patch.object(cc, 'REPO', repo):
                self.assertEqual(cc.check_repo(False),
                                 ['1 commit(s) behind upstream/main, merge it then install'])


class VendorTests(unittest.TestCase):
    def test_content_shared_and_target_layers_and_failed_vendor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); upstream = root / 'upstream'; upstream.mkdir()
            subprocess.run(['git', 'init', '-q', str(upstream)], check=True)
            subprocess.run(['git', '-C', str(upstream), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', '-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '-qm', 'initial'], check=True)
            (upstream / 'LICENSE').write_text('MIT\nCopyright Test\n', newline='\n')
            (upstream / 'demo').mkdir()
            (upstream / 'demo/SKILL.md').write_text('original\n', newline='\n')
            sources = root / 'sources.tsv'
            sources.write_text(cc.HEADER + '\ndemo\thttps://example.invalid/repo.git\tdemo\tmain\t-\t-\n', newline='\n')
            support = root / 'support.tsv'; support.write_text(cc.HEADER + '\n', newline='\n')
            patches = root / 'patches'
            for layer, before, after in [('content', 'original', 'custom'), ('compat/shared', 'custom', 'portable'), ('compat/codex', 'portable', 'codex')]:
                path = patches / layer / 'demo.patch'; path.parent.mkdir(parents=True)
                path.write_text(f'--- a/SKILL.md\n+++ b/SKILL.md\n@@ -1 +1 @@\n-{before}\n+{after}\n', newline='\n')
            original_reader, original_writer = cc.read_sources, cc.write_sources
            def reader(path=None):
                return original_reader(sources if path is None else path)
            def writer(items, path=None):
                return original_writer(items, sources if path is None else path)
            with patch.multiple(cc, SKILLS=root/'skills', PATCHES=patches, LICENSES=root/'licenses', NOTICE=root/'NOTICE.md', SUPPORT_SOURCES=support), patch.object(cc, 'read_sources', reader), patch.object(cc, 'write_sources', writer), patch.object(cc, 'clone', return_value=upstream), contextlib.redirect_stdout(io.StringIO()):
                cc.cmd_vendor(argparse.Namespace(names=[]))
                self.assertEqual((cc.SKILLS/'demo/SKILL.md').read_text(), 'portable\n')
                # git apply honours core.autocrlf, so Windows checkouts get CRLF here
                self.assertEqual(cc.skill_files('codex')['demo/SKILL.md'].replace(b'\r\n', b'\n'), b'codex\n')
                recorded = sources.read_bytes()
                (upstream/'demo/SKILL.md').write_text('upstream changed\n', newline='\n')
                with self.assertRaisesRegex(RuntimeError, 'PATCH FAILED'):
                    cc.cmd_vendor(argparse.Namespace(names=[]))
                self.assertEqual((cc.SKILLS/'demo/SKILL.md').read_text(), 'portable\n')
                self.assertEqual(sources.read_bytes(), recorded)


class SkillGroupTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.skills = Path(tmp.name) / 'skills'
        for rel in ('solo/SKILL.md', 'team/beta/SKILL.md', 'team/gamma/SKILL.md', 'team/gamma/scripts/run.py'):
            (self.skills / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.skills / rel).write_text(rel + '\n')
        p = patch.object(cc, 'SKILLS', self.skills)
        p.start()
        self.addCleanup(p.stop)

    def test_group_folder_installs_its_skills_flat(self):
        self.assertEqual(sorted(cc.skill_files('claude')), [
            'beta/SKILL.md', 'gamma/SKILL.md', 'gamma/scripts/run.py', 'solo/SKILL.md'])

    def test_same_name_in_two_places_fails(self):
        (self.skills / 'team/solo').mkdir()
        (self.skills / 'team/solo/SKILL.md').write_text('again\n')
        with self.assertRaisesRegex(RuntimeError, 'solo'):
            cc.skill_files('claude')


class SourceReproductionTests(unittest.TestCase):
    def test_pinned_sources_reproduce_shared_tree_and_both_targets(self):
        """Offline integration check when the vendoring cache is available."""
        import hashlib
        sources = cc.read_sources()
        for source in sources + cc.read_sources(cc.SUPPORT_SOURCES):
            cache = cc.CACHE / hashlib.sha256(source.repo.encode()).hexdigest()[:12]
            if not cache.exists() or subprocess.run(
                ['git', '-C', str(cache), 'cat-file', '-e', source.sha],
                capture_output=True,
            ).returncode:
                self.skipTest('pinned upstream commits are not cached locally')
        with tempfile.TemporaryDirectory() as tmp:
            for source in sources:
                with self.subTest(skill=source.name):
                    cache = cc.CACHE / hashlib.sha256(source.repo.encode()).hexdigest()[:12]
                    stage = Path(tmp) / source.name
                    stage.mkdir()
                    names = cc.run(['git', '-C', str(cache), 'ls-tree', '-r', '--name-only', source.sha, '--', source.path]).splitlines()
                    for name in names:
                        dest = stage / Path(name).relative_to(source.path)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(subprocess.check_output(['git', '-C', str(cache), 'show', source.sha + ':' + name]))
                    self.assertEqual(cc.tree_hash(stage), source.content)
                    for asset in cc.read_sources(cc.SUPPORT_SOURCES):
                        owner, _, rel = asset.name.partition('/')
                        if owner == source.name:
                            asset_cache = cc.CACHE / hashlib.sha256(asset.repo.encode()).hexdigest()[:12]
                            dest = stage / rel
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            dest.write_bytes(subprocess.check_output(['git', '-C', str(asset_cache), 'show', asset.sha + ':' + asset.path]))
                            self.assertEqual(cc.tree_hash(dest), asset.content)
                    cc.rewrite_refs(stage, cc.rename_map(sources), Path(source.path).name, source.name)
                    cc.apply_patch(source.name, stage)
                    cc.apply_patch(source.name, stage, 'compat/shared')
                    self.assertEqual(cc.tree_hash(stage), cc.tree_hash(cc.SKILLS / source.name))
                    for target in ('claude', 'codex'):
                        rendered = Path(tmp) / (source.name + '-' + target)
                        shutil.copytree(stage, rendered)
                        cc.apply_patch(source.name, rendered, 'compat/' + target)


@unittest.skipUnless(shutil.which('codex'), 'Codex CLI is not installed')
class CodexDiscoveryTests(unittest.TestCase):
    def test_global_instructions_project_fallback_and_skill_policy(self):
        # debug prompt-input renders context locally; it does not run a model.
        with tempfile.TemporaryDirectory(prefix='cc-discovery-') as tmp:
            root = Path(tmp)
            cfg, project = root / 'codex', root / 'project'
            cfg.mkdir(); project.mkdir()
            subprocess.run(['git', 'init', '-q', str(project)], check=True)
            (cfg / 'config.toml').write_bytes(cc.render_codex_settings(cfg))
            (cfg / 'AGENTS.md').write_bytes(cc.render_instructions('codex'))
            (project / 'CLAUDE.md').write_text('CC_FALLBACK_DISCOVERY_TEST\n')
            for rel, data in cc.skill_files('codex').items():
                path = project / '.agents/skills' / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            result = subprocess.run(
                ['codex', 'debug', 'prompt-input', 'Inspect skills.'],
                cwd=project, env=dict(os.environ, CODEX_HOME=str(cfg)),
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode and ('unrecognized subcommand' in result.stderr):
                self.skipTest('this Codex version has no debug prompt-input command')
            self.assertEqual(result.returncode, 0, result.stderr)
            texts = [item.get('text', '') for message in json.loads(result.stdout)
                     for item in message.get('content', []) if isinstance(item, dict)]
            catalog = '\n'.join(text for text in texts if '<skills_instructions>' in text)
            self.assertTrue(any('Working agreements' in text for text in texts))
            self.assertTrue(any('CC_FALLBACK_DISCOVERY_TEST' in text for text in texts))
            self.assertIn('- tdd:', catalog)
            self.assertNotIn('- review-loop:', catalog)


if __name__ == "__main__":
    unittest.main()
