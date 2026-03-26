# Tool Model

## Goal

Define tools as first-class product assets with clear schemas, policies, and runtime behavior.

This document assumes the policy model in `docs/370-Safety-And-Permissions.md`, the runtime model in `docs/420-Request-Runtime.md`, and the adaptive behavior model in `docs/460-Adaptive-Evolution-Model.md` [1][2][3].

## Scope

### Included

- tool definitions
- input and output schemas
- risk classification
- execution adapters
- approval hooks
- tool result traces

### Excluded

- arbitrary hidden tool calls
- tool behavior defined only in prompt text
- connector-specific policy bypasses

## Tool Definition

A tool should declare:

- stable id and label
- description
- input schema
- output schema
- risk tier
- execution adapter
- timeout and retry policy
- visibility and ownership

## Tool Classes

- retrieval tool
- transformation tool
- local action tool
- external API tool
- workflow tool

Tool class affects policy defaults, audit requirements, and execution UX.

## Execution Rules

- tool invocations must be typed and traceable
- tool inputs should be validated before execution
- results should be stored as structured artifacts when possible
- failed tool calls should preserve error detail for inspection
- tool availability should be resolved through profile, workspace, and policy rules together
- adaptive overlays may influence tool preference order, but not expand the effective tool permission set [1][3]

## Approval Rules

- approval requirements should be derived from tool risk tier plus active policy
- tools should not self-elevate their own permissions through prompt content
- learned behavior should not convert a previously approval-gated tool into an unapproved action path [1][3]

## Data Impact

Recommended entities:

- `tool_definitions`
- `tool_versions`
- `tool_invocations`
- `tool_artifacts`

## Client Impact

- users should be able to inspect which tools a profile may use
- runtime traces should show which tools ran, with what outcome
- approvals should reference tool name, action summary, and target

## References

[1] `docs/370-Safety-And-Permissions.md`

[2] `docs/420-Request-Runtime.md`

[3] `docs/460-Adaptive-Evolution-Model.md`
