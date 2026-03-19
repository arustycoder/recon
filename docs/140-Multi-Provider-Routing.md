# Multi-Provider Routing

## Goal

Turn the gateway provider registry from a simple provider picker into a lightweight routing layer that can manage more than one concrete backend instance.

## Scope

### Included

- named provider profiles with `enabled`, `default`, `priority`, and `tags`
- default provider selection
- fallback routing across multiple providers
- provider-level default skills
- provider health probing through the gateway

### Excluded

- weighted traffic splitting
- circuit breakers and cooldown windows
- cost-aware routing
- distributed failover state

## Behavior

- a request can still target a specific `provider_id`
- if `provider_strategy=default`, the gateway uses the selected provider or the default provider
- if `provider_strategy=fallback`, the gateway tries the selected provider first and then falls back across other enabled providers in priority order
- streaming requests emit a `provider_error` SSE event before moving to the next provider in fallback mode

## API Impact

### Provider metadata

`GET /api/providers` now returns richer provider information:

- `enabled`
- `priority`
- `tags`
- `default_skill_ids`

### Provider health

New endpoint:

- `GET /api/providers/{provider_id}/health`

This allows the desktop app or operators to validate a specific configured backend before routing live traffic to it.

### Chat request

The request model now accepts:

- `provider_id`
- `provider_strategy`

## Implementation Notes

- provider profiles remain env-driven for now through `DARKFACTORY_GATEWAY_PROVIDERS_JSON`
- the gateway reuses the existing desktop `AssistantService` per provider profile
- fallback is deliberately synchronous and simple in the first phase so failure behavior is easy to reason about
