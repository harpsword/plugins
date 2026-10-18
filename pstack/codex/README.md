# pstack for Codex

All upstream skills are included. Ordinary source Markdown bodies and reference resources retain their original wording and Cursor vocabulary. The package's `codex/runtime.md` interprets host operations while source skills own task workflows. One guarded native override supplies setup. The bot skill body and script bootstrap remain upstream copies. Paths in this README are relative to the generated package root.

## Install and use

From the source repository root:

```bash
python3 scripts/build-pstack-codex.py
codex plugin marketplace add .
codex plugin add pstack@local-plugins
```

The marketplace points at `dist/pstack-codex`. Distribute that entire directory. Rebuild and reinstall after source changes. Start a new chat after installation.

Use `$pstack:setup-pstack` for model roles and budget, then `$pstack:poteto-mode` plus a goal and a verifiable result. Use `$pstack:poteto-help` for the skill map. Only setup-pstack allows automatic selection; the other 53 are explicit entrypoints. Once a workflow is active it reads and uses the other skills by path, without requiring separate user invocations.

The runtime adapter maps source tools, paths, model defaults, history, and continuation to actual Codex capabilities. Native setup at `skills/setup-pstack/SKILL.md` owns the role configuration and schema. It writes project `.codex/pstack-models.json` by default, or the personal file under the effective Codex home when requested. It does not change the host's model configuration. Codex help uses these package documents instead of source instructions for Cursor installation or Custom Modes.

For project-only activation, set `[plugins."pstack@local-plugins"] enabled = false` in the user config and `enabled = true` in the trusted project's `.codex/config.toml`. Keep these entries in valid TOML table form on separate lines. Installation and activation are separate. The CLI can enable the plugin globally when reinstalling. After installation, restore the existing global activation preference and verify the intended project still reports enabled.

## Capabilities and limits

All workflows are available, but their live gates still depend on the host. Multi-model execution needs exposed model overrides. Independent review needs subagents. UI verification needs a connected control surface. Recall and reflection use scoped chat tools or a verified transcript, not guessed filesystem paths. A missing full tool trace makes eval chain-following inconclusive. Recurring work needs a user-authorized scheduler. Bot UI needs an existing authorized webhook endpoint and its verified contract. Runtime guidance replaces unavailable Cursor provisioning, secret cards, panels, and wake envelopes. HTTP acceptance alone does not prove bot execution. These limitations are reported at the affected step rather than silently skipping it.

Independent reviewers and verifiers start with empty conversation history and an explicit brief, regardless of whether a plan document exists. This covers Interrogate, Reflect's three lenses, independent verification and audit lanes, task judges, and decision-trail reviewers. Reflect and trail reviewers receive the scoped transcript as evidence. Synthesizers receive reviewer outputs; ordinary workers and stateful follow-ups choose context for their assignment. Arena/Eval candidates and blind judges retain their stricter information-isolation rules, including Architect's Arena runners. See [the context rules](codex/runtime.md#independent-review-and-verification).

The bundled tools need shell, Python, or Node for local checks, Bun for the PR watcher and orchestration ledger, and authenticated gh or Origin for live forge work. Before any bundled Bun consumer starts, the coordinator follows [the runtime preparation sequence](codex/runtime.md#run-artifacts-and-executable-dependencies). It creates a fresh tools directory in the run, copies the complete generated scripts directory, makes the tools root writable, and runs the copied `orch/orch.ts --help` synchronously. Only a successful exit establishes readiness. A bare dependency install does not run the bootstrap's install-key checks.

All later Bun entrypoints and bundled Bun tests use that recorded copy. Tests run with the copy as their working directory. Consumers retain their original arguments and working directories. The ledger remains separately bound through `ORCH_STORE` or `--store`. Record the package root, version, and ready tools path for resume, inspect actual process state, and reuse the copy without overwriting active tools. A failed or missing copy requires a fresh destination and successful preparation before consumers start.

The adapter does not provide automatic content-addressed staging, concurrent cold initialization, transparent relocation, or in-place tools upgrades. Ordinary Node and Bash helpers can still run from the installed package. The worktree audit does not scan transcripts and reports `verify-chat-usage` without usage evidence. Program plans retain structural checks and a status-message marker, with continuation requirements expressed in ordinary prose. Bot guidance does not promise remote access to local failure logs or event replay. External services and credential-dependent flows are not exercised by package validation.

## Maintain and validate

The build copies canonical skills, agents, assets, documentation, and reference resources. It translates invocation flags to `agents/openai.yaml`, normalizes exposed skill names, and adds a runtime pointer to every exposed skill and delegate brief. It does not rewrite ordinary prose or reject source host vocabulary. Copied automation references remain unchanged and dormant; Cursor automation deployment remains unsupported.

`pstack/codex/patches.json` declares the adaptation boundary. Its `scripts` map contains three counted edits, two for the worktree audit and one for the plan checker program marker. Upstream checker fixtures remain unchanged. Its `overrides` map guards only the canonical setup-pstack source by SHA-256 before replacing it. The bot body and bootstrap remain unchanged. A changed guarded source or missing executable anchor fails before output changes. Review upstream changes before updating a guard. Ordinary source prose changes flow through the next build without maintaining paragraph patches.

```bash
python3 scripts/validate-pstack-codex.py
# Requires Bun on PATH, or PSTACK_TEST_BUN set to its absolute executable.
python3 scripts/test-pstack-runtime.py
```

Validation checks skill identities and policies, resource inventories, local Markdown links, package relocatability, deterministic rebuilding, source preservation, adaptation guards, stale-output removal, unknown history, and executable behavior. The Bun suite exercises the generated upstream bootstrap through the documented copy and initialization sequence. It covers both real entrypoints, read-only source, warm reuse, failed initialization, original fixture tests, and preservation of arguments, working directories, and exit codes. Deterministic failure cases may stub dependency downloads. A separate real locked install and entrypoint smoke in the writable run copy verifies dependency access.

A structural plan check does not satisfy a blocked scheduling or live-verification gate. Build output is ignored by Git. Make durable fixes in the source or adapter, then rebuild.
