#!/usr/bin/env python3
"""Derive a full Codex package while preserving the original Cursor source."""

import json
import os
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'pstack'
DESTINATION = ROOT / 'dist/pstack-codex'


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


def adapt_text(text, names):
    replacements = {
        'pstack/skills/': '<installed-package>/skills/',
        '~/.cursor/rules/pstack-models.mdc': '.codex/pstack-models.json',
        'pstack-models.mdc': 'pstack-models.json',
        '~/.cursor/skills/': '~/.agents/skills/',
        '.cursor/skills/': '.agents/skills/',
        '~/.cursor/plugins/': '${CODEX_HOME:-~/.codex}/plugins/cache/',
        '.cursor/worktrees/': '.codex/worktrees/',
        "Cursor's built-in `create-skill`": 'the available `skill-creator`',
        "Cursor's built-in for authoring SKILL.md files": 'the host authoring capability described in the runtime guide',
        'create-skill': 'skill-creator',
        "Cursor's `/loop` command": 'the runtime continuation procedure',
        "(a built-in, not a pstack skill)": '(not a slash command)',
        '/loop 1h': 'heartbeat 1h',
        '/loop': 'run-until-done',
        'Cursor cloud agent': 'isolated Codex worker',
        'Cursor restart': 'Codex restart',
        'the cloud agent\'s status in the Cursor dashboard': 'the actual worker status from host tools',
        'a isolated Codex worker': 'an isolated Codex worker',
        'run-until-done until': 'run until',
        'cloud workers': 'isolated workers',
        'cloud agents': 'isolated workers',
        'cloud agent': 'isolated worker',
        'cloud concurrency limit': 'host concurrency limit',
        'own cloud VM': 'own isolated worktree and runtime instance',
        'AskQuestion': 'host question tool',
        'subagent_type: "poteto-agent"': 'the poteto-agent prompt brief',
        'subagent_type: "comment-sicko"': 'the comment-sicko prompt brief',
        'subagent_type: generalPurpose': 'a supported generic delegate type',
        'run_in_background: true': 'background delegation when supported',
        'readonly: true': 'an explicit no-write contract',
        'readonly: false': 'available tool access within the assigned scope',
        'grok-4.7-xhigh-fast': 'inherit-parent',
        'claude-opus-5-5-xhigh': 'inherit-parent',
        '(readonly strips MCP)': '(read-only is a no-write contract)',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r'\bTask\b', 'delegate', text)
    # Only invocation tokens, never directory paths or URLs.
    pattern = r'(?<![\w/.:])/(%s)(?![\w/-])' % '|'.join(map(re.escape, sorted(names, key=len, reverse=True)))
    return re.sub(pattern, lambda m: '$pstack:' + m[1], text)


def build(destination=DESTINATION):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    names = {p.parent.name for p in (SOURCE / 'skills').glob('*/SKILL.md')}
    patches = json.loads((SOURCE / 'codex/patches.json').read_text())
    applied = set()
    for name in ('skills', 'agents', 'assets', '.codex-plugin'):
        target = destination / name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(SOURCE / name, target, ignore=shutil.ignore_patterns('node_modules', '__pycache__'))
    runtime_dir = destination / 'codex'
    if runtime_dir.exists():
        shutil.rmtree(runtime_dir)
    runtime_dir.mkdir()
    shutil.copy2(SOURCE / 'codex/runtime.md', runtime_dir / 'runtime.md')
    shutil.copy2(SOURCE / 'LICENSE', destination / 'LICENSE')
    shutil.copy2(SOURCE / 'codex/README.md', destination / 'README.md')
    if (destination / 'docs').exists():
        shutil.rmtree(destination / 'docs')
    for path in sorted(destination.rglob('*')):
        if not path.is_file() or path.suffix not in ('.md', '.sh', '.mjs', '.ts'):
            continue
        relative = path.relative_to(destination).as_posix()
        if relative.startswith('codex/') or relative == 'README.md':
            continue
        text = path.read_text()
        for patch in patches.get(relative, []):
            if text.count(patch['old']) != 1:
                raise ValueError(f'Upstream adapter anchor changed: {relative}: {patch["old"][:80]}')
            text = text.replace(patch['old'], patch['new'])
            applied.add(relative)
        override = SOURCE / 'codex/overrides' / relative
        if override.exists():
            text = override.read_text()
        if path.suffix == '.md':
            text = adapt_text(text, names)
        elif relative.endswith(('check-plan.mjs', 'check-plan.test.ts')):
            text = text.replace('/loop 1h', 'heartbeat 1h').replace('git show origin/main:', 'installed package')
        if path.name == 'SKILL.md':
            original = (SOURCE / relative).read_text()
            _, explicit, _ = frontmatter(original)
            description, _, body = frontmatter(text)
            runtime = os.path.relpath(runtime_dir / 'runtime.md', path.parent)
            pointer = f'Read [the Codex runtime adapter]({runtime}) before executing this skill. It supplies model selection, delegation, history, continuation, and dependency handling.\n\n'
            text = f'---\nname: {path.parent.name}\ndescription: {json.dumps(description, ensure_ascii=False)}\n---\n\n' + pointer + body
            policy = path.parent / 'agents/openai.yaml'
            policy.parent.mkdir(exist_ok=True)
            policy.write_text('policy:\n  allow_implicit_invocation: ' + str(not explicit).lower() + '\n')
        elif relative.startswith('agents/'):
            # Agent briefs are read explicitly by supported Codex delegate types.
            _, head, body = text.split('---', 2)
            text = '---' + head + '---\n\nRead [the Codex runtime adapter](../codex/runtime.md) before this brief.\n' + body
        path.write_text(text)
    if set(patches) != applied:
        raise ValueError(f'Unapplied patches: {set(patches) - applied}')
    # Portable manifests auto-discover root skills and take precedence over this overlay.
    for name in ('plugin.json', '.cursor-plugin', '.claude-plugin'):
        target = destination / name
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
    return destination


if __name__ == '__main__':
    print(build())
