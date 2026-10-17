#!/usr/bin/env python3
"""Exercise Codex plan contracts against the shipped Node checker."""
import importlib.util
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('builder', ROOT / 'scripts/build-pstack-codex.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PlanContracts(unittest.TestCase):
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
        cls.plan = re.sub(r'(?m)^.*(?:heartbeat 1h|Continuation\.).*$', '', cls.plan)
        if 'status message' not in cls.plan:
            cls.plan = cls.plan.replace('### Arm the program', '### Arm the program\nRead the installed package and send a status message when changed.')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check(self, contract, expected, extra='', error=None):
        plan = self.plan.replace('### Arm the program', '### Arm the program\n' + contract + '\n' + extra)
        path = Path(self.temp.name) / 'plan.md'
        path.write_text(plan)
        result = subprocess.run(['node', str(self.checker), str(path)], text=True, capture_output=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        if error:
            self.assertIn(error, result.stderr)

    def test_current_session(self):
        self.check('Continuation. current-session. Wait on actual workers and processes; no future wakeup.', 0)

    def test_authorized_scheduler(self):
        self.check('Continuation. authorized-heartbeat. User requested hourly follow-up; stop when all PRs finish.', 0)

    def test_missing_scheduler_disclosed(self):
        self.check('Continuation. blocked. No scheduler is exposed; future wakeups remain unavailable.', 0)

    def test_missing_continuation(self):
        self.check('', 1, error='continuation contract')

    def test_code_sample_cannot_supply_contract(self):
        self.check('```text\nContinuation. current-session. Wait on workers.\n```', 1,
                   error='continuation contract')

    def test_legacy_heartbeat_does_not_authorize_schedule(self):
        self.check('heartbeat 1h', 1, error='continuation contract')

    def test_unresolved_host_paths(self):
        for token in ('<installed-package>', '<execution playbook>', '<control skill path>',
                      '<each other leaf skill the program uses>'):
            with self.subTest(token=token):
                self.check('Continuation. current-session. Wait on workers.', 1,
                           extra=f'- [ ] Read `{token}`.', error='unresolved host reference')

    def test_real_path_and_unrelated_html(self):
        self.check('Continuation. current-session. Wait on workers.', 0,
                   extra=f'- [ ] Read `{self.package}/codex/runtime.md`.\n<details>Details</details>')


if __name__ == '__main__':
    unittest.main()
