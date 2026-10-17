#!/usr/bin/env python3
"""Validate the full Codex package, resource graph, policies, and host adapters."""

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('build_pstack', ROOT / 'scripts/build-pstack-codex.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and 'node_modules' not in p.parts}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_package(plugin):
    source = ROOT / 'pstack'
    manifest = json.loads((plugin / '.codex-plugin/plugin.json').read_text())
    cursor = json.loads((source / '.cursor-plugin/plugin.json').read_text())
    require(manifest['name'] == cursor['name'] == 'pstack', 'plugin identity')
    require(manifest['skills'] == './skills/', 'Codex skill root')
    require(not (plugin / 'plugin.json').exists(), 'portable manifest would bypass adapter')
    expected = {p.parent.name for p in (source / 'skills').glob('*/SKILL.md')}
    actual = {p.parent.name for p in (plugin / 'skills').glob('*/SKILL.md')}
    require(expected == actual and len(actual) == 54, 'all 54 upstream skills must be exposed')
    automatic = []
    for name in sorted(expected):
        skill = plugin / 'skills' / name / 'SKILL.md'
        description, _, body = builder.frontmatter(skill.read_text())
        _, explicit, _ = builder.frontmatter((source / 'skills' / name / 'SKILL.md').read_text())
        require(bool(description.strip()), f'{name}: empty description')
        require(f'\nname: {name}\n' in skill.read_text(), f'{name}: invalid identity')
        policy = (skill.parent / 'agents/openai.yaml').read_text()
        require(policy == 'policy:\n  allow_implicit_invocation: ' + str(not explicit).lower() + '\n',
                f'{name}: invocation policy drift')
        require('the Codex runtime adapter' in body, f'{name}: runtime not reachable')
        if not explicit:
            automatic.append(name)
    require(automatic == ['setup-pstack'], 'automatic entrypoints changed')

    # Every upstream skill asset and delegate brief must survive packaging.
    for folder in ('skills', 'agents'):
        for original in (source / folder).rglob('*'):
            if original.is_file() and 'node_modules' not in original.parts:
                require((plugin / original.relative_to(source)).is_file(), f'missing resource: {original}')
    markdown = list(plugin.rglob('*.md'))
    forbidden = ('~/.cursor/', '.cursor/skills/', 'pstack-models.mdc', 'cloud_base_branch',
                 'git show origin/main:pstack/', 'node pstack/skills/', 'path in the system prompt',
                 'cloud default', 'Chain rebases run in cloud', 'via the loop skill',
                 'subagent_type:', 'grok-4.7-', 'claude-opus-5-5-', 'run_in_background:', '/loop',
                 'allow_multiple:', 'from `cursor-team-kit`', '`/deslop`', 'on a lane VM',
                 'without waiting for its stop to land', 'Each tick re-reads both playbooks from trunk',
                 "On the operator's go, arm `heartbeat 1h`",
                 'Stand down a stuck lane and dispatch its replacement now.')
    for path in markdown:
        text = path.read_text()
        for token in forbidden:
            require(token not in text, f'{path}: unadapted host token {token}')
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
            if '://' in target or target.startswith('#') or target == 'url':
                continue  # Upstream synthesizer template contains literal [label](url).
            resource = (path.parent / target.split('#', 1)[0]).resolve()
            require(resource.is_relative_to(plugin.resolve()), f'escaping reference: {path}: {target}')
            require(resource.exists(), f'broken reference: {path}: {target}')
    # Principles remain the original rules; only host vocabulary and runtime pointer differ.
    for name in sorted(n for n in expected if n.startswith('principle-')):
        _, _, original = builder.frontmatter((source / 'skills' / name / 'SKILL.md').read_text())
        require(builder.adapt_text(original, expected) in (plugin / 'skills' / name / 'SKILL.md').read_text(),
                f'principle body drift: {name}')
    return len(actual), len(markdown)


def check_audit(plugin):
    with tempfile.TemporaryDirectory(prefix='pstack-audit-') as directory:
        work = Path(directory)
        repo = work / 'repo'
        subprocess.run(['git', 'clone', '--quiet', '--shared', '--no-checkout', str(ROOT), str(repo)], check=True)
        subprocess.run(['git', '-C', str(repo), 'worktree', 'add', '--quiet', '--detach', str(work / 'branch'), 'HEAD'], check=True)
        # No forge credentials or network are needed to check local history-unknown behavior.
        bin_dir = work / 'bin'
        bin_dir.mkdir()
        for name in ('gh', 'origin'):
            path = bin_dir / name
            path.write_text('#!/bin/sh\nexit 1\n')
            path.chmod(0o755)
        import os
        env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ['PATH'], PSTACK_TRANSCRIPTS_DIR='')
        result = subprocess.run(['bash', str(plugin / 'skills/poteto-mode/scripts/worktree-audit.sh'),
                                 '-b', 'HEAD', str(repo)], env=env, text=True, capture_output=True, check=True)
        require('verify-chat-usage' in result.stdout, 'unknown chat usage must not be safe to prune')
        require('\tsafe\t' not in result.stdout, 'missing history cannot establish safe cleanup')


def main():
    source_before = {name: snapshot(ROOT / 'pstack' / name) for name in ('skills', 'agents')}
    catalog = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text())
    entry = next(p for p in catalog['plugins'] if p['name'] == 'pstack')
    plugin = (ROOT / entry['source']['path']).resolve()
    require(plugin == builder.DESTINATION, 'marketplace build path')
    builder.build()
    counts = check_package(plugin)
    with tempfile.TemporaryDirectory(prefix='pstack-package-') as directory:
        relocated = Path(directory) / 'pstack'
        shutil.copytree(plugin, relocated, ignore=shutil.ignore_patterns('node_modules'))
        require(check_package(relocated) == counts, 'relocation changed resources')
        before = snapshot(relocated)
        builder.build(relocated)
        require(snapshot(relocated) == before, 'build is not deterministic')
        # Exercise the broken-link failure, not only the successful traversal.
        (relocated / 'codex/runtime.md').unlink()
        try:
            check_package(relocated)
        except ValueError as error:
            require('broken reference' in str(error), str(error))
        else:
            raise ValueError('validator missed a missing runtime resource')
    check_audit(plugin)
    subprocess.run([sys.executable, str(ROOT / 'scripts/test-pstack-adapter.py')], check=True)
    require(source_before == {name: snapshot(ROOT / 'pstack' / name) for name in source_before},
            'build modified original Cursor workflows')
    print(f'PASS: {counts[0]} skills, {counts[1]} Markdown resources, 53 explicit / 1 automatic; '
          'resource inventory, links, relocation, deterministic build, failure detection, '
          'history-unknown audit, plan continuation contracts, and original source preservation.')


if __name__ == '__main__':
    main()
