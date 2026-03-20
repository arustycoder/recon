# Provider Health And Reset

## Goal

Make provider status operationally useful instead of binary, and give operators a way to recover a provider immediately after fixing it.

## Scope

### Included

- health grading:
  - `healthy`
  - `degraded`
  - `cooldown`
  - `disabled`
  - `misconfigured`
  - `unreachable`
- cooldown-aware health responses
- manual provider reset endpoint

### Excluded

- automated alerting
- UI for health reset
- distributed shared breaker state

## API

- `GET /api/providers/{provider_id}/health`
- `POST /api/providers/{provider_id}/reset`

## Behavior

- `healthy`: provider is callable and has no outstanding failure pressure
- `degraded`: provider is callable, but recent failures exist
- `cooldown`: provider is temporarily blocked after repeated failures
- `disabled`: provider is disabled in configuration
- `misconfigured`: provider configuration is incomplete
- `unreachable`: provider health check failed because the target could not be reached

## Implementation Notes

- manual reset clears cooldown and consecutive failure counters
- health grading is based on provider config, breaker state, and active health probing
- this is intentionally simpler than a full service mesh or distributed breaker design
