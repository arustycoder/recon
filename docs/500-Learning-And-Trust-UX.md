# Learning And Trust UX

## Goal

Define how the product makes assistant behavior inspectable, controllable, and believable to end users.

This document unifies the memory, knowledge, policy, and adaptive-learning models in `docs/340-Memory-Model.md`, `docs/360-Knowledge-System.md`, `docs/370-Safety-And-Permissions.md`, and `docs/460-Adaptive-Evolution-Model.md` [1][2][3][4].

## Scope

### Included

- user-facing trust questions
- evidence and citation UX
- learning and memory controls
- action and approval visibility
- refusal and policy explanation
- temporary and no-learning modes

### Excluded

- full observability consoles for operators
- raw model internals or chain-of-thought exposure

## Core Trust Questions

For any materially important result, the user should be able to answer:

- what informed this answer
- what sources were used
- what the assistant is trying to do next
- what it learned or proposed to learn
- what was blocked or refused
- how to change the behavior next time

## Trust Surfaces

### Answer Provenance

The product should make it visible when an answer was shaped by:

- retrieved knowledge and citations
- remembered context
- learned behavior overlays
- active profile selection

The goal is not to dump every internal signal, but to expose the factors that materially changed the result.

### Action Visibility

When the assistant moves beyond answering, the user should see:

- what tool or action is proposed
- what inputs or resources it will touch
- whether approval is required
- where results will be written or published

### Learning Visibility

The product should distinguish clearly between:

- `memory`: remembered facts, preferences, summaries, or constraints
- `learned behavior`: adaptive overlays that change how the assistant behaves

These should not be collapsed into one generic “memory” surface.

### Policy Visibility

When the assistant refuses, waits, or narrows its behavior, the product should explain whether the reason was:

- missing permission
- missing evidence
- temporary mode or no-learning mode
- missing approval
- policy restriction on scope or risk

## Control Model

Users should be able to:

- inspect sources and citations
- inspect and edit durable memory
- inspect, pause, reset, or delete learned behavior
- choose temporary or no-learning interactions
- see which profile is active before execution

Workspace owners or operators should additionally be able to:

- control shared learning scope
- review higher-risk adaptive changes
- control shared source visibility and automation boundaries

## UX Rules

- separate `remembered` from `learned`
- separate `grounded` from `confident-sounding`
- explain policy effects in product language, not implementation jargon
- prefer evidence labels and citations over fake certainty scores
- make temporary and no-learning modes easy to enter
- make rollback of learning straightforward and visible

## Product Implications

- trust should be a persistent product surface, not a hidden debug panel
- the product should explain behavior changes as changes in profile, memory, policy, or learned overlays
- citations, approvals, and learning controls should be available across channels when they materially affect the result

## References

[1] `docs/340-Memory-Model.md`

[2] `docs/360-Knowledge-System.md`

[3] `docs/370-Safety-And-Permissions.md`

[4] `docs/460-Adaptive-Evolution-Model.md`
