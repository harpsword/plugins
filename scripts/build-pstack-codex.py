#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'pstack'
DESTINATION = ROOT / 'dist/pstack-codex'
RESOURCE_DIRS = ('skills', 'agents', 'assets', 'docs', 'automations', '.codex-plugin')


def frontmatter(text):
    _, head, body = text.split('---', 2)
    match = re.search(r'^description: (.*)(?:\n|$)', head, re.M)
    description = match[1]
    if description in ('>-', '>', '|', '|-'):
        rest = head[match.end():]
        description = ' '.join(line.strip() for line in rest.splitlines()
                               if line.startswith('  '))
    elif description.startswith('"'):
        description = json.loads(description)
    explicit = bool(re.search(r'^disable-model-invocation: true$', head, re.M))
    return description, explicit, body.lstrip('\n')


def adapted_files():
    manifest = json.loads((SOURCE / 'codex/patches.json').read_text())
    overrides = SOURCE / 'codex/overrides'
    expected = set(manifest['overrides'])
    actual = {p.relative_to(overrides).as_posix() for p in overrides.rglob('*') if p.is_file()}
    if actual != expected:
        raise ValueError(f'Override inventory changed: {actual ^ expected}')
    files = {}
    for relative, reviewed_hash in manifest['overrides'].items():
        original = SOURCE / relative
        if hashlib.sha256(original.read_bytes()).hexdigest() != reviewed_hash:
            raise ValueError(f'Upstream override source changed: {relative}; '
                             f'compare it with codex/overrides/{relative} before updating its reviewed hash')
        files[relative] = (overrides / relative).read_text()
    for relative, patches in manifest['scripts'].items():
        if Path(relative).suffix == '.md' or relative in files:
            raise ValueError(f'Only non-overridden executable resources may be patched: {relative}')
        text = (SOURCE / relative).read_text()
        for patch in patches:
            if not patch['old'] or text.count(patch['old']) != 1:
                raise ValueError(f'Upstream adapter anchor changed: {relative}: {patch["old"][:80]}')
            text = text.replace(patch['old'], patch['new'])
        files[relative] = text
    return files


def build(destination=DESTINATION):
    replacements = adapted_files()
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for name in (*RESOURCE_DIRS, 'codex'):
        target = destination / name
        if target.exists():
            shutil.rmtree(target)
        if name != 'codex':
            shutil.copytree(SOURCE / name, target, ignore=shutil.ignore_patterns('node_modules', '__pycache__'))
    runtime_dir = destination / 'codex'
    runtime_dir.mkdir()
    shutil.copy2(SOURCE / 'codex/runtime.md', runtime_dir / 'runtime.md')
    shutil.copy2(SOURCE / 'LICENSE', destination / 'LICENSE')
    shutil.copy2(SOURCE / 'codex/README.md', destination / 'README.md')
    for relative, text in replacements.items():
        (destination / relative).write_text(text)
    for path in (destination / 'skills').glob('*/SKILL.md'):
        relative = path.relative_to(destination)
        _, explicit, _ = frontmatter((SOURCE / relative).read_text())
        description, _, body = frontmatter(path.read_text())
        runtime = os.path.relpath(runtime_dir / 'runtime.md', path.parent)
        pointer = (f'Read [the Codex runtime adapter]({runtime}) before executing this skill. '
                   'It governs host operations; the upstream workflow still owns task requirements.\n\n')
        path.write_text(f'---\nname: {path.parent.name}\ndescription: {json.dumps(description, ensure_ascii=False)}\n---\n\n' + pointer + body)
        policy = path.parent / 'agents/openai.yaml'
        policy.parent.mkdir(exist_ok=True)
        policy.write_text('policy:\n  allow_implicit_invocation: ' + str(not explicit).lower() + '\n')
    for path in (destination / 'agents').rglob('*.md'):
        text = path.read_text()
        _, head, body = text.split('---', 2)
        path.write_text('---' + head + '---\n\nRead [the Codex runtime adapter](../codex/runtime.md) '
                        'before this brief. It governs host operations.\n' + body)
    for name in ('plugin.json', '.cursor-plugin', '.claude-plugin'):
        target = destination / name
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
    return destination


if __name__ == '__main__':
    print(build())
