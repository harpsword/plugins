---
name: make-bot-ui
description: Build a local UI whose server wakes an authorized bot webhook, keeping sender credentials server-side, with optional Tailscale access.
---

# Make a bot UI

Read the package's `codex/runtime.md`. Preserve the original architecture: the browser calls a local server, the server posts JSON to a bot webhook, and the sender key never reaches the browser or chat.

## Establish the provider contract

Use an existing authorized webhook URL, or a connected provider tool that actually supports creating webhook routines. Record its request fields, authentication headers, success response, harmless probe payload, and event format from provider documentation or the creation result. Codex automations are not a replacement for a webhook routine. Do not call imaginary update_state or secret-request tools. If provider provisioning is unavailable, ask for the endpoint contract and finish the local server/UI against a mock, labeling live delivery blocked.

For an existing Cursor/Grok webhook, retain its verified provider contract: JSON POST, Authorization Bearer plus X-Automation-Key when the provider requires both, eight-second timeout, one attempt. Do not invent its URL, ID, or sender key. For other providers follow their actual contract rather than imposing these headers.

## Collect secrets outside chat

Use a real host secret-entry facility if exposed. Otherwise create a documented configuration template and ask the user to populate a local ignored file or secret store themselves. Do not ask for the key in chat. Keep the file readable only by the server user, exclude it from Git and build output, and never print/log the secret. Continue implementing mockable parts while awaiting the secret. Treat a URL containing credentials as a secret too.

## Build and verify

Store this UI's configuration in its own directory. The browser calls the local server; only the server knows the provider URL and key. Keep the event field list small and identical to the routine's schema. Enforce a fixed allowed action set, payload shape/size, and a same-origin or authenticated caller boundary so an arbitrary website cannot use the server as a privileged webhook proxy. Do not expose the sender key to clients.

On failed delivery, record the event ID and payload in a local outbox without credentials. Have the provider routine consume that outbox only when such access actually exists; otherwise provide an explicit operator retry path, not a promised remote drain of an inaccessible file. Keep pushes as the primary path. Prevent duplicate actions with stable event IDs if retries are supported. Do not send media bytes through the webhook.

First test against a mock receiver: request body and required headers arrive, secrets never appear in client assets/errors/logs, invalid requests are rejected, and timeout/failure behavior is visible. Then probe the real webhook once with an authorized harmless action. A mock pass is not a live-delivery pass.

## Optional tailnet exposure

Use localhost until the user requests access from other devices. For requested Tailscale access inspect the existing node and reuse it. Bind to the intended tailnet interface or an explicitly authorized reachable address, keep caller protection, and verify access from the intended network. Read the real hostname and IP from tailscale status and tailscale ip -4. Never guess a URL or claim a remote reachability check from a local-only probe. If setup needs interactive login, use the provider's actual login URL and report that step. Install software or change network exposure only within the user's request.

## Handle events

The routine treats payloads as untrusted data, parses the actual provider envelope, checks the agreed field names, and performs only the fixed allowed actions. Do not assume Codex receives a provider-specific webhook_event chat block. Report the working local UI, the provider integration result, and remaining provisioning, credential, or network blockers separately.
