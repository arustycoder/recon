# Assistant System Architecture

## Goal

Define the target-state architecture for `recon` as a general-purpose, customizable AI assistant product.

This architecture is informed by the adaptive-assistant patterns summarized in `docs/450-Industry-Patterns-For-Adaptive-Assistants.md` and the evolution model in `docs/460-Adaptive-Evolution-Model.md`, especially the separation of stable profile state from learned behavior [1][2].

## Design Principles

- conversation is one surface, not the product boundary
- every durable fact must be scoped, inspectable, and deletable
- task execution must be explicit, resumable, and approval-aware
- grounded outputs are preferred over fluent but unsupported outputs
- tool use is policy-controlled
- adaptive behavior should evolve through overlays, not silent global drift [1][2]
- all channels share one runtime contract
- quality must be measurable, not assumed

## Companion Design Docs

- `docs/340-Memory-Model.md`
- `docs/350-Task-Runtime.md`
- `docs/360-Knowledge-System.md`
- `docs/370-Safety-And-Permissions.md`
- `docs/380-Evaluation-And-Quality.md`
- `docs/390-Identity-And-Collaboration.md`
- `docs/400-Channels-And-Integrations.md`
- `docs/410-Core-Data-Model.md`
- `docs/420-Request-Runtime.md`
- `docs/430-Assistant-Profiles-And-Templates.md`
- `docs/440-Tool-Model.md`
- `docs/450-Industry-Patterns-For-Adaptive-Assistants.md`
- `docs/460-Adaptive-Evolution-Model.md`

## Core Product Objects

### User And Team

Actors that own assets, invoke requests, approve actions, and receive results.

### Workspace

A scoped environment containing conversations, resources, knowledge, memories, tasks, and policy settings.

### Assistant Profile

A versioned assistant definition containing instructions, style, enabled capabilities, and policy defaults.

### Adaptive Overlay

A scoped learned behavior layer that refines the published profile without mutating it directly [2].

### Conversation

A thread of user-visible interaction. A conversation may produce direct answers or spawn tasks.

### Resource

User-provided or system-created material such as files, URLs, notes, or structured records.

### Memory

Durable context captured across conversations or tasks at a defined scope.

### Knowledge Source

Managed information prepared for retrieval, citation, and refresh.

### Task

A durable unit of assistant work that may outlive one foreground request.

### Tool

A controlled capability the assistant may invoke to read, write, fetch, transform, or act.

## Logical Services

### Client Layer

Web, desktop, mobile, API, and connector surfaces. Clients render state, collect input, and display approvals, tasks, and citations.

### Assistant Runtime

Orchestrates request handling, context assembly, retrieval, tool execution, streaming, task handoff, and final output generation.

### Knowledge Service

Owns ingestion, parsing, indexing, retrieval, source freshness, and citation metadata.

### Memory Service

Owns summary generation, memory extraction, ranking, retention, and delete/archive behavior.

### Policy Service

Evaluates permissions, tool risk rules, approval requirements, data visibility, and secret use.

### Identity Service

Resolves users, teams, roles, ownership, and sharing rules.

### Model Routing Service

Selects and invokes model providers according to profile, policy, cost, latency, and capability constraints.

### Control Plane

Manages profiles, templates, tools, source configuration, adaptive promotions, policy settings, evaluations, and operational inspection [1][2].

### Observability Plane

Captures request traces, task traces, tool calls, citations, audits, feedback, metrics, and evaluation results.

## Execution Modes

- direct answer: one foreground request produces one final response
- streamed answer: the response is emitted incrementally
- tool-assisted answer: the runtime invokes bounded tools before final output
- task handoff: the request creates a longer-running task
- approval wait: execution pauses until a required approval is granted or denied

## Deployment Modes

### Local Personal

Single-user deployment with local storage and optional local model access.

### Hosted Team

Shared deployment with managed identity, policy, evaluation, and operational control surfaces.

### Hybrid

Client-local interaction paired with remote runtime, knowledge, and policy services.

## Suggested Build Order

1. core data model, identity model, workspace model
2. assistant profiles and request runtime
3. memory and knowledge systems
4. task runtime, tools, and approval flows
5. evaluation, control plane, and multi-channel delivery

## References

[1] `docs/450-Industry-Patterns-For-Adaptive-Assistants.md`

[2] `docs/460-Adaptive-Evolution-Model.md`
