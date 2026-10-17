# pstack on Codex

Read this guide before executing any bundled skill or delegate brief. It defines the host operations used by the preserved pstack workflows. Follow the user's scope, repository instructions, and host permissions throughout.

## Invocation and resources

The original invocation policy is preserved: only setup-pstack allows implicit selection. The other 53 skills require explicit user invocation or a path reference from an active workflow. Once poteto-mode is invoked, resolve named skills to `skills/<name>/SKILL.md` inside this installed package and read them when their triggers apply. A missing catalog entry is not a missing file. Use `$pstack:<name>` for user prompts. Plain references such as `how`, `architect`, or `no-comments` mean read the corresponding bundled file, not ask the user to invoke it.

Paths in a skill resolve relative to that skill directory unless specified otherwise. The package root contains `.codex-plugin/plugin.json`, this guide at `codex/runtime.md`, `skills/`, and `agents/`. Playbook references beginning `playbooks/` or `scripts/` resolve from `skills/poteto-mode/`, not the playbook's containing folder. Give delegates absolute paths. Never search plugin caches and choose a version by lexical order.

## Models

Read project `.codex/pstack-models.json` if present; otherwise read `${CODEX_HOME:-~/.codex}/pstack-models.json`. The project file is a complete override, not a merge. Setup documents the schema. Missing roles inherit their host model. Panel defaults are two inherited-model seats for arena runners, architect runners, and interrogate reviewers. Arena cross-judge pool defaults to one inherited seat. Reflect still has three lenses and a separate synthesizer. Preserve seat counts and independent perspectives even when model diversity is unavailable.

`auto` and `inherit-parent` mean omit model and reasoning overrides. Explicit entries separate `model` and optional `reasoning_effort`; never concatenate effort or speed into a provider slug. Validate against the current tool's supported choices. Pass explicit overrides only when the user/configuration and host permit them. For tools that require fresh context to override a model, provide a self-contained brief and the supported fresh-context option. If a configured model is unavailable, disclose it and inherit unless the user requires diversity; in that case report the missing capability. Do not substitute an unexposed model or claim independent same-model seats are different model families. An explicit role reasoning_effort takes precedence over the global budget and generic difficulty advice. Preserve it unless the user changes that role. Budget labels supply the starting effort only for an explicit model with no effort: unlimited=max, large=xhigh, medium=high, small=medium. Use only supported levels; disclose any required adjustment. Aliases inherit both model and effort, regardless of budget.

## Delegation

Use the session's actual subagent APIs and schemas. In this desktop host those may be `spawn_agent`, `send_message`, `followup_task`, `wait_agent`, and `interrupt_agent`; other Codex hosts may expose different names. Workflow phrases like delegate call, background execution, or read-only describe intent, not literal API fields. Read-only means explicitly prohibit file edits and external mutations while allowing available read tools. Do not assume readonly removes MCP access.

For `poteto-agent`, pass the installed `agents/poteto-agent.md` and mode paths; for `comment-sicko`, pass `agents/comment-sicko.md`. These are prompt briefs, not automatically registered agent types. Use a supported generic/explorer/worker type and require reading the appropriate brief. Preserve every scoped review rule in those files.

Respect actual concurrency and nesting limits. Queue required workers rather than dropping coverage. Every writer gets owned files or a separate worktree, knows it shares the checkout unless isolated, preserves others' changes, and reports actual artifacts and checks. For races, give each candidate separate output at the specified base. Never assume a cloud VM, durable agent, or shared remote filesystem exists. Do not create user-owned chats just to implement fan-out. If delegation is prohibited or unavailable, do safe local investigation/implementation and label any unfulfilled independent-review or parallel-experiment gate. Never ship under a false independent PASS.

## Blind delegation

For Arena candidates, Eval candidates, and their blind judges, always start a new agent with `fork_turns="none"` or the host's equivalent empty conversation context, including when the model is `auto`, `inherit-parent`, or omitted. Model inheritance never authorizes conversation inheritance. Do not reuse an agent that has already seen coordinator-only information.

Prepare a complete, role-scoped brief before spawning. Candidates receive only the organic task, necessary project constraints and grounding, their own workspace/output paths, and requested deliverables. Keep the coordinator's rubric, experimental purpose, other candidates, and model/variant mapping out of their prompts and referenced resources. Eval additionally requires sanitized names throughout candidate-visible paths and content. Judges receive the task context needed to assess the result, the rubric, and completed outputs under neutral labels; keep model/variant identities and the coordinator's preferred result private. Do not send candidates or judges the coordinator's Arena/Eval instructions or this guide merely to explain their role. Inspect supplied files and paths for information leakage as well as the prompt.

If the host cannot provide fresh context, report the blind run as blocked. If a participant has already received disallowed information, discard that participant's blind result and restart with a clean brief and context; asking it to ignore the information does not restore blinding.

## History

For the active conversation, use visible messages and actual tool outputs. For a user-requested prior chat or project recall, use available `list_threads` / `read_thread` tools, restrict to the requested project/topic/time before fetching detailed content, and cite the real IDs. If the listing is incomplete, disclose the coverage gap rather than claiming exhaustive search. Read-only retrieval does not authorize messaging those chats.

A user-provided transcript/export or a host-provided exact transcript path is also valid. Do not glob all user sessions or derive Cursor-style transcript paths. Inspect the actual format before parsing. A summary or local digest is not a complete tool trace. For eval chain-following, missing actual read/tool evidence is INCONCLUSIVE; behavior tests may still pass. For reflection or personalization, a current-chat digest can support provisional findings, with the limitation disclosed. For worktree cleanup, no transcript evidence means usage is unknown, not safe to delete. `PSTACK_TRANSCRIPTS_DIR` may name an explicitly scoped export for the audit script, never an entire history directory.

## Continuation

A run-until-done request has a falsifiable exit predicate. Keep finite work in the current turn, wait on actual processes/workers, and recheck evidence after each event. The source workflow's loop or heartbeat notation is not a Codex slash command. An hourly heartbeat means use the available automation API only when the user asked for recurring monitoring or future continuation. Inspect existing matching automations first; save the task scope, predicate, cadence, and stop condition, stay quiet when unchanged, and retire the schedule on completion. No durable scheduler means no promise of unattended wakeups. Do not implement unsupported scheduling with cron, polling scripts, or new chats.

After restart, inspect real worker/process state and recover from persisted artifacts. Background execution does not imply survival across sessions. Preserve watcher verdicts and shipping gates in the playbooks. Keep an actual long-running watcher as a process if supported; bounded polls keep the user informed. Avoid a second competing watcher.

## External dependencies and delivery

Use the host's shell/PTY for CLI checks and connected browser/computer tools for UI checks. If a project verify skill exists, prefer it. The source names `control-cli` and `control-ui` as capability roles; use installed equivalents or the actual tools, without pretending a missing plugin is installed. A missing surface remains an unpassed live-verification gate.

For the diff cleanup procedure, use an installed equivalent of `deslop` or inspect the diff for speculative guards, casts, redundant abstractions, dead code, and filler comments, following the bundled review rubric. For `skill-creator`, use the installed authoring skill or author a SKILL.md with valid name/description, preserved explicit-invocation policy in agents/openai.yaml, focused instructions and references, and a realistic verification pass. Do not edit installed plugin cache as the durable source; edit the source package and rebuild/reinstall.

Use the current host's question and planning tools only when their schemas and active mode support the operation; otherwise ask in chat and maintain a checklist. Do not invent option counts or multi-select fields. Source references to Read, Grep, Glob, and Shell describe file-reading, search, and command capabilities; map them to actual tools such as shell reads and rg, not literal unsupported API names. Explicit-only skills stay explicit-only during reflection and personalization; fix missed routing in the active workflow rather than widening invocation policy. Plan-only requests remain plan-only. Skills' commit/PR/merge steps apply within the delivery scope the user granted. Read applicable commit rules first. Preserve user edits and permission gates; do not reset dirty worktrees, auto-message people, or publish just because a playbook mentions it. Connected sources in why/recall require available credentials and tool access; report unavailable sources.

A bot webhook belongs to its provider. make-bot-ui can connect an existing authorized webhook; Codex scheduling is not a webhook receiver. Report provider provisioning and secret-entry blockers precisely while completing local UI/server work with a mock.

## Durable run directory

Resolve `<installed-package>` to the absolute root containing this runtime guide. Never expect pstack source files in the consumer repository or load Cursor sources from its trunk. Record this package version and paths for later continuation.

Use an explicit host-provided writable artifact directory if available; otherwise use `<project-root>/.pstack/runs/<unique-run-id>/`. Create only the directory for the current run. Keep plans in `docs/` beneath it. Pass its absolute path to every worker and bind orchestration commands with `--store` or `ORCH_STORE`. Do not assume the system prompt includes an agent store. Keep these local operational records out of commits unless the user asks to include them.


Before running the bundled Bun entrypoints, set `PSTACK_TOOLS_DIR` to an absolute writable directory dedicated to this run, outside the installed package. Alternatively, set `PSTACK_RUN_DIR` to the durable run directory and tools use its `tools/` subdirectory. The bootstrap copies the complete script bundle into a content-addressed child directory, installs its locked dependencies there, and relaunches the same entrypoint with the original arguments and working directory. It never installs into the plugin cache. Keep `ORCH_STORE` or `--store` bound separately to the durable run directory. A missing Bun runtime, unavailable dependency download, or unwritable tools directory is a setup blocker, not a successful watcher or verifier. Preserve the tools directory while its processes are running.
