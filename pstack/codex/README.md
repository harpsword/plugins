# pstack for Codex

All 54 upstream skills are included. The original Cursor package remains unchanged. The Codex build preserves the author's playbooks, principles, review lenses, prompts, and scripts, with host-specific patches and three replacements for setup, help, and bot webhook integration.

## Install and use

From the source repository root:

```bash
python3 scripts/build-pstack-codex.py
codex plugin marketplace add .
codex plugin add pstack@local-plugins
```

The marketplace points at `dist/pstack-codex`. Distribute that entire directory. Rebuild and reinstall after source changes. Start a new chat after installation.

Use `$pstack:setup-pstack` for model roles and budget, then `$pstack:poteto-mode` plus a goal and a verifiable result. Use `$pstack:poteto-help` for the skill map. Only setup-pstack allows automatic selection; the other 53 are explicit entrypoints. Once a workflow is active it reads and uses the other skills by path, without requiring separate user invocations.

The runtime adapter at `codex/runtime.md` defines delegation, model roles, scoped history, continuation, and tool dependencies. `setup-pstack` writes project `.codex/pstack-models.json` by default, or the personal file under the effective Codex home when requested. It does not change the host's model configuration. Inherited-model panel seats remain independent but are not presented as different model families.

For project-only activation, set `[plugins."pstack@local-plugins"] enabled = false` in the user config and `enabled = true` in the trusted project's `.codex/config.toml`. Keep these entries in valid TOML table form on separate lines. Installation and activation are separate.

## Capabilities and limits

All workflows are available, but their live gates still depend on the host. Multi-model execution needs exposed model overrides. Independent review needs subagents. UI verification needs a connected control surface. Recall and reflection use scoped chat tools or a verified transcript, not guessed filesystem paths. A missing full tool trace makes eval chain-following inconclusive. Recurring work needs a user-authorized scheduler. Bot UI connects a real provider webhook; it does not turn a Codex schedule into one. These limitations are reported at the affected step rather than silently skipping it.

The bundled tools need their usual runtimes: shell/Python/Node for local checks, Bun for the PR watcher and orchestration ledger, and authenticated gh or Origin for live forge work. External services and credential-dependent flows are not exercised by package validation.

## Maintain and validate

The build reads canonical `pstack/skills` and `pstack/agents`, applies exact checked anchors from `pstack/codex/patches.json`, performs the host vocabulary mapping, and overlays `pstack/codex/overrides`. An upstream anchor change fails the build instead of silently dropping an adaptation. It translates invocation flags to `agents/openai.yaml`, normalizes skill names, and adds a runtime pointer to every skill and delegate brief.

```bash
python3 scripts/validate-pstack-codex.py
```

Validation checks all skill identities and policies, resource inventories, local Markdown links, relocatability, deterministic rebuilding, unchanged upstream files, and host-specific script behavior. Build output is ignored by Git. Never make a durable fix only in dist/ or the installed cache.
