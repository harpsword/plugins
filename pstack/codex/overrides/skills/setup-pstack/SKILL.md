---
name: setup-pstack
description: Configure pstack's Codex model roles and reasoning budget, or check available delegation and verification capabilities.
---

# Setup pstack

Read the package's `codex/runtime.md`. Preserve the author's configurable role assignments, panel sizes, and budget choices using Codex-supported models.

1. Detect the model identifiers and reasoning levels exposed for delegates in this session. Do not guess identifiers from marketing names or concatenate effort suffixes. If no overrides are exposed, inheritance remains available; explain the limitation.
2. Read project `.codex/pstack-models.json`, otherwise the personal `pstack-models.json` under the effective Codex home. Preserve existing choices and scope. For a new configuration default to the project file; use personal scope only when requested. Never modify config.toml to store pstack-specific fields.
3. Ask for the budget if not already specified: unlimited (max), large (xhigh), medium (high), or small (medium). Show supported adjustments. Aliases inherit both model and effort. The budget is an effort preference, not a monetary cap.
4. Show every role below, its effective model and effort, and every panel seat. Let the user accept or change them. Preserve explicit configured choices on rerun. Prefer distinct supported model families for review/judgment when the user selects them; otherwise retain two independent inherited-model seats and explain they are not model-diverse. If the session exposes no models, do not force guessed model choices.
5. Validate real identifiers and reasoning levels against the session, then write the chosen file atomically using a temporary file in the same directory. Keep the schema version, budget, and roles. Report unknown/retired roles before removing them. Use JSON parsing to check the result. Re-running the same setup is idempotent.
6. Report the path and effective choices. The next skill reads the file directly; no always-applied Cursor rule is needed. Offer create-verification-skill once if this project lacks a real-app harness, without creating it unless requested.

Configuration shape below uses inheritance for portable defaults. An explicit seat is an object such as `{"model":"<verified-id>","reasoning_effort":"high"}`; omit unsupported optional effort. Scalar roles accept one alias/object; panel roles accept a nonempty list. The cross-judge pool is a list from which Arena selects one seat. Repeated aliases still count as separate panel seats.

```json
{
  "version": 1,
  "budget": "large",
  "roles": {
    "feature, refactoring": "inherit-parent",
    "bug-fix": "inherit-parent",
    "perf-issue": "inherit-parent",
    "hillclimb": "inherit-parent",
    "judgment and prose": "inherit-parent",
    "hardest tasks": "inherit-parent",
    "how explorer": "inherit-parent",
    "how explainer": "inherit-parent",
    "why investigators": "inherit-parent",
    "why synthesizer": "inherit-parent",
    "reflect tooling": "inherit-parent",
    "reflect judgment, divergent, synthesizer": "inherit-parent",
    "arena runners": ["inherit-parent", "inherit-parent"],
    "arena cross-judge pool": ["inherit-parent"],
    "swarm workers": "inherit-parent",
    "architect runners": ["inherit-parent", "inherit-parent"],
    "interrogate reviewers": ["inherit-parent", "inherit-parent"]
  }
}
```

A malformed existing file is a configuration error: report the offending field and repair only within the user's setup request. Do not silently fall back and overwrite it.
