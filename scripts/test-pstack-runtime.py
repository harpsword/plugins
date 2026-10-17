#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUN = os.environ.get('PSTACK_TEST_BUN') or shutil.which('bun')
spec = importlib.util.spec_from_file_location('builder', ROOT / 'scripts/build-pstack-codex.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

INSTALL_PRELOAD = r"""
const fs = require('node:fs');
const path = require('node:path');
const spawnSync = Bun.spawnSync;
Bun.spawnSync = function(argv, options) {
  if (argv[1] === 'install') {
    fs.appendFileSync(process.env.TEST_INSTALL_LOG, JSON.stringify({
      argv, cwd: options.cwd,
      ready: fs.existsSync(process.env.TEST_READY_FILE),
      marker: fs.existsSync(path.join(options.cwd, 'node_modules', '.poteto-mode-tools-install-key'))
    }) + '\n');
    if (process.env.TEST_FAIL_INSTALL === '1') return {
      exitCode: 7,
      stdout: Buffer.from('dependency install output\n'),
      stderr: Buffer.from('dependency install failed\n')
    };
  }
  return spawnSync(argv, options);
};
"""


def snapshot(root):
    return {
        str(path.relative_to(root)): (
            stat.S_IMODE(path.stat().st_mode),
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None,
        )
        for path in (root, *root.rglob('*'))
    }


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not BUN or not shutil.which(BUN):
            raise RuntimeError('Bun is required. Set PSTACK_TEST_BUN or put bun on PATH.')
        cls.bun = str(Path(shutil.which(BUN)).absolute())
        cls.package_temp = tempfile.TemporaryDirectory(prefix='pstack generated runtime ')
        cls.package = builder.build(Path(cls.package_temp.name) / 'immutable plugin cache')
        cls.scripts = cls.package / 'skills/poteto-mode/scripts'
        for path in (cls.package, *cls.package.rglob('*')):
            path.chmod(stat.S_IMODE(path.stat().st_mode) & ~0o222)
        cls.original = snapshot(cls.package)

    @classmethod
    def tearDownClass(cls):
        for path in (cls.package, *cls.package.rglob('*')):
            if path.is_dir():
                path.chmod(stat.S_IMODE(path.stat().st_mode) | stat.S_IWUSR)
        cls.package_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pstack runtime ')
        self.base = Path(self.temp.name).resolve()
        self.run = self.base / 'current run'
        self.run.mkdir()
        self.tools = self.run / 'tools with spaces'
        self.ready = self.run / 'ready-tools.txt'
        self.cwd = self.base / 'consumer project'
        self.cwd.mkdir()
        self.preload = self.base / 'install-preload.cjs'
        self.preload.write_text(INSTALL_PRELOAD)
        self.log = self.base / 'install calls.jsonl'
        self.env = {key: value for key, value in os.environ.items()
                    if key not in ('PSTACK_TOOLS_DIR', 'PSTACK_RUN_DIR', 'ORCH_STORE',
                                   'ORCH_REPO', 'NODE_OPTIONS', 'BUN_OPTIONS')}
        self.env.update(PATH=str(Path(self.bun).parent) + os.pathsep + self.env.get('PATH', ''),
                        TEST_INSTALL_LOG=str(self.log), TEST_READY_FILE=str(self.ready))

    def tearDown(self):
        try:
            self.assertEqual(self.original, snapshot(self.package),
                             'installed package bytes or modes changed')
        finally:
            for path in self.base.rglob('*'):
                if path.is_dir():
                    path.chmod(stat.S_IMODE(path.stat().st_mode) | stat.S_IWUSR)
            self.temp.cleanup()

    def execute(self, argv, **env):
        return subprocess.run(argv, cwd=self.cwd, env={**self.env, **env},
                              text=True, capture_output=True, timeout=120)

    def copy_command(self, tools):
        quote = shlex.quote
        return (f'mkdir {quote(str(tools))} &&\n'
                f'cp -R {quote(str(self.scripts) + "/.")} {quote(str(tools) + "/")} &&\n'
                f'chmod u+w {quote(str(tools))}')

    def prepare(self, tools=None, preload=False, **env):
        tools = tools or self.tools
        argv = [self.bun]
        if preload:
            argv.extend(('--preload', str(self.preload)))
        argv.extend((str(tools / 'orch/orch.ts'), '--help'))
        command = (self.copy_command(tools) + ' &&\n' + shlex.join(argv) + ' &&\n'
                   + f'printf \'%s\\n\' {shlex.quote(str(tools))} > {shlex.quote(str(self.ready))}')
        return self.execute(['sh', '-c', command], **env)

    def invoke(self, entrypoint='orch/orch.ts', args=(), tools=None, preload=False, **env):
        argv = [self.bun]
        if preload:
            argv.extend(('--preload', str(self.preload)))
        argv.extend((str((tools or self.tools) / entrypoint), *args))
        return self.execute(argv, **env)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def install_calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def assert_ready(self, tools=None):
        tools = tools or self.tools
        self.assertEqual(self.ready.read_text(), str(tools) + '\n')
        expected = hashlib.sha256((tools / 'package.json').read_bytes() + b'\0'
                                  + (tools / 'bun.lock').read_bytes()).hexdigest()
        self.assertEqual((tools / 'node_modules/.poteto-mode-tools-install-key').read_text(), expected + '\n')
        self.assertTrue((tools / 'node_modules/commander/package.json').is_file())

    def test_fresh_copy_is_complete_writable_and_ready_after_real_initialization(self):
        result = self.prepare(preload=True)
        self.assert_success(result)
        self.assertIn('Usage: orch', result.stdout)
        self.assert_ready()
        self.assertEqual(stat.S_IMODE(self.tools.stat().st_mode),
                         stat.S_IMODE(self.scripts.stat().st_mode) | stat.S_IWUSR)
        probe = self.tools / 'writable-root-probe'
        probe.write_text('writable')
        probe.unlink()
        for relative, (mode, digest) in snapshot(self.scripts).items():
            if relative != '.':
                copied = self.tools / relative
                self.assertEqual(stat.S_IMODE(copied.stat().st_mode), mode, relative)
                if digest is not None:
                    self.assertEqual(hashlib.sha256(copied.read_bytes()).hexdigest(), digest, relative)
        calls = self.install_calls()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['argv'][1:], ['install', '--frozen-lockfile'])
        self.assertEqual(calls[0]['cwd'], str(self.tools))
        self.assertEqual((calls[0]['ready'], calls[0]['marker']), (False, False))

    def test_warm_copy_reuses_both_actual_entrypoints_without_installing(self):
        self.assert_success(self.prepare())
        marker = self.tools / 'node_modules/.poteto-mode-tools-install-key'
        before = marker.read_bytes(), marker.stat().st_mtime_ns
        for entrypoint, expected in (('orch/orch.ts', 'Usage: orch'),
                                     ('watch-pr/watch-pr', 'Usage: watch-pr')):
            with self.subTest(entrypoint=entrypoint):
                result = self.invoke(entrypoint, ('--help',), preload=True, TEST_FAIL_INSTALL='1')
                self.assert_success(result)
                self.assertIn(expected, result.stdout)
        self.assertEqual(self.install_calls(), [])
        self.assertEqual((marker.read_bytes(), marker.stat().st_mtime_ns), before)
        self.assert_ready()

    def test_failed_initialization_does_not_publish_and_fresh_retry_succeeds(self):
        failed = self.prepare(preload=True, TEST_FAIL_INSTALL='1')
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('exited with status 7', failed.stderr)
        self.assertIn('dependency install output', failed.stdout)
        self.assertIn('dependency install failed', failed.stderr)
        self.assertFalse(self.ready.exists())
        self.assertFalse((self.tools / 'node_modules/.poteto-mode-tools-install-key').exists())
        self.assertEqual(len(self.install_calls()), 1)
        self.assertEqual(self.install_calls()[0]['ready'], False)
        failed_copy = snapshot(self.tools)
        retry = self.run / 'fresh retry tools'
        self.assert_success(self.prepare(retry))
        self.assert_ready(retry)
        self.assertEqual(snapshot(self.tools), failed_copy)

    def test_existing_tools_destination_stops_before_initialization(self):
        self.tools.mkdir()
        sentinel = self.tools / 'active consumer data'
        sentinel.write_text('preserve this copy')
        before = snapshot(self.tools)
        result = self.prepare(preload=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(snapshot(self.tools), before)
        self.assertEqual(self.install_calls(), [])
        self.assertFalse(self.ready.exists())

    def test_bare_install_is_not_ready_until_copied_entrypoint_runs(self):
        self.assert_success(self.execute(['sh', '-c', self.copy_command(self.tools)]))
        result = subprocess.run([self.bun, 'install', '--frozen-lockfile'], cwd=self.tools,
                                env=self.env, text=True, capture_output=True, timeout=120)
        self.assert_success(result)
        self.assertFalse((self.tools / 'node_modules/.poteto-mode-tools-install-key').exists())
        self.assertFalse(self.ready.exists())
        self.assert_success(self.invoke(args=('--help',), preload=True))
        self.assertEqual(len(self.install_calls()), 1)
        self.assertTrue((self.tools / 'node_modules/.poteto-mode-tools-install-key').is_file())

    def test_cold_bootstrap_preserves_relative_store_argument_and_consumer_cwd(self):
        self.assert_success(self.execute(['sh', '-c', self.copy_command(self.tools)]))
        result = self.invoke(args=('init', '--store', 'ledger with spaces', '--json'))
        self.assert_success(result)
        store = self.cwd / 'ledger with spaces'
        self.assertEqual(json.loads(result.stdout[result.stdout.index('{'):]), {'store': str(store)})
        self.assertEqual((store / 'units.tsv').read_text(), 'id\ttrack\tstate\tbranch\tpr\tsha\tbrief\n')
        self.assertFalse((self.tools / 'ledger with spaces').exists())
        result = self.invoke(args=('unit', 'add', 'work-1', '--track', 'track with spaces',
                                   '--brief', 'brief with spaces.md', '--store', 'ledger with spaces', '--json'))
        self.assert_success(result)
        unit = json.loads(result.stdout)
        self.assertEqual((unit['id'], unit['track'], unit['brief']),
                         ('work-1', 'track with spaces', 'brief with spaces.md'))

    def test_actual_entrypoints_preserve_error_exit_codes(self):
        self.assert_success(self.prepare())
        self.assert_success(self.invoke(args=('init', '--store', 'ledger with spaces')))
        cold = self.run / 'cold error tools'
        self.assert_success(self.execute(['sh', '-c', self.copy_command(cold)]))
        missing = self.invoke(tools=cold, args=('unit', 'get', 'absent', '--store', 'ledger with spaces'))
        self.assertEqual(missing.returncode, 2, missing.stdout + missing.stderr)
        self.assertEqual(missing.stderr, 'error: unit absent not found\n')
        invalid = self.invoke(args=('--invalid-option',))
        self.assertEqual(invalid.returncode, 1, invalid.stdout + invalid.stderr)
        self.assertIn("error: unknown option '--invalid-option'", invalid.stderr)
        watcher = self.invoke('watch-pr/watch-pr', ('--pr', 'invalid'))
        self.assertEqual(watcher.returncode, 64, watcher.stdout + watcher.stderr)
        self.assertIn('must be a positive integer', watcher.stderr)

    def test_original_bundled_bun_tests_run_from_ready_copy(self):
        self.assert_success(self.prepare())
        self.assert_ready()
        result = subprocess.run([self.bun, 'test', 'orch', 'watch-pr', 'check-plan.test.ts'],
                                cwd=self.tools, env=self.env, text=True, capture_output=True, timeout=120)
        self.assert_success(result)
        self.assertRegex(result.stderr, r'\b[1-9][0-9]* pass\b')
        self.assertRegex(result.stderr, r'\b0 fail\b')


if __name__ == '__main__':
    unittest.main(verbosity=2)
