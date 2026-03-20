# Provider Resilience

## Goal

Prevent a flaky provider from being hit repeatedly by the gateway during fallback routing.

## Scope

### Included

- per-provider consecutive failure counters
- cooldown windows after repeated failures
- immediate cooldown for explicit upstream rate-limit responses
- cooldown-aware graded provider health responses
- routing that skips providers in cooldown when alternatives exist
- manual reset to clear provider breaker state

### Excluded

- distributed circuit breaker state
- rolling latency windows
- success-rate based health scoring
- manual reset UI

## Behavior

- each provider profile can define:
  - `max_consecutive_failures`
  - `cooldown_seconds`
- when a provider crosses the failure threshold, the gateway opens a cooldown window
- when an upstream provider returns `429`, the gateway marks it as rate-limited and opens cooldown immediately
- fallback routing prefers healthy providers and skips cooled-down providers when another route is available
- `GET /api/providers/{provider_id}/health` returns a dedicated rate-limit status while the provider is blocked for `429`
- this does not imply automatic fallback to mock unless the caller explicitly requested `provider_strategy=fallback`

## API And Config Impact

Provider discovery now exposes:

- `cooldown_seconds`
- `max_consecutive_failures`
- `prompt_cost_per_1k`
- `completion_cost_per_1k`

`DARKFACTORY_GATEWAY_PROVIDERS_JSON` may now include those fields per provider record.

## Implementation Notes

- the circuit breaker state is intentionally in-memory for the first phase
- a successful request resets the provider failure counter
- if all providers are cooling down, the gateway still returns a clear provider error instead of silently hanging
- operators can manually reset a provider after fixing keys, network reachability, or upstream service state
- rate-limit cooldown should preserve the upstream signal in both request logs and provider health checks
