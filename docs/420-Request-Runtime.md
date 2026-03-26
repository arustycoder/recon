# Request Runtime

## Goal

Define the lifecycle of a single assistant request from ingress to final answer, tool action, approval wait, or task handoff.

This runtime assumes the effective assistant model defined in `docs/460-Adaptive-Evolution-Model.md` and the canonical object model in `docs/410-Core-Data-Model.md` [1][2].

## Scope

### Included

- request intake
- actor, workspace, and profile resolution
- context assembly
- retrieval
- tool loop
- streaming
- task handoff
- trace persistence

### Excluded

- long-running task internals beyond the handoff boundary
- connector-specific transport details

## Lifecycle

1. validate actor, workspace, and channel context
2. resolve assistant profile, approved adaptive overlays, and effective policy [1]
3. load relevant memory and recent conversation state
4. retrieve knowledge when needed
5. decide response mode: direct, streamed, tool-assisted, or task handoff
6. execute bounded tool calls when allowed
7. generate and stream or finalize the answer
8. persist citations, traces, memory candidates, and feedback hooks
9. create a task instead of continuing inline when the work exceeds foreground limits

## Response Modes

- `direct_answer`
- `streamed_answer`
- `tool_assisted_answer`
- `task_created`
- `waiting_approval`
- `refused`

## Runtime Rules

- every request should produce a request record even when refused or canceled
- partial output should remain inspectable when streaming fails
- tool calls should be bounded by policy, timeout, and trace capture
- citations should travel with grounded outputs
- memory writes should be explicit outputs of the runtime, not hidden side effects
- adaptive behavior must be read from approved overlays, not inferred ad hoc on each request [1]

## Data Impact

Recommended entities:

- `request_records`
- `request_steps`
- `tool_invocations`
- `request_citations`
- `memory_candidates`

## Client Impact

- clients should be able to render progress, citations, approvals, and task handoff consistently
- polling and streaming should represent the same underlying request state

## References

[1] `docs/460-Adaptive-Evolution-Model.md`

[2] `docs/410-Core-Data-Model.md`
