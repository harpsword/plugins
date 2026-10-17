#!/usr/bin/env python3
import importlib.util
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('builder', ROOT / 'scripts/build-pstack-codex.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PackagePreservation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pstack source ')
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'source'
        shutil.copytree(builder.SOURCE, self.source,
                        ignore=shutil.ignore_patterns('node_modules', '__pycache__'))
        self.package = Path(self.temp.name) / 'installed package'
        patch = mock.patch.object(builder, 'SOURCE', self.source)
        patch.start()
        self.addCleanup(patch.stop)

    def package_bytes(self):
        return {path.relative_to(self.package).as_posix(): path.read_bytes()
                for path in self.package.rglob('*') if path.is_file()}

    def test_upstream_prose_and_new_requirement_survive(self):
        skill = self.source / 'skills/how/SKILL.md'
        text = skill.read_text()
        paragraph = next(line for line in text.splitlines() if line.startswith('Every spawn is a Task'))
        rewritten = 'Every explanation starts with fresh Cursor Task explorers using the configured model.'
        requirement = 'Before explaining a subsystem, inspect one representative caller and report its assumptions.'
        skill.write_text(text.replace(paragraph, rewritten) + '\n' + requirement + '\n')
        builder.build(self.package)
        packaged = (self.package / 'skills/how/SKILL.md').read_text()
        self.assertIn(rewritten + '\n', packaged)
        self.assertIn('\n' + requirement + '\n', packaged)
        self.assertNotIn(paragraph, packaged)

    def test_native_source_changes_preserve_existing_output(self):
        builder.build(self.package)
        before = self.package_bytes()
        source = self.source / 'skills/setup-pstack/SKILL.md'
        source.write_bytes(source.read_bytes() + b'\nUpstream added a requirement.\n')
        with self.assertRaisesRegex(ValueError, 'Upstream override source changed'):
            builder.build(self.package)
        self.assertEqual(self.package_bytes(), before)

    def test_restored_upstream_bot_and_bootstrap_survive(self):
        bot = self.source / 'skills/make-bot-ui/SKILL.md'
        bot.write_text(bot.read_text() + '\nAn upstream bot requirement.\n')
        bootstrap = self.source / 'skills/poteto-mode/scripts/bootstrap.ts'
        bootstrap.write_text(bootstrap.read_text() + '\nexport const upstreamRevision = 2;\n')
        builder.build(self.package)
        _, _, body = builder.frontmatter(bot.read_text())
        self.assertTrue((self.package / bot.relative_to(self.source)).read_text().endswith(body))
        self.assertEqual((self.package / bootstrap.relative_to(self.source)).read_bytes(), bootstrap.read_bytes())

    def test_missing_executable_anchor_preserves_existing_output(self):
        builder.build(self.package)
        before = self.package_bytes()
        checker = self.source / 'skills/poteto-mode/scripts/check-plan.mjs'
        original = checker.read_text()
        marker = 'const PROGRAM_MARKERS = ["git show origin/main:", "/loop 1h", "status message"];'
        self.assertIn(marker, original)
        checker.write_text(original.replace(marker, 'const PROGRAM_MARKERS = ["changed upstream"];'))
        with self.assertRaisesRegex(ValueError, 'Upstream adapter anchor changed'):
            builder.build(self.package)
        self.assertEqual(self.package_bytes(), before)

    def test_removed_resource_does_not_survive_rebuild(self):
        resource = self.source / 'skills/how/references/temporary-guide.md'
        resource.write_text('An upstream guide that will be retired.\n')
        builder.build(self.package)
        packaged = self.package / resource.relative_to(self.source)
        self.assertEqual(packaged.read_text(), 'An upstream guide that will be retired.\n')
        resource.unlink()
        builder.build(self.package)
        self.assertFalse(packaged.exists())
        self.assertTrue((self.package / 'skills/how/SKILL.md').is_file())


class PlanCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='pstack adapter ')
        cls.package = builder.build(Path(cls.temp.name) / 'installed package')
        cls.checker = cls.package / 'skills/poteto-mode/scripts/check-plan.mjs'
        fixture = (cls.checker.parent / 'check-plan.test.ts').read_text()
        rule = re.search(r'const rule =\s*("[^"]+");', fixture).group(1)
        plan = fixture.split('const validPlan = ', 1)[1].split('\nconst runPlan', 1)[0]
        cls.plan = subprocess.check_output(
            ['node', '-e', f'const rule = {rule}; const plan = {plan}\nprocess.stdout.write(plan);'], text=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check(self, plan, expected, error=None):
        path = Path(self.temp.name) / 'plan.md'
        path.write_text(plan)
        result = subprocess.run(['node', str(self.checker), str(path)], text=True, capture_output=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        if error:
            self.assertIn(error, result.stderr)

    def test_accepts_original_upstream_fixture(self):
        self.check(self.plan, 0)

    def test_accepts_codex_plan_without_cursor_markers_or_custom_grammar(self):
        plan = self.plan.replace('`git show origin/main:` /loop 1h status message',
                                 'Read the recorded package paths and send a status message when changed.')
        self.check(plan, 0)

    def test_rejects_missing_upstream_program_section(self):
        self.check(self.plan.replace('### Boot recipe', 'Boot instructions'), 1,
                   error='Program checklist lacks "### Boot recipe"')

    def test_rejects_missing_status_message(self):
        self.check(self.plan.replace('status message', 'progress report'), 1,
                   error='Program checklist lacks "status message"')


if __name__ == '__main__':
    unittest.main()
