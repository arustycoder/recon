# Evaluation And Quality

## Goal

Define how the product measures assistant quality, catches regressions, and controls profile or provider changes before they become default behavior.

This document assumes the adaptive governance loop described in `docs/460-Adaptive-Evolution-Model.md` and the industry patterns summarized in `docs/450-Industry-Patterns-For-Adaptive-Assistants.md` [1][2].

## Scope

### Included

- offline evaluation suites
- human review workflows
- online product signals
- quality, latency, and cost guardrails
- release gates for profiles, tools, and retrieval behavior

### Excluded

- public leaderboard features
- one-number quality reporting with no traceability

## Quality Dimensions

- correctness
- groundedness
- instruction following
- task success
- safety behavior
- latency
- cost

## Evaluation Layers

### Offline

Stable cases used to compare profiles, providers, tool behavior, and retrieval behavior.

### Human Review

Focused inspection for correctness, citations, usability, and safety.

### Online Signals

Runtime evidence such as feedback, completion rate, tool failure rate, approval failure rate, latency drift, and cost drift.

## Release Rules

- default profile changes should pass offline regression first
- tool-enabled profiles should be reviewed for both success and safety
- retrieval changes should be evaluated for citation quality, not only answer style
- cost and latency regressions should be visible before rollout
- learned overlays should be promotable only after explicit evaluation evidence [1][2]

## Data Impact

Recommended entities:

- `eval_suites`
- `eval_cases`
- `eval_runs`
- `eval_results`
- `feedback_records`

## Client Impact

- control-plane surfaces should expose comparison views between profile or provider revisions
- feedback capture should be available from every user-facing channel

## References

[1] `docs/460-Adaptive-Evolution-Model.md`

[2] `docs/450-Industry-Patterns-For-Adaptive-Assistants.md`
