# Gateway Review

## What Changed

The gateway now has three meaningful layers instead of one:

- provider profiles and fallback routing
- skill template rendering with parameter injection
- normalized gateway APIs for chat, stream, cancel, provider health, and request inspection

## Reflection

### What worked

- reusing `AssistantService` kept the first gateway implementation small
- env-driven provider profiles make local experimentation fast
- a deterministic skill pipeline is much easier to debug than agentic skill execution
- the new adapter boundary lets the gateway evolve without staying hard-coupled to desktop orchestration forever

### What is still intentionally missing

- background job execution
- authentication, quotas, and audit policy

### Risks

- fallback can hide flaky providers if gateway-side logs are not surfaced clearly
- phase-based skills are useful, but they are not yet true tools
- the default gateway adapter still reuses desktop provider code, so the boundary is cleaner but not fully independent yet
- sync and stream error handling can still drift unless their contracts are reviewed together whenever resilience logic changes

## Industry Comparison

### LiteLLM Proxy

- LiteLLM positions its Proxy Server as a centralized LLM gateway with authentication, spend tracking, logging, guardrails, caching, and virtual keys
- our current design aligns with its value on unified provider routing and fallback, but stays intentionally smaller and product-embedded for now

### OpenAI-style API contracts

- OpenAI’s current API guidance emphasizes semantic streaming events, request IDs, and caller-supplied `X-Client-Request-Id` correlation
- the gateway should keep converging on normalized `chat / stream / cancel / health / requests` contracts so the desktop client stays thin and easier to evolve
- background execution and polling are the clearest next step once Recon starts handling very long reasoning jobs

### LangGraph-style orchestration

- graph orchestration becomes valuable when the request flow contains multi-step tools, retries, and human approval
- Recon is not there yet; the current deterministic skill layer is the lower-risk intermediate step

## Next Gaps

- separate gateway provider adapters from desktop service code
- add durable gateway metrics and cost tracking, not only request status
- add distributed provider resilience state for multi-process deployments
- evolve phase-based skills toward tool-using workflows only when the product truly needs them
- replace the default `AssistantService` adapter with gateway-native provider adapters over time
- unify gateway error taxonomy so `404`, `429`, timeout, stream interruption, and provider misconfiguration always map to stable client-facing semantics
