#!/usr/bin/env python3
"""Validate the full Codex package, resource graph, policies, and host adapters."""

import hashlib
import importlib.util
import json
import os
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
    source = builder.SOURCE
    manifest = json.loads((plugin / '.codex-plugin/plugin.json').read_text())
    cursor = json.loads((source / '.cursor-plugin/plugin.json').read_text())
    require(manifest['name'] == cursor['name'] == 'pstack', 'plugin identity')
    require(manifest['skills'] == './skills/', 'Codex skill root')
    expected = {p.parent.name for p in (source / 'skills').glob('*/SKILL.md')}
    actual = {p.parent.name for p in (plugin / 'skills').glob('*/SKILL.md')}
    require(expected == actual, 'upstream skill inventory changed')
    adaptations = json.loads((source / 'codex/patches.json').read_text())
    resources = {}
    for folder in ('skills', 'agents', 'assets', 'docs', 'automations', '.codex-plugin'):
        for original in (source / folder).rglob('*'):
            if original.is_file() and not {'node_modules', '__pycache__'}.intersection(original.parts):
                resources[original.relative_to(source).as_posix()] = original.read_bytes()
    resources.update({
        'codex/runtime.md': (source / 'codex/runtime.md').read_bytes(),
        'README.md': (source / 'codex/README.md').read_bytes(),
        'LICENSE': (source / 'LICENSE').read_bytes(),
    })
    automatic = []
    for relative, original in list(resources.items()):
        path = plugin / relative
        adapted = original
        if relative in adaptations['scripts']:
            text = original.decode()
            for patch in adaptations['scripts'][relative]:
                text = text.replace(patch['old'], patch['new'])
            adapted = text.encode()
        if relative in adaptations['overrides']:
            adapted = (source / 'codex/overrides' / relative).read_bytes()
        if path.name == 'SKILL.md' and path.parent.parent == plugin / 'skills':
            description, _, original_body = builder.frontmatter(adapted.decode())
            _, explicit, _ = builder.frontmatter(original.decode())
            packaged = path.read_text()
            actual_description, _, body = builder.frontmatter(packaged)
            require(description.strip() and actual_description == description,
                    f'{relative}: description drift')
            header = (f'---\nname: {path.parent.name}\n'
                      f'description: {json.dumps(description, ensure_ascii=False)}\n---\n\n')
            require(packaged.startswith(header), f'{relative}: invalid Codex metadata')
            runtime = os.path.relpath(plugin / 'codex/runtime.md', path.parent)
            pointer = (f'Read [the Codex runtime adapter]({runtime}) before executing this skill. '
                       'It governs host operations; the upstream workflow still owns task requirements.\n\n')
            require(body == pointer + original_body, f'{relative}: workflow body drift')
            policy = path.parent / 'agents/openai.yaml'
            policy_text = 'policy:\n  allow_implicit_invocation: ' + str(not explicit).lower() + '\n'
            require(policy.read_text() == policy_text, f'{relative}: invocation policy drift')
            resources[policy.relative_to(plugin).as_posix()] = policy_text.encode()
            resources[relative] = (header + pointer + original_body).encode()
            if not explicit:
                automatic.append(path.parent.name)
        elif relative.startswith('agents/') and path.suffix == '.md':
            _, head, body = original.decode().split('---', 2)
            pointer = ('Read [the Codex runtime adapter](../codex/runtime.md) before this brief. '
                       'It governs host operations.\n')
            resources[relative] = ('---' + head + '---\n\n' + pointer + body).encode()
        else:
            resources[relative] = adapted
    require(automatic == ['setup-pstack'], 'automatic entrypoints changed')
    markdown = list(plugin.rglob('*.md'))
    for path in markdown:
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', path.read_text()):
            if '://' in target or target.startswith('#') or target == 'url':
                continue
            resource = (path.parent / target.split('#', 1)[0]).resolve()
            require(resource.is_relative_to(plugin.resolve()), f'escaping reference: {path}: {target}')
            require(resource.exists(), f'broken reference: {path}: {target}')
    actual_resources = snapshot(plugin)
    require(set(actual_resources) == set(resources),
            f'package inventory drift: missing {sorted(set(resources) - set(actual_resources))}; '
            f'extra {sorted(set(actual_resources) - set(resources))}')
    for relative, expected_bytes in resources.items():
        require((plugin / relative).read_bytes() == expected_bytes, f'resource content drift: {relative}')
    return len(actual), len(markdown), len(automatic)


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
        env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ['PATH'])
        result = subprocess.run(['bash', str(plugin / 'skills/poteto-mode/scripts/worktree-audit.sh'),
                                 '-b', 'HEAD', str(repo)], env=env, text=True, capture_output=True, check=True)
        require('verify-chat-usage' in result.stdout, 'unknown chat usage must not be safe to prune')
        require('\tsafe\t' not in result.stdout, 'missing history cannot establish safe cleanup')


def main():
    source_before = snapshot(builder.SOURCE)
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
    require(source_before == snapshot(builder.SOURCE), 'build modified original source resources')
    print(f'PASS: {counts[0]} skills, {counts[1]} Markdown resources, '
          f'{counts[0] - counts[2]} explicit / {counts[2]} automatic; '
          'resource inventory, links, relocation, deterministic build, failure detection, '
          'history-unknown audit, upstream plan checks, and original source preservation.')


if __name__ == '__main__':
    main()
