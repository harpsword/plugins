#!/usr/bin/env python3
"""Exercise bootstrap.ts with real Bun processes and a network-free install stub.

Set PSTACK_TEST_BUN to an absolute Bun executable if it is not on PATH.
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "pstack/codex/overrides/skills/poteto-mode/scripts/bootstrap.ts"
BUN = os.environ.get('PSTACK_TEST_BUN') or shutil.which('bun')

MOCK_BUN = r"""
const fs = require('fs');
const path = require('path');
const originalSpawnSync = Bun.spawnSync;
Bun.spawnSync = function(argv, options) {
  const install = argv[1] === 'install';
  fs.appendFileSync(process.env.TEST_LOG, JSON.stringify({
    kind: install ? 'install' : 'relaunch', argv, cwd: options.cwd
  }) + '\n');
  if (install) {
    if (process.env.TEST_INSTALL_FAILURE) return {
      exitCode: 7, stdout: Buffer.from('install output\n'), stderr: Buffer.from('install error\n')
    };
    const moduleDir = path.join(options.cwd, 'node_modules', 'commander');
    fs.mkdirSync(moduleDir, { recursive: true });
    fs.writeFileSync(path.join(moduleDir, 'package.json'),
      JSON.stringify({ type: 'module', main: 'index.js' }));
    fs.writeFileSync(path.join(moduleDir, 'index.js'), 'export const token = "installed";');
    if (process.env.TEST_MUTATE_BUNDLE) {
      fs.writeFileSync(path.join(options.cwd, 'unexpected-file'), 'install changed bundle');
    }
    return { exitCode: 0, stdout: Buffer.from('install progress\n'), stderr: Buffer.alloc(0) };
  }
  return originalSpawnSync(argv, options);
};
"""

ENTRYPOINT = """
import { ensureDependenciesInstalled } from '../bootstrap.ts';
import { fileURLToPath } from 'node:url';
import { readFileSync } from 'node:fs';
ensureDependenciesInstalled();
const { token } = await import('commander');
console.log(JSON.stringify({ token, argv: process.argv.slice(2), cwd: process.cwd(),
  env: process.env.TEST_PRESERVED, entrypoint: fileURLToPath(import.meta.url),
  resource: readFileSync(new URL('../resources/nested/value.txt', import.meta.url), 'utf8') }));
process.exitCode = Number(process.env.TEST_EXIT_CODE || 0);
"""


@unittest.skipUnless(BUN, 'Bun is required; set PSTACK_TEST_BUN or put bun on PATH')
class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pstack runtime ')
        self.base = Path(self.temp.name).resolve()
        self.package = self.base / 'immutable plugin cache'
        self.scripts = self.package / 'skills/poteto-mode/scripts'
        self.tools = self.base / 'current run/tools with spaces'
        self.cwd = self.base / 'consumer project'
        self.cwd.mkdir()
        (self.package / '.codex-plugin').mkdir(parents=True)
        (self.package / '.codex-plugin/plugin.json').write_text('{}')
        for directory in ('orch', 'watch-pr', 'resources/nested'):
            (self.scripts / directory).mkdir(parents=True)
        (self.scripts / 'bootstrap.ts').write_text(BOOTSTRAP.read_text())
        (self.scripts / 'package.json').write_text('{"type":"module"}')
        (self.scripts / 'bun.lock').write_text('fixture lock')
        (self.scripts / 'resources/nested/value.txt').write_text('complete bundle v1')
        (self.scripts / 'orch/orch.ts').write_text(ENTRYPOINT)
        (self.scripts / 'watch-pr/watch-pr').write_text(ENTRYPOINT)
        self.mock = self.base / 'mock-bun.cjs'
        self.mock.write_text(MOCK_BUN)
        self.log = self.base / 'calls.jsonl'
        self.original = self.snapshot()

    def tearDown(self):
        self.assertEqual(self.original, self.snapshot(), 'installed package was modified')
        self.temp.cleanup()

    def snapshot(self):
        return {str(p.relative_to(self.package)): hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
                for p in self.package.rglob('*')}

    def invoke(self, entrypoint='orch/orch.ts', args=(), **overrides):
        env = {key: value for key, value in os.environ.items()
               if key not in ('PSTACK_TOOLS_DIR', 'PSTACK_RUN_DIR', 'NODE_OPTIONS')}
        env.update(PSTACK_TOOLS_DIR=str(self.tools), TEST_LOG=str(self.log),
                   TEST_PRESERVED='env with spaces')
        for key, value in overrides.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        return subprocess.run([BUN, '--preload', str(self.mock), str(self.scripts / entrypoint), *args],
                              cwd=self.cwd, env=env, text=True, capture_output=True, timeout=15)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_relocates_complete_bundle_and_preserves_process_contract(self):
        result = self.invoke(args=('status', '--store', 'store with spaces', '--json'))
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = json.loads(result.stdout)
        self.assertEqual(observed['argv'], ['status', '--store', 'store with spaces', '--json'])
        self.assertEqual(observed['cwd'], str(self.cwd))
        self.assertEqual(observed['env'], 'env with spaces')
        self.assertEqual(observed['token'], 'installed')
        self.assertEqual(observed['resource'], 'complete bundle v1')
        self.assertTrue(Path(observed['entrypoint']).is_relative_to(self.tools))
        calls = self.calls()
        self.assertEqual([call['kind'] for call in calls], ['install', 'relaunch'])
        self.assertTrue(Path(calls[0]['cwd']).is_relative_to(self.tools))

    def test_reuses_current_bundle_without_reinstall(self):
        for _ in range(2):
            result = self.invoke()
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([call['kind'] for call in self.calls()], ['install', 'relaunch', 'relaunch'])

    def test_executes_with_read_only_installed_package(self):
        paths = [self.package, *self.package.rglob('*')]
        original_modes = {path: path.stat().st_mode & 0o777 for path in paths}
        try:
            for path in paths:
                path.chmod(0o555 if path.is_dir() else 0o444)
            result = self.invoke()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['token'], 'installed')
        finally:
            for path, mode in original_modes.items():
                path.chmod(mode)

    def test_concurrent_invocations_publish_complete_runtime(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: self.invoke(), range(2)))
        for result in results:
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(results[0].stdout)['entrypoint'], json.loads(results[1].stdout)['entrypoint'])
        self.assertFalse(any(path.name.startswith('.pstack-stage-') for path in self.tools.iterdir()))

    def test_extensionless_entrypoint_and_exit_code(self):
        result = self.invoke('watch-pr/watch-pr', args=('42', '--watch'), TEST_EXIT_CODE='23')
        self.assertEqual(result.returncode, 23, result.stderr)
        observed = json.loads(result.stdout)
        self.assertEqual(observed['argv'], ['42', '--watch'])
        self.assertTrue(observed['entrypoint'].endswith('/watch-pr/watch-pr'))

    def test_content_change_uses_fresh_runtime(self):
        first = self.invoke()
        self.assertEqual(first.returncode, 0, first.stderr)
        resource = self.scripts / 'resources/nested/value.txt'
        resource.write_text('complete bundle v2')
        self.original = self.snapshot()
        second = self.invoke()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertNotEqual(json.loads(first.stdout)['entrypoint'], json.loads(second.stdout)['entrypoint'])
        self.assertEqual(json.loads(second.stdout)['resource'], 'complete bundle v2')
        self.assertEqual(sum(call['kind'] == 'install' for call in self.calls()), 2)

    def test_run_directory_fallback(self):
        result = self.invoke(PSTACK_TOOLS_DIR=None, PSTACK_RUN_DIR=str(self.tools.parent))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(Path(json.loads(result.stdout)['entrypoint']).is_relative_to(self.tools.parent / 'tools'))

    def test_missing_relative_or_unusable_destination_fails_before_install(self):
        unusable = self.base / 'ordinary file'
        unusable.write_text('not a directory')
        for destination in (None, 'relative tools', str(unusable)):
            with self.subTest(destination=destination):
                result = self.invoke(PSTACK_TOOLS_DIR=destination)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('absolute writable directory dedicated to this run', result.stderr)
                self.assertEqual(self.calls(), [])

    def test_rejects_plugin_destination_including_symlink(self):
        alias = self.base / 'cache alias'
        alias.symlink_to(self.package, target_is_directory=True)
        for destination in (self.package / 'tools', alias / 'tools'):
            result = self.invoke(PSTACK_TOOLS_DIR=str(destination))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('outside the installed plugin package', result.stderr)
            self.assertEqual(self.calls(), [])

    def test_failed_install_does_not_publish_and_retry_succeeds(self):
        failed = self.invoke(TEST_INSTALL_FAILURE='1')
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('exited with status 7', failed.stderr)
        self.assertIn('install output', failed.stderr)
        self.assertIn('install error', failed.stderr)
        self.assertEqual(list(self.tools.iterdir()), [])
        retried = self.invoke()
        self.assertEqual(retried.returncode, 0, retried.stderr)

    def test_install_mutation_fails_without_restart_loop(self):
        result = self.invoke(TEST_MUTATE_BUNDLE='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Incomplete pstack tools runtime', result.stderr)
        self.assertEqual([call['kind'] for call in self.calls()], ['install', 'relaunch'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
