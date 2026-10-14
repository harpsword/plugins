---
name: poteto-help
description: Guide users through pstack setup, poteto-mode, and choosing a skill, playbook, or principle in Codex.
---

# Poteto help

Answer the user's question and give one usable prompt. Help requests do not start an implementation run. If the user asks for work, read the corresponding skill and proceed within that scope.

Read the installed package's codex/runtime.md and the relevant skill before explaining its behavior. Link the actual local Codex-adapted file; the upstream public Cursor copy is not the adapted version. Package README.md describes installation and scope.

## Start

1. Install the built Codex package through its marketplace as described in README.md.
2. Invoke `$pstack:setup-pstack` to choose supported model roles, reasoning budget, and panel sizes. A missing config inherits the session's model; no claim of model-family diversity is made.
3. Invoke `$pstack:poteto-mode` with a goal and a check that can pass or fail. It routes to the original playbooks and reads the other skills itself. Only setup-pstack allows automatic discovery; the other 53 skills are explicit entrypoints and internal path references.

Codex does not need a Cursor Custom Mode. Invoke the mode for each new task, and have delegates read its absolute path. For a plan-only request, use the multi-phase-plan playbook without implementing it. For long work distinguish current-session continuation from a user-requested future heartbeat, using the runtime guide. Never promise that an ordinary conversation keeps running after the host stops it.

## Pick a skill

| The user wants to | Skill |
|---|---|
| Do any non-trivial task with rigor | [`/poteto-mode`](../poteto-mode/SKILL.md) |
| Check that the agent understood their goal and the problem before it starts | [`/in-your-own-words`](../in-your-own-words/SKILL.md) |
| Aim a task higher before starting: more expert, more outcome-focused, not overspecified | [`/sharpen`](../sharpen/SKILL.md) |
| Know how code works now, or where new code should live | [`/how`](../how/SKILL.md) |
| Know why code is shaped this way, or where a number came from | [`/why`](../why/SKILL.md) |
| Understand a change or subsystem, explained plainly | [`/teach`](../teach/SKILL.md) |
| Catch up on their own recent work on a topic | [`/recall`](../recall/SKILL.md) |
| Catch up on what changed in this chat since their last message, in a few plain sentences and small visuals, with enough context to decide each action item | [`/ketchup`](../ketchup/SKILL.md) |
| Know what a small diff could break outside itself | [`/blast-radius`](../blast-radius/SKILL.md) |
| Settle types and module shape before code that crosses a function boundary | [`/architect`](../architect/SKILL.md) |
| Get several attempts at one brief, merged into the best one | [`/arena`](../arena/SKILL.md) |
| Run parallel checks over slices, or race workers, as cloud agents | [`/swarm`](../swarm/SKILL.md) |
| Have different models review a diff and try to break it | [`/interrogate`](../interrogate/SKILL.md) |
| Fix a bug test-first when a cheap local test exists | [`/tdd`](../tdd/SKILL.md) |
| Apply TypeScript rules to `.ts` or `.tsx` work | [`/typescript-best-practices`](../typescript-best-practices/SKILL.md) |
| Strip comments before review, using a reviewer that didn't write them | [`/no-comments`](../no-comments/SKILL.md) |
| Clean AI tells out of prose | [`/unslop`](../unslop/SKILL.md) |
| Write docs, an RFC, a README, a PR description, or a commit message to a standard | [`/technical-writing`](../technical-writing/SKILL.md) |
| Hear the last reply again in plain words | [`/bro`](../bro/SKILL.md) |
| Give agents a scripted way to drive the app and prove behavior | [`/create-verification-skill`](../create-verification-skill/SKILL.md) |
| Bring a verification skill and its feature map back in line with the app | [`/maintain-verification-skill`](../maintain-verification-skill/SKILL.md) |
| Vet a performance number before reporting or acting on it | [`/benchmark-checklist`](../benchmark-checklist/SKILL.md) |
| Run a large or cross-cutting change, or one to review after stepping away | [`/figure-it-out`](../figure-it-out/SKILL.md) |
| Keep a decision log during a run, and review it afterward | [`/show-me-your-work`](../show-me-your-work/SKILL.md) |
| Pick a model for each role and a reasoning budget | [`/setup-pstack`](../setup-pstack/SKILL.md) |
| Turn their own working habits into a personal mode skill | [`/automate-me`](../automate-me/SKILL.md) |
| Turn what a finished task taught into skill edits | [`/reflect`](../reflect/SKILL.md) |
| Stop agents from repeating the same mistakes in this repo | [`/correct`](../correct/SKILL.md) |
| Build a page whose buttons wake a Grok Bot over a webhook | [`/make-bot-ui`](../make-bot-ui/SKILL.md) |
| Find their way around pstack | `/poteto-help` |


Read a skill's body before recommending it. Principles live in sibling principle-* folders and guide decisions; poteto-mode reads them on demand. Playbooks live under poteto-mode/playbooks and are not separate skill commands.

## Common distinctions

- how explains mechanics, why investigates rationale, and teach integrates them for the reader.
- arena compares candidate artifacts and synthesizes one; swarm covers slices or races and returns one report.
- interrogate reviews the diff; blast-radius tests effects outside it. Reviews preserve independent seats even without different model families.
- recall reconstructs recent work across scoped chats; ketchup covers this chat since the user's last message. session-pickup resumes one named prior task.
- figure-it-out designs a bespoke run; orchestrate coordinates a program; autonomous-run pursues one exit predicate.
- no-comments uses the bundled comment-sicko brief. Model settings, child-agent types, and tool names come from Codex, not the source platform.

## Missing capabilities

Use the runtime dependency mappings for deslop, control-cli, control-ui, and skill-creator. A missing live surface, independent reviewer, external history, webhook provisioning, or scheduler is an explicit limitation; do not claim its gate passed. Use available evidence and finish independent work.

When a run drifts, state the affected gate and the concrete correction. Model changes take effect when the next skill reads pstack-models.json. If a skill is not automatically selected, explain its explicit policy instead of changing it. To personalize the mode use automate-me; to review lessons use reflect, preserving its approval gate.

Give at most one tailored example prompt, then a link to the file supporting the answer.
