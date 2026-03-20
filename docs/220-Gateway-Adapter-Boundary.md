# Gateway Adapter Boundary

## Goal

Start separating gateway orchestration from the desktop-oriented `AssistantService` implementation.

## Scope

### Included

- gateway adapter protocol
- adapter factory
- default adapter backed by `AssistantService`
- gateway-side latency and metric measurement in the adapter layer

### Excluded

- fully independent provider clients for gateway and desktop
- separate package extraction
- remote worker adapters

## Why

The gateway should own:

- provider execution lifecycle
- gateway metrics
- request correlation ids
- resilience behavior

The desktop service should not remain the gateway’s long-term abstraction boundary.

## Implementation Notes

- `GatewayService` now depends on an adapter factory instead of constructing `AssistantService` directly
- the default adapter still reuses desktop code for now, which keeps migration cost low
- future work can replace the adapter implementation provider by provider without rewriting gateway orchestration
