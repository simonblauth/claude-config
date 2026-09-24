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


class InstallTests(unittest.TestCase):
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
        bin_dir = self.base / 'bin'; bin_dir.mkdir()
        (bin_dir / 'git').symlink_to(shutil.which('git'))
        with patch.dict(os.environ, {'PATH': str(bin_dir)}):
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


class VendorTests(unittest.TestCase):
    def test_content_shared_and_target_layers_and_failed_vendor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); upstream = root / 'upstream'; upstream.mkdir()
            subprocess.run(['git', 'init', '-q', str(upstream)], check=True)
            subprocess.run(['git', '-C', str(upstream), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', '-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '-qm', 'initial'], check=True)
            (upstream / 'LICENSE').write_text('MIT\nCopyright Test\n')
            (upstream / 'demo').mkdir()
            (upstream / 'demo/SKILL.md').write_text('original\n')
            sources = root / 'sources.tsv'
            sources.write_text(cc.HEADER + '\ndemo\thttps://example.invalid/repo.git\tdemo\tmain\t-\t-\n')
            support = root / 'support.tsv'; support.write_text(cc.HEADER + '\n')
            patches = root / 'patches'
            for layer, before, after in [('content', 'original', 'custom'), ('compat/shared', 'custom', 'portable'), ('compat/codex', 'portable', 'codex')]:
                path = patches / layer / 'demo.patch'; path.parent.mkdir(parents=True)
                path.write_text(f'--- a/SKILL.md\n+++ b/SKILL.md\n@@ -1 +1 @@\n-{before}\n+{after}\n')
            original_reader, original_writer = cc.read_sources, cc.write_sources
            def reader(path=None):
                return original_reader(sources if path is None else path)
            def writer(items, path=None):
                return original_writer(items, sources if path is None else path)
            with patch.multiple(cc, SKILLS=root/'skills', PATCHES=patches, LICENSES=root/'licenses', NOTICE=root/'NOTICE.md', SUPPORT_SOURCES=support), patch.object(cc, 'read_sources', reader), patch.object(cc, 'write_sources', writer), patch.object(cc, 'clone', return_value=upstream), contextlib.redirect_stdout(io.StringIO()):
                cc.cmd_vendor(argparse.Namespace(names=[]))
                self.assertEqual((cc.SKILLS/'demo/SKILL.md').read_text(), 'portable\n')
                self.assertEqual(cc.skill_files('codex')['demo/SKILL.md'], b'codex\n')
                recorded = sources.read_bytes()
                (upstream/'demo/SKILL.md').write_text('upstream changed\n')
                with self.assertRaisesRegex(RuntimeError, 'PATCH FAILED'):
                    cc.cmd_vendor(argparse.Namespace(names=[]))
                self.assertEqual((cc.SKILLS/'demo/SKILL.md').read_text(), 'portable\n')
                self.assertEqual(sources.read_bytes(), recorded)


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
