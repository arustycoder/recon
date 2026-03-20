# Gateway Provider Adapters

## Goal

Separate gateway-side provider calls into explicit provider adapters so routing, retries, and provider-specific policies can evolve without staying coupled to one generic wrapper.

## Scope

### Included

- dedicated adapters for:
  - `mock`
  - `ollama`
  - `openai_compatible`
  - `http_backend`
- adapter factory routing by provider kind
- shared adapter metrics collection

### Excluded

- provider-specific retry policies
- adapter-level circuit breaking
- tracing exporters

## Behavior

- each adapter owns the concrete provider call path for its provider kind
- the gateway service depends on the adapter interface, not on desktop `AssistantService.stream_reply()` as a single monolithic path
- metrics and target labels remain normalized through the shared adapter result type

## Implementation Notes

- the first phase still reuses low-level helper methods from `AssistantService` to avoid duplicating HTTP protocol handling
- the important architectural shift is that provider branching now happens in the adapter layer, not in the gateway service
