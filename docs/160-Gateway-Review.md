# Gateway Review

## What Changed

The gateway now has three meaningful layers instead of one:

- provider profiles and fallback routing
- skill template rendering with parameter injection
- normalized gateway APIs for chat, stream, cancel, and provider health

## Reflection

### What worked

- reusing `AssistantService` kept the first gateway implementation small
- env-driven provider profiles make local experimentation fast
- a deterministic skill pipeline is much easier to debug than agentic skill execution

### What is still intentionally missing

- background job execution
- authentication, quotas, and audit policy

### Risks

- fallback can hide flaky providers if gateway-side logs are not surfaced clearly
- phase-based skills are useful, but they are not yet true tools
- direct reuse of desktop provider code is efficient now but will eventually need separation once gateway-specific concerns grow

## Industry Comparison

### LiteLLM Proxy

- LiteLLM positions its Proxy Server as a centralized LLM gateway with authentication, spend tracking, logging, guardrails, caching, and virtual keys
- our current design aligns with its value on unified provider routing and fallback, but stays intentionally smaller and product-embedded for now

### OpenAI-style API contracts

- OpenAI’s current API guidance emphasizes semantic streaming events, request IDs, and caller-supplied `X-Client-Request-Id` correlation
- the gateway should keep converging on normalized `chat / stream / cancel / health / requests` contracts so the desktop client stays thin and easier to evolve
- background execution and polling are the clearest next step once DarkFactory starts handling very long reasoning jobs

### LangGraph-style orchestration

- graph orchestration becomes valuable when the request flow contains multi-step tools, retries, and human approval
- DarkFactory is not there yet; the current deterministic skill layer is the lower-risk intermediate step

## Next Gaps

- separate gateway provider adapters from desktop service code
- add durable gateway metrics and cost tracking, not only request status
- add distributed provider resilience state for multi-process deployments
- evolve phase-based skills toward tool-using workflows only when the product truly needs them
