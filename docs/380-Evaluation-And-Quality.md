# Evaluation And Quality

## Goal

Define how `recon` measures assistant quality, catches regressions, and compares profile or provider changes before they become the default behavior.

## Scope

### Included

- offline evaluation suites
- golden task cases
- profile and provider comparison
- human review workflow
- user feedback capture
- quality, latency, and cost guardrails

### Excluded

- public leaderboard features
- one-number quality scoring without trace detail

## Evaluation Layers

### Offline Regression

Stable test cases used to compare:

- prompt/profile revisions
- provider changes
- tool behavior changes
- retrieval changes

### Human Review

Focused review for:

- correctness
- citation quality
- instruction following
- safety and refusal behavior
- task usefulness

### Online Signals

Runtime signals such as:

- user feedback
- completion rate
- approval failure rate
- tool failure rate
- cost and latency drift

## Data Impact

Recommended new entities:

- `eval_suites`
- `eval_cases`
- `eval_runs`
- `eval_results`
- `feedback_records`

Suggested tracked fields:

- profile version
- provider id
- tool set
- retrieval mode
- pass/fail or scored dimensions
- reviewer notes

## Release Rules

- default profile changes should pass offline regression first
- tool-enabled profiles should be checked for both task success and safety behavior
- major retrieval changes should include citation-quality review, not only answer review

## Implementation Notes

- the first phase can keep evaluation storage simple and file-backed if needed
- request metrics already present in the gateway should be reused for latency and cost baselines
- evaluation should be treated as a product requirement, not a temporary development aid

## Relationship To Existing Docs

- complements `docs/170-Gateway-Observability.md`
- complements `docs/200-Gateway-Metrics-And-Costs.md`
- complements `docs/330-Generic-Assistant-Platform.md`
