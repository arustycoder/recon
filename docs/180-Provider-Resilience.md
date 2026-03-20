# Provider Resilience

## Goal

Prevent a flaky provider from being hit repeatedly by the gateway during fallback routing.

## Scope

### Included

- per-provider consecutive failure counters
- cooldown windows after repeated failures
- cooldown-aware provider health responses
- routing that skips providers in cooldown when alternatives exist

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
- fallback routing prefers healthy providers and skips cooled-down providers when another route is available
- `GET /api/providers/{provider_id}/health` returns a cooldown message while the provider is blocked

## API And Config Impact

Provider discovery now exposes:

- `cooldown_seconds`
- `max_consecutive_failures`

`DARKFACTORY_GATEWAY_PROVIDERS_JSON` may now include those fields per provider record.

## Implementation Notes

- the circuit breaker state is intentionally in-memory for the first phase
- a successful request resets the provider failure counter
- if all providers are cooling down, the gateway still returns a clear provider error instead of silently hanging
