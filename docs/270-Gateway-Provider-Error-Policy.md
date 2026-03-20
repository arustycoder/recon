# Gateway Provider Error Policy

## Goal

Make gateway retry and cooldown behavior explicit instead of scattering those decisions across service branches.

## Scope

This version introduces a first policy table over normalized gateway error types.

The table currently governs:

- provider cooldown behavior
- whether an error is considered recoverable enough for same-provider sync retry
- the semantic bridge between adapter failures and gateway routing behavior

## Policy Table

Current policy intent:

- `rate_limited`
  - same-provider sync retry: no
  - cooldown: full provider cooldown window
- `stream_interrupted`
  - same-provider sync retry: yes
  - cooldown: short cooldown window
- `upstream_timeout`
  - same-provider sync retry: yes
  - cooldown: threshold-based
- `upstream_unreachable`
  - same-provider sync retry: yes
  - cooldown: threshold-based
- `provider_disabled`
  - same-provider sync retry: no
  - cooldown: none
- `provider_cooldown`
  - same-provider sync retry: no
  - cooldown: none
- `misconfigured`
  - same-provider sync retry: no
  - cooldown: none
- all other classified failures
  - same-provider sync retry: no
  - cooldown: threshold-based

## Implementation Notes

- policy currently lives alongside the classifier in `src/darkfactory_gateway/errors.py`
- adapters now normalize provider failures into `GatewayProviderError`
- provider client code now emits typed `AssistantServiceError` instances before adapter normalization
- gateway service consumes normalized errors and applies policy-driven cooldown decisions
- provider client sync recovery now consults the shared policy table for same-provider non-stream retry decisions

## Remaining Gaps

- sync retry policy is now shared, but fallback routing and retry counting are still not fully driven from one centralized execution planner
- fallback routing still depends mainly on request strategy plus provider availability
- future versions should expose policy metadata in operator docs or admin APIs if this becomes externally configurable
